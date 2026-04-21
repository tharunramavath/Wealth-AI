import os
import json
import re
import time
import logging
import hashlib
import requests
from openai import OpenAI
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
SERP_API_KEY = os.environ.get("SERP_API", "")
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)
MODEL_NAME = "meta/llama-3.1-405b-instruct"

INTENTS_NEEDING_LIVE_NEWS = {"market_outlook", "stock_research", "rebalancing", "general"}

NEWS_CACHE_TTL = 300
NEWS_CACHE = {}

RESPONSE_CACHE_TTL = 600
RESPONSE_CACHE = {}

INTENT_PATTERNS = {
    "portfolio_analysis": [
        r"analyze.*portfolio", r"portfolio.*risk", r"my.*holdings", r"my.*stocks",
        r"diversif", r"allocation", r"weight.*portfolio", r"concentration"
    ],
    "rebalancing": [
        r"rebalanc", r"adjust.*allocation", r"change.*portfolio", r"trim.*position",
        r"add.*position", r"reduce.*holding", r"sell.*stock", r"buy.*stock"
    ],
    "market_outlook": [
        r"market.*outlook", r"market.*trend", r"market.*condition", r"bull.*bear",
        r"market.*direction", r"nifty.*outlook", r"sector.*rotation", r"which.*sector",
        r"war.*impact", r"impact.*portfolio", r"geopolitical", r"russia.*ukraine",
        r"israel.*iran", r"war.*stock", r"current.*situation", r"economic.*impact"
    ],
    "stock_research": [
        r"what.*about.*stock", r"tell.*about.*stock", r"analyze.*stock", r"stock.*recommend",
        r"is.*stock.*good", r"should.*buy", r"is.*reliance", r"is.*tcs", r"is.*infosys",
        r"ticker", r"price.*target"
    ],
    "stock_recommendation": [
        r"recommend.*stock", r"recommend.*me.*stock", r"top.*stock", r"best.*stock",
        r"which.*stock.*should", r"give.*me.*stock", r"stock.*idea", r"stock.*pick",
        r"buy.*suggest", r"investment.*idea", r"good.*stock.*now", r"top.*5",
        r"top.*10", r"stock.*opportunity", r"what.*stock.*should.*buy",
        r"which.*stock.*to.*buy", r"find.*stock", r"identify.*stock"
    ],
    "education": [
        r"what.*is.*eps", r"explain.*pe.*ratio", r"what.*does.*mean", r"how.*does.*work",
        r"what.*is.*bull", r"what.*is.*bear", r"learn.*about", r"understand"
    ],
    "complaint": [
        r"not.*working", r"error", r"bug", r"issue", r"problem", r"fix.*this", r"wrong"
    ],
}

def detect_intent(query: str) -> str:
    query_lower = query.lower()
    scores = {}
    
    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, query_lower):
                score += 1
        scores[intent] = score
    
    best_intent = max(scores, key=scores.get)
    return best_intent if scores[best_intent] > 0 else "general"

INTENT_INSTRUCTIONS = {
    "portfolio_analysis": "Focus on analyzing the user's current portfolio composition, risk metrics, sector exposure, and diversification. Provide specific insights about their holdings.",
    "rebalancing": "Provide specific rebalancing recommendations with percentage adjustments. Mention specific sectors or stocks to add/trim.",
    "market_outlook": "Share current market trends, sector rotation insights, and macroeconomic factors. Relate to the user's portfolio if applicable.",
    "stock_research": "Provide stock-specific insights including fundamentals, valuation, recent news, and technical outlook. Be specific about the company.",
    "stock_recommendation": "Use the quantitative stock recommendation engine to generate top stock picks based on the user's risk profile. Present the recommendations clearly with scores and allocation.",
    "education": "Explain financial concepts clearly with examples relevant to Indian markets. Use simple language.",
    "complaint": "Acknowledge the issue empathetically and provide helpful troubleshooting steps.",
    "general": "Provide a helpful, balanced response covering all relevant aspects."
}

