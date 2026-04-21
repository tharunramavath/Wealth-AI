import os
import json
import time
from openai import OpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from src.compliance import load_client_profile, enforce_compliance, validate_tickers
from src.structured_db import get_asset_metadata
from src.monitoring import log_prediction
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
if not NVIDIA_API_KEY:
    print("⚠️ WARNING: NVIDIA_API_KEY environment variable is not set. Setup API key to test LLM generation.")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)
MODEL_NAME = "meta/llama-3.1-405b-instruct"

def get_hybrid_context(query: str, client_portfolio: dict) -> dict:
    """Retrieves context from both Vector DB (news) and Structured DB (market fundamentals)."""
    # 1. Vector Retrieval
    vector_context = ""
    sources_used = []
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        faiss_path = os.path.join(BASE_DIR, "faiss_index")
        vectorstore = FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        docs = retriever.invoke(query)
        for doc in docs:
            src = doc.metadata.get('source', 'Unknown')
            sources_used.append(src)
            vector_context += f"--- Source: {src} ---\n{doc.page_content}\n\n"
    except Exception as e:
        print(f"⚠️ Vector Store Error: {e}")
        vector_context = ""

    # 2. Structured Metadata Retrieval
    structured_context = ""
    try:
        tickers = list(client_portfolio.keys())
        structured_metadata = get_asset_metadata(tickers)
        if not structured_metadata.empty:
            structured_context = structured_metadata.to_markdown(index=False)
        else:
            structured_context = "No volatility or sector data available."
    except Exception as e:
        print(f"⚠️ Structured DB Error: {e}")

    return {
        "vector_context": vector_context,
        "structured_context": structured_context,
        "sources": list(set(sources_used))
    }

def generate_nba(client_id: str, triggering_event: dict = None):
    """Generates the Next Best Action reasoning via Hybrid RAG + Compliance.
    
    Args:
        client_id: The client identifier
        triggering_event: Optional dict with event details that triggered this NBA
    """
    start_time = time.time()
    client = load_client_profile(client_id)
    if not client:
        return {"error": f"Client {client_id} not found."}

    event_context = ""
    if triggering_event:
        event_context = f"""
--- TRIGGERING MARKET EVENT ---
Event: {triggering_event.get('headline', 'N/A')}
Sector Impacted: {triggering_event.get('sector', 'Unknown')}
Severity: {triggering_event.get('severity', 'Low')}
Event Type: {triggering_event.get('event_type', 'general_news')}
Sentiment: {triggering_event.get('sentiment', {})}
Summary: {triggering_event.get('summary', 'N/A')}
Source: {triggering_event.get('source', 'N/A')}
"""

    # Fetch hybrid context
    query = f"News regarding {', '.join(client['portfolio'].keys())} and {client['financial_goal']}"
    context_data = get_hybrid_context(query, client['portfolio'])
    
    prompt = f"""
    You are an elite SEBI-registered wealth advisor in India specializing in NSE/BSE equities.
    Provide a Next Best Action (NBA) for the following client based ONLY on the provided market context.

    --- CLIENT PROFILE ---
    Name: {client['name']} ({client['age']})
    Risk Tolerance: {client['risk_tolerance']}
    Investment Horizon: {client['investment_horizon']} years
    Goal: {client['financial_goal']}
    Current Portfolio Weights: {json.dumps(client['portfolio'])}

    {event_context}

    --- FINANCIAL KNOWLEDGE BASE (STRUCTURED) ---
    {context_data['structured_context']}

    --- MARKET CONTEXT (VECTOR RAG) ---
    {context_data['vector_context']}

    --- EXAMPLE OF HIGH CONFIDENCE NBA ---
    Input: RBI cuts repo rate by 25bps.
    Output: {{
        "market_insight": "RBI has lowered interest rates to stimulate growth.",
        "portfolio_impact": "Positive for banking and auto stocks due to lower borrowing costs.",
        "next_best_action": "Increase weight in HDFCBANK.NS and TATAMOTORS.NS.",
        "reasoning": "Rate cuts directly improve NIMs for banks and demand for credit-sensitive sectors like Auto.",
        "proposed_portfolio": {{"HDFCBANK.NS": 0.4, "TATAMOTORS.NS": 0.3, "NIFTYBEES.NS": 0.3}},
        "confidence_score": 0.95
    }}

    --- INSTRUCTIONS ---
    1. Market Insight: Summarise the core market event from the context.
    2. Portfolio Impact: How does it affect this specific portfolio?
    3. Next Best Action: Specific trade or hold recommendation. Use actual NSE/BSE tickers (.NS or .BO).
    4. Reasoning: Explain the rationale briefly.
    5. Proposed Portfolio: Based on your recommendation, output the EXACT target portfolio weights as a JSON object (sum must equal 1.0).
    
    Please output JSON strictly matching the following schema:
    {{
        "market_insight": "string",
        "portfolio_impact": "string",
        "next_best_action": "string",
        "reasoning": "string",
        "proposed_portfolio": {{"TICKER1": 0.5, "TICKER2": 0.5}},
        "confidence_score": 0.85
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a specialist in the Indian Stock Market. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        result["sources"] = context_data["sources"]
        
        if triggering_event:
            result["triggering_event"] = {
                "headline": triggering_event.get("headline"),
                "sector": triggering_event.get("sector"),
                "severity": triggering_event.get("severity"),
                "event_type": triggering_event.get("event_type"),
                "sentiment": triggering_event.get("sentiment")
            }
        
        # Indian Market Tickers Only
        allowed_tickers = ["HDFCBANK.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "BHARTIARTL.NS", "ITC.NS", 
                          "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "WIPRO.NS", "HCLTECH.NS",
                          "TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "ONGC.NS",
                          "NIFTYBEES.NS", "GOLDBEES.NS", "LIQUIDBEES.NS", "JUNIORBEES.NS", "Cash"]
                          
        proposed_keys = list(result.get("proposed_portfolio", {}).keys())

        compliance_flags = enforce_compliance(client["risk_tolerance"], client["portfolio"], result["next_best_action"])
        hallucination_flags = validate_tickers(" ".join(proposed_keys), allowed_tickers)
        
        all_flags = compliance_flags + hallucination_flags
        result["flags"] = all_flags
        result["is_compliant"] = len(all_flags) == 0
        
        latency = (time.time() - start_time) * 1000
        
        # Log telemetry
        log_prediction(client_id, latency, result.get("confidence_score", 0), all_flags, result["next_best_action"])

        return result

    except Exception as e:
        print(f"LLM Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    if NVIDIA_API_KEY:
        from src.structured_db import update_metadata
        update_metadata() # Ensure DB is loaded for manual run
        print("\n🤖 Running Hybrid AI Engine for Client: HSBC-WM-0001 (Conservative)")
        print("-" * 50)
        output = generate_nba("HSBC-WM-0001")
        print(json.dumps(output, indent=2))
    else:
        print("\nSet GEMINI_API_KEY to test.")
