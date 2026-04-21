from typing import Dict, TypedDict
import os
import json
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from src.compliance import enforce_compliance, load_client_profile

class AgentState(TypedDict):
    client_id: str
    portfolio: dict
    risk_tolerance: str
    goal: str
    market_context: str
    proposed_nba: str
    compliance_flags: list
    final_decision: dict

# 1. Market Analyst Node
def market_analyst_agent(state: AgentState):
    print("🕵️  [Market Analyst Agent]: Retrieving context for portfolio...")
    from src.nba_engine import get_context
    portfolio_tickers = list(state["portfolio"].keys())
    query = f"News affecting {portfolio_tickers}"
    context = get_context(query)
    
    # We could have an LLM summarize here, but standard passing context is faster for Demo
    return {"market_context": context}

# 2. Strategy Agent Node
def strategy_agent(state: AgentState):
    print("📈 [Strategy Agent]: Drafting Next Best Action...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    prompt = f"""
    Given the client goal: {state['goal']} and risk tolerance: {state['risk_tolerance']}.
    Portfolio: {json.dumps(state['portfolio'])}
    Context: {state['market_context']}
    
    Draft a single, actionable trade recommendation.
    """
    response = llm.invoke(prompt)
    return {"proposed_nba": response.content}

# 3. Compliance Node
def compliance_agent(state: AgentState):
    print("🛡️  [Compliance Agent]: Running strict deterministic guardrails on strategy output...")
    flags = enforce_compliance(state["risk_tolerance"], state["portfolio"], state["proposed_nba"])
    return {"compliance_flags": flags}

# 4. Supervisor Node (Routing)
def supervisor_routing(state: AgentState) -> str:
    print(f"🚦 [Supervisor]: Reviewing compliance output ({len(state['compliance_flags'])} violations)...")
    if len(state["compliance_flags"]) > 0:
        return "REJECTED"
    return "APPROVED"

def block_action(state: AgentState):
    print("🛑 [Action Blocked]: Compliance rejected the NBA...")
    return {"final_decision": {"status": "blocked", "reason": state["compliance_flags"]}}

def approve_action(state: AgentState):
    print("✅ [Action Approved]: Executing NBA...")
    return {"final_decision": {"status": "approved", "action": state["proposed_nba"]}}

def run_agent_workflow(client_id: str):
    from dotenv import load_dotenv
    load_dotenv()
    
    client = load_client_profile(client_id)
    if not client:
        return
        
    initial_state = {
        "client_id": client_id,
        "portfolio": client["portfolio"],
        "risk_tolerance": client["risk_tolerance"],
        "goal": client["financial_goal"],
        "market_context": "",
        "proposed_nba": "",
        "compliance_flags": [],
        "final_decision": {}
    }

    # Build LangGraph
    workflow = StateGraph(AgentState)
    workflow.add_node("MarketAnalyst", market_analyst_agent)
    workflow.add_node("StrategyAgent", strategy_agent)
    workflow.add_node("ComplianceAgent", compliance_agent)
    workflow.add_node("Approve", approve_action)
    workflow.add_node("Block", block_action)

    # Edge Connections
    workflow.set_entry_point("MarketAnalyst")
    workflow.add_edge("MarketAnalyst", "StrategyAgent")
    workflow.add_edge("StrategyAgent", "ComplianceAgent")

    workflow.add_conditional_edges(
        "ComplianceAgent",
        supervisor_routing,
        {
            "APPROVED": "Approve",
            "REJECTED": "Block"
        }
    )

    workflow.add_edge("Approve", END)
    workflow.add_edge("Block", END)

    app = workflow.compile()
    print("\n--- 🚀 Running Multi-Agent Workflow ---")
    result = app.invoke(initial_state)
    print("\n--- 🏁 Workflow Complete ---")
    print(json.dumps(result["final_decision"], indent=2))

if __name__ == "__main__":
    run_agent_workflow("HSBC-WM-0001")