def parse_stock_count(query: str) -> int:
    query_lower = query.lower()
    match = re.search(r'top\s*(\d+)', query_lower)
    if match:
        count = int(match.group(1))
        return min(max(count, 5), 10)
    if 'five' in query_lower:
        return 5
    if 'ten' in query_lower:
        return 10
    return 5


def get_stock_recommendations(
    n: int,
    risk_tolerance: str,
    investment_horizon: str,
    portfolio: list
) -> dict:
    try:
        from src.stock_recommender import get_stock_recommendation as get_rec
        result = get_rec(
            n=n,
            risk_tolerance=risk_tolerance,
            investment_horizon=investment_horizon,
            user_portfolio=portfolio
        )
        return result
    except Exception as e:
        logger.error(f"Error getting stock recommendations: {e}")
        return {"error": str(e), "recommended_stocks": []}


def generate_stock_explanation(recommendations: dict, risk_tolerance: str) -> str:
    if not recommendations.get("recommended_stocks"):
        return "Unable to generate stock recommendations at this time."
    
    stocks = recommendations["recommended_stocks"]
    summary = recommendations.get("portfolio_summary", {})
    methodology = recommendations.get("scoring_methodology", {})
    
    stocks_text = "\n".join([
        f"{i+1}. **{s['ticker']}** ({s['sector']}) - Score: {s['score']:.2f}"
        for i, s in enumerate(stocks)
    ])
    
    sectors = summary.get("sectors_represented", [])
    diversification = summary.get("diversification", "Medium")
    risk_level = summary.get("risk_level", "Moderate")
    
    prompt = f"""You are a quantitative investment advisor. Explain these stock recommendations clearly.

USER PROFILE:
- Risk Tolerance: {risk_tolerance.upper()}
- Recommended Portfolio Diversification: {diversification}

TOP STOCK RECOMMENDATIONS:
{stocks_text}

PORTFOLIO SUMMARY:
- Sectors: {', '.join(sectors)}
- Number of Stocks: {len(stocks)}
- Risk Level: {risk_level}

SCORING METHODOLOGY:
{methodology.get('momentum_weight', 'N/A')} momentum, {methodology.get('volatility_weight', 'N/A')} volatility,
{methodology.get('beta_weight', 'N/A')} beta, {methodology.get('drawdown_weight', 'N/A')} drawdown control

Write a clear, professional explanation (2-3 paragraphs):
1. Why these stocks were selected based on the quantitative model
2. How they provide diversification across sectors
3. Key risk considerations for this {risk_tolerance} portfolio
Do NOT guarantee returns. Be specific about scores and metrics."""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a quantitative investment advisor. Provide clear, professional explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        return "Stock recommendations generated. Explanation unavailable."

def get_rag_context(query: str, k=3) -> str:
    try:
        embeddings = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")
        vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = vectorstore.as_retriever(search_kwargs={"k": k}).invoke(query)
        if not docs:
            logger.info("No relevant documents found in vector store for query")
            return ""
        return "\n\n".join([doc.page_content for doc in docs])
    except FileNotFoundError:
        logger.warning("FAISS index file not found. Run the indexing script first.")
        return ""
    except Exception as e:
        logger.error(f"Error loading RAG context: {e}")
        return ""

