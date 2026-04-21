import os
import json
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def load_client_profile(client_id: str) -> Dict[str, Any]:
    try:
        with open("data/clients/client_profiles.json", "r") as f:
            profiles = json.load(f)
            
        for p in profiles:
            if p["client_id"] == client_id:
                return p
        logging.warning(f"Client {client_id} not found.")
        return {}
        
    except FileNotFoundError:
        logging.error("data/clients/client_profiles.json not found.")
        return {}

def enforce_compliance(risk_tolerance: str, portfolio: Dict[str, float], next_best_action: str) -> List[str]:
    """
    Rule-based hard guardrails for financial recommendations.
    Returns a list of compliance violation messages (or empty list if passed).
    """
    violations = []
    
    # Example Rule 1: Conservative Risk Limits
    if risk_tolerance == "Conservative":
        equity_exposure = sum(weight for asset, weight in portfolio.items() if asset not in ["Cash", "GOLDBEES.NS", "LIQUIDBEES.NS", "TLT"])
        if equity_exposure > 0.40:
            violations.append(f"Conservative Client Rule Violation: Existing equity exposure ({equity_exposure:.1%}) exceeds 40% limit.")
            
        # Do not recommend high-volatility assets if conservative
        if any(kw in next_best_action.lower() for kw in ["crypto", "bitcoin", "options", "leveraged", "penny"]):
            violations.append("Conservative Client Rule Violation: Recommendation contains blocked high-risk asset classes.")

    # Example Rule 2: Illiquid Assets
    if risk_tolerance == "Low" and any(kw in next_best_action.lower() for kw in ["private equity", "vc", "real estate fund"]):
            violations.append("Liquidity Rule Violation: Client requires high liquidity but recommendation contains illiquid asset mentions.")

    # Example Rule 3: No direct naked shorting without compliance desk review
    if "short" in next_best_action.lower() and "sell short" in next_best_action.lower():
         violations.append("Firm Protocol Violation: Short selling requires margin approval and cannot be automated.")
         
    return violations


def validate_tickers(recommendation_text: str, allowed_tickers: List[str] = None) -> List[str]:
    """
    Checks for LLM 'hallucinated' tickers by scanning for stock ticker patterns (e.g. MSFT, AAPL, RELIANCE.NS)
    and flagging if they are not real ones.
    """
    import re
    
    # Try to find things that look like uppercase stock tickers: 1 to 5 uppercase characters, optionally followed by .NS or similar
    # This is a basic regex; tuning depends on specific markets
    potential_tickers = re.findall(r'\b[A-Z]{1,5}(?:\.[A-Z]{1,2})?\b', recommendation_text)
    
    # Remove common words that are all caps but not tickers
    common_acronyms = {"THE", "AND", "OR", "IT", "IN", "ON", "AT", "TO", "A", "I", "US", "UK", "UAE", "AI", "ESG", "CEO", "CFO", "Q1", "Q2", "Q3", "Q4", "ETF", "NAV"}
    potential_tickers = [t for t in potential_tickers if t not in common_acronyms]
    
    if not potential_tickers or not allowed_tickers:
        return []
    
    # Check against valid ones
    hallucinations = []
    for t in potential_tickers:
       # basic substring match, skipping check for some base symbols to avoid false positives
       # In a real app, this would hit a DB table of all known world equities.
       if t not in allowed_tickers and not any(t in allowed for allowed in allowed_tickers):
           # Simple heuristic: if it's 2 chars, might just be a word.
           if len(t) > 2:
               hallucinations.append(t)
               
    verbage = [f"Flagging possible hallucinated ticker: {h}" for h in set(hallucinations)]
    return verbage
