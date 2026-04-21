import yfinance as yf
from typing import Optional, Dict, Any

QUOTE_TYPE_MAP = {
    "EQUITY": "Stock",
    "ETF": "ETF",
    "MUTUALFUND": "Mutual Fund",
    "CRYPTOCURRENCY": "Crypto",
    "INDEX": "Index",
    "CURRENCY": "Forex",
    "OPTION": "Option",
    " futures": "Futures",
    "WARRANT": "Warrant",
    "BOND": "Bond",
    "COMMODITY": "Commodity",
}

EXCHANGE_MAP = {
    "NasdaqGS": "NASDAQ",
    "NasdaqGM": "NASDAQ",
    "NasdaqG": "NASDAQ",
    "NYSE": "NYSE",
    "AMEX": "AMEX",
    "BSE": "BSE",
    "NSE": "NSE",
    "LSE": "LSE",
    "HKEX": "HKEX",
    "JPX": "JPX",
    "TSX": "TSX",
    "ASX": "ASX",
}


def get_asset_metadata(ticker: str) -> Dict[str, Any]:
    """
    Fetch asset metadata from Yahoo Finance and enrich with additional fields.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'RELIANCE.NS')
    
    Returns:
        Dict containing enriched asset metadata
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        if not info or info.get("symbol") is None:
            return {
                "ticker": ticker.upper(),
                "company_name": ticker.upper(),
                "asset_type": "Stock",
                "sector": "Unknown",
                "industry": "Unknown",
                "exchange": "Unknown",
                "currency": "USD",
                "error": "Unable to fetch metadata"
            }
        
        quote_type = info.get("quoteType", "EQUITY")
        asset_type = QUOTE_TYPE_MAP.get(quote_type, "Stock")
        
        raw_exchange = info.get("exchange", "Unknown")
        exchange = EXCHANGE_MAP.get(raw_exchange, raw_exchange)
        
        return {
            "ticker": info.get("symbol", ticker.upper()),
            "company_name": info.get("longName") or info.get("shortName") or ticker.upper(),
            "asset_type": asset_type,
            "sector": info.get("sector") or "Unknown",
            "industry": info.get("industry") or "Unknown",
            "exchange": exchange,
            "currency": info.get("currency") or "USD",
        }
        
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "company_name": ticker.upper(),
            "asset_type": "Stock",
            "sector": "Unknown",
            "industry": "Unknown",
            "exchange": "Unknown",
            "currency": "USD",
            "error": str(e)
        }


def validate_ticker(ticker: str) -> bool:
    """Validate if a ticker exists in Yahoo Finance."""
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period="1d", timeout=5)
        return hist is not None and not hist.empty
    except Exception:
        return False


def search_tickers(query: str) -> list:
    """Search for tickers using Yahoo Finance."""
    try:
        results = yf.Search(query, max_results=10).quotes
        if results:
            return [
                {
                    "symbol": r["symbol"],
                    "name": r.get("shortname") or r.get("longname"),
                    "exchange": r.get("exchange")
                }
                for r in results
            ]
    except Exception:
        pass
    return []