def get_live_news(query: str, num_results: int = 5) -> tuple:
    if not SERP_API_KEY:
        logger.warning("SERP_API key not configured")
        return "", []
    
    cache_key = hashlib.md5(f"{query}:{num_results}".encode()).hexdigest()
    current_time = time.time()
    
    if cache_key in NEWS_CACHE:
        cached_time, cached_data, cached_sources = NEWS_CACHE[cache_key]
        if current_time - cached_time < NEWS_CACHE_TTL:
            return cached_data, cached_sources
    
    try:
        params = {
            "engine": "google_news",
            "q": query,
            "num": num_results,
            "api_key": SERP_API_KEY
        }
        response = requests.get("https://serpapi.com/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        news_results = data.get("news_results", [])
        if not news_results:
            top_stories = data.get("top_stories", [])
            news_results = top_stories[:num_results]
        
        if not news_results:
            return "", []
        
        formatted_news = []
        sources = []
        for i, item in enumerate(news_results[:num_results], 1):
            title = item.get("title", "")
            source_data = item.get("source", {})
            if isinstance(source_data, dict):
                source = source_data.get("name", "Unknown")
            else:
                source = str(source_data)
            date = item.get("date", "")
            snippet = item.get("snippet", item.get("description", ""))
            sources.append(f"{source} ({date})")
            
            formatted_news.append(f"[{i}] {title}")
            formatted_news.append(f"    Source: {source} | Date: {date}")
            if snippet:
                formatted_news.append(f"    Summary: {snippet[:200]}")
        
        result = "\n".join(formatted_news)
        NEWS_CACHE[cache_key] = (current_time, result, sources)
        return result, sources
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching live news: {e}")
        return "", []
    except Exception as e:
        logger.error(f"Unexpected error in get_live_news: {e}")
        return "", []

def build_context_with_live_news(query: str, intent: str) -> tuple:
    rag_context = get_rag_context(query)
    live_news = ""
    sources = []
    
    if intent in INTENTS_NEEDING_LIVE_NEWS:
        search_terms = query
        if intent == "market_outlook":
            search_terms = f"{query} stock market impact"
        elif intent == "stock_research":
            search_terms = f"{query} stock latest news"
        elif intent == "rebalancing":
            search_terms = f"{query} portfolio strategy market"
        
        live_news, sources = get_live_news(search_terms)
    
    if rag_context and live_news:
        context = f"=== HISTORICAL MARKET DATA ===\n{rag_context}\n\n=== LIVE NEWS (Current) ===\n{live_news}"
    elif live_news:
        context = f"=== LIVE NEWS (Current) ===\n{live_news}\n\nNo historical market data available for this query."
    elif rag_context:
        context = rag_context
    else:
        context = "No specific market data available. Use your general knowledge."
    
    return context, sources

def format_portfolio(portfolio: list) -> str:
    if not portfolio:
        return "No portfolio loaded."
    lines = []
    for p in portfolio:
        ticker = p.get("ticker", "Unknown")
        qty = p.get("quantity", 0)
        avg_price = p.get("avg_price", 0)
        sector = p.get("sector", "Unknown")
        lines.append(f"  - {ticker}: {qty} shares @ ₹{avg_price:.2f} (Sector: {sector})")
    return "\n".join(lines)

def format_conversation_history(history: list) -> str:
    if not history:
        return "No previous conversation."
    lines = []
    for msg in history[-10:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "")[:300]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)

def format_nba_history(nba_history: list) -> str:
    if not nba_history:
        return "No recent recommendations."
    lines = []
    for rec in nba_history[-3:]:
        action = rec.get("next_best_action", "N/A")
        if isinstance(action, dict):
            action = action.get("action", "N/A")
        insight = rec.get("market_insight", "")[:150]
        created = rec.get("created_at", "")[:10]
        lines.append(f"  - [{created}] {action}: {insight}...")
    return "\n".join(lines) if lines else "No recent recommendations."

