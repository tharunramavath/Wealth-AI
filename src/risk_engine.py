import pandas as pd
import numpy as np

def calculate_portfolio_risk(client_portfolio: dict) -> dict:
    """
    Computes real-time risk metrics for a client portfolio based on the last 90 days.
    Required metrics: Sharpe Ratio, Volatility, Beta (vs SPY), and Max Drawdown.
    """
    # Exclude non-tradeable assets like Cash from the metric calculations
    tradeable_assets = [ticker for ticker in client_portfolio.keys() if ticker != "Cash"]
    
    try:
        prices = pd.read_csv("data/raw/prices.csv", index_col=0, parse_dates=True)
    except FileNotFoundError:
        return {"error": "Run pipeline step 1 first. data/raw/prices.csv is missing."}

    # Ensure all required assets are in the data
    available_assets = [t for t in tradeable_assets if t in prices.columns]
    
    if len(available_assets) == 0:
        return {"volatility": 0.0, "sharpe_ratio": 0.0, "beta": 0.0, "max_drawdown": 0.0, "note": "All assets in cash or no price data"}

    # Rescale weights for the available tradeable portion
    sub_weights = [client_portfolio[t] for t in available_assets]
    weight_sum = sum(sub_weights)
    if weight_sum == 0:
        return {}
    
    norm_weights = np.array([w / weight_sum for w in sub_weights])
    
    # Calculate Daily Returns
    returns = prices[available_assets].pct_change().dropna()
    portfolio_returns = returns.dot(norm_weights)

    # Risk Metrics
    # 1. Volatility (Annualized)
    daily_vol = portfolio_returns.std()
    ann_volatility = daily_vol * np.sqrt(252)

    # 2. Sharpe Ratio (Assumes 3% risk-free rate)
    rf_daily = 0.03 / 252
    excess_returns = portfolio_returns - rf_daily
    if daily_vol > 0:
        sharpe = (excess_returns.mean() / daily_vol) * np.sqrt(252)
    else:
        sharpe = 0.0

    # 3. Max Drawdown
    cumulative_returns = (1 + portfolio_returns).cumprod()
    peak = cumulative_returns.cummax()
    drawdown = (cumulative_returns - peak) / peak
    max_drawdown = drawdown.min()

    # 4. Beta vs Benchmark (SPY)
    beta = 1.0 # Default fallback
    if "SPY" in prices.columns:
        spy_returns = prices["SPY"].pct_change().dropna()
        # Align index
        aligned = pd.concat([portfolio_returns, spy_returns], axis=1, join='inner')
        aligned.columns = ['Port', 'SPY']
        if len(aligned) > 0 and aligned['SPY'].var() > 0:
            cov = aligned.cov().iloc[0, 1]
            var = aligned['SPY'].var()
            beta = cov / var

    return {
        "volatility": round(ann_volatility, 3),
        "sharpe_ratio": round(sharpe, 3),
        "beta": round(beta, 3),
        "max_drawdown": round(max_drawdown, 3)
    }

if __name__ == "__main__":
    from src.compliance import load_client_profile
    client = load_client_profile("HSBC-WM-0002") # Aggressive
    if client:
        print(f"Risk Profile for {client['name']} (Aggressive):")
        metrics = calculate_portfolio_risk(client["portfolio"])
        for k, v in metrics.items():
            print(f"  {k:15s} : {v}")