def answer_finance_query(
    user_query: str,
    user_profile: dict,
    portfolio: list,
    conversation_history: list = None,
    recent_nba: list = None,
    user_id: str = None
) -> dict:
    if not NVIDIA_API_KEY:
        return {"answer": "NVIDIA_API_KEY not configured. Please set it in your .env file.", "sources": [], "cached": False}

    cache_key = f"{user_id or 'anonymous'}:{user_query}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    current_time = time.time()
    
    if cache_hash in RESPONSE_CACHE:
        cached_time, cached_response = RESPONSE_CACHE[cache_hash]
        if current_time - cached_time < RESPONSE_CACHE_TTL:
            return {"answer": cached_response["answer"], "sources": cached_response["sources"], "cached": True}

    detected_intent = detect_intent(user_query)
    
    if detected_intent == "stock_recommendation":
        n = parse_stock_count(user_query)
        risk_tolerance = user_profile.get("risk_tolerance", "moderate")
        investment_horizon = user_profile.get("investment_horizon", "medium")
        
        try:
            recommendations = get_stock_recommendations(
                n=n,
                risk_tolerance=risk_tolerance,
                investment_horizon=investment_horizon,
                portfolio=portfolio
            )
            
            explanation = generate_stock_explanation(recommendations, risk_tolerance)
            
            RESPONSE_CACHE[cache_hash] = (current_time, {
                "answer": explanation,
                "sources": [],
                "recommendations": recommendations
            })
            
            return {
                "answer": explanation,
                "sources": [],
                "cached": False,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Error in stock recommendation: {e}")
            return {"answer": "I encountered an error generating stock recommendations. Please try again.", "sources": [], "cached": False}
    
    intent_instruction = INTENT_INSTRUCTIONS.get(detected_intent, INTENT_INSTRUCTIONS["general"])
    
    portfolio_text = format_portfolio(portfolio)
    context, sources = build_context_with_live_news(user_query, detected_intent)
    history_text = format_conversation_history(conversation_history or [])
    nba_text = format_nba_history(recent_nba or [])
    
    risk_tolerance = user_profile.get("risk_tolerance", "moderate")
    investment_horizon = user_profile.get("investment_horizon", "medium")
    goals = user_profile.get("goals", [])
    goals_text = ", ".join(goals) if isinstance(goals, list) else str(goals)

    system_instruction = """You are a senior financial advisor at a leading wealth management firm.
Use the LIVE NEWS DATA below to provide detailed, insightful analysis. Synthesize information into natural prose.

IMPORTANT: Maintain consistency with our previous conversation. If this is a follow-up question, build upon what was discussed before.

GUIDELINES:
1. Write in flowing paragraphs, not bullet lists
2. Integrate specific numbers, dates, and facts naturally
3. Directly relate news insights to the user's specific portfolio holdings
4. Give clear buy/hold/sell recommendations with specific tickers and reasons
5. Explain WHY the news affects their portfolio
6. Be direct and actionable"""

    prompt = f"""{system_instruction}

=== LIVE NEWS DATA ===
{context}

=== USER'S PORTFOLIO ===
{portfolio_text}

=== USER PROFILE ===
- Risk Tolerance: {risk_tolerance.upper()}
- Investment Horizon: {investment_horizon.upper()}
- Financial Goals: {goals_text}

=== RECENT AI RECOMMENDATIONS ===
{nba_text}

=== PREVIOUS CONVERSATION ===
{history_text}

=== CURRENT QUESTION ===
{user_query}

Provide detailed analysis based on the news data. Write naturally. Explain how this affects the user's portfolio specifically."""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a knowledgeable and empathetic financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1500
        )
        answer = response.choices[0].message.content
        RESPONSE_CACHE[cache_hash] = (current_time, {"answer": answer, "sources": sources})
        return {"answer": answer, "sources": sources, "cached": False}
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return {"answer": "I apologize, but I encountered an error processing your request. Please try again.", "sources": [], "cached": False}


REC_STREAMS = {}

def answer_finance_query_streaming(
    user_query: str,
    user_profile: dict,
    portfolio: list,
    conversation_history: list = None,
    recent_nba: list = None,
    user_id: str = None
):
    """Streaming version of the finance query handler."""
    cache_key = f"{user_id or 'anonymous'}:{user_query}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    current_time = time.time()
    
    if cache_hash in RESPONSE_CACHE:
        cached_time, cached_response = RESPONSE_CACHE[cache_hash]
        if current_time - cached_time < RESPONSE_CACHE_TTL:
            rec = cached_response.get("recommendations", {})
            REC_STREAMS[cache_hash] = rec
            yield f"{{\"__sources\": {json.dumps(cached_response['sources'])}, \"__cached\": true, \"__intent\": \"{cached_response.get('intent', 'general')}\"}}\n"
            yield cached_response["answer"]
            return

    if not NVIDIA_API_KEY:
        yield "NVIDIA_API_KEY not configured. Please set it in your .env file."
        return

    detected_intent = detect_intent(user_query)
    
    if detected_intent == "stock_recommendation":
        n = parse_stock_count(user_query)
        risk_tolerance = user_profile.get("risk_tolerance", "moderate")
        investment_horizon = user_profile.get("investment_horizon", "medium")
        
        try:
            recommendations = get_stock_recommendations(
                n=n,
                risk_tolerance=risk_tolerance,
                investment_horizon=investment_horizon,
                portfolio=portfolio
            )
            
            REC_STREAMS[cache_hash] = recommendations
            explanation = generate_stock_explanation(recommendations, risk_tolerance)
            
            yield f"{{\"__sources\": [], \"__cached\": false, \"__intent\": \"stock_recommendation\", \"__recommendations\": true}}\n"
            
            for token in explanation:
                yield token
            
            RESPONSE_CACHE[cache_hash] = (current_time, {
                "answer": explanation, 
                "sources": [],
                "recommendations": recommendations,
                "intent": "stock_recommendation"
            })
            return
            
        except Exception as e:
            logger.error(f"Error in stock recommendation: {e}")
            yield "I encountered an error generating stock recommendations. Please try again."
            return
    
    intent_instruction = INTENT_INSTRUCTIONS.get(detected_intent, INTENT_INSTRUCTIONS["general"])
    
    portfolio_text = format_portfolio(portfolio)
    context, sources = build_context_with_live_news(user_query, detected_intent)
    history_text = format_conversation_history(conversation_history or [])
    nba_text = format_nba_history(recent_nba or [])
    
    risk_tolerance = user_profile.get("risk_tolerance", "moderate")
    investment_horizon = user_profile.get("investment_horizon", "medium")
    goals = user_profile.get("goals", [])
    goals_text = ", ".join(goals) if isinstance(goals, list) else str(goals)

    system_instruction = """You are a senior financial advisor at a leading wealth management firm.
Use the LIVE NEWS DATA below to provide detailed, insightful analysis. Synthesize information into natural prose.

IMPORTANT: Maintain consistency with our previous conversation. If this is a follow-up question, build upon what was discussed before.

GUIDELINES:
1. Write in flowing paragraphs, not bullet lists
2. Integrate specific numbers, dates, and facts naturally
3. Directly relate news insights to the user's specific portfolio holdings
4. Give clear buy/hold/sell recommendations with specific tickers and reasons
5. Explain WHY the news affects their portfolio
6. Be direct and actionable"""

    prompt = f"""{system_instruction}

=== LIVE NEWS DATA ===
{context}

=== USER'S PORTFOLIO ===
{portfolio_text}

=== USER PROFILE ===
- Risk Tolerance: {risk_tolerance.upper()}
- Investment Horizon: {investment_horizon.upper()}
- Financial Goals: {goals_text}

=== RECENT AI RECOMMENDATIONS ===
{nba_text}

=== PREVIOUS CONVERSATION ===
{history_text}

=== CURRENT QUESTION ===
{user_query}

Provide detailed analysis based on the news data. Write naturally. Explain how this affects the user's portfolio specifically."""

    yield f"{{\"__sources\": {json.dumps(sources)}, \"__cached\": false}}\n"

    try:
        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a knowledgeable and empathetic financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1500,
            stream=True
        )
        
        full_response = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token
        
        RESPONSE_CACHE[cache_hash] = (current_time, {"answer": full_response, "sources": sources})
    except Exception as e:
        logger.error(f"Error in streaming response: {e}")
        yield "I apologize, but I encountered an error processing your request. Please try again."
Please try again."
