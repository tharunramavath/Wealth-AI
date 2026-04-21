"""
Backtest Engine - Path-Dependent Risk Metrics
Calculates: Max Drawdown, Volatility, Sortino Ratio, VaR, CVaR
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class BacktestEngine:
    def __init__(self, initial_value: float = 100000):
        self.initial_value = initial_value
        
    def fetch_price_series(self, ticker: str, start_date: datetime, end_date: datetime) -> Optional[pd.Series]:
        """Fetch daily close prices for a ticker with fallback."""
        try:
            hist = yf.Ticker(ticker).history(start=start_date, end=end_date, timeout=10)
            if hist is not None and not hist.empty and 'Close' in hist.columns:
                return hist['Close'].dropna()
        except Exception as e:
            print(f"[WARN] Error fetching {ticker}: {e}")
        
        # Fallback: try without end date
        try:
            hist = yf.download(ticker, start=start_date, period="6mo", progress=False)
            if hist is not None and not hist.empty:
                if 'Close' in hist.columns:
                    return hist['Close'].dropna()
                elif 'Adj Close' in hist.columns:
                    return hist['Adj Close'].dropna()
        except Exception as e:
            print(f"[WARN] Fallback failed for {ticker}: {e}")
        
        return None
    
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate daily returns from prices."""
        return prices.pct_change().dropna()
    
    def calculate_max_drawdown(self, prices: pd.Series) -> Tuple[float, datetime, datetime]:
        """
        Calculate maximum drawdown and its duration.
        Returns: (max_drawdown_pct, peak_date, trough_date)
        """
        running_max = prices.expanding().max()
        drawdown = (prices - running_max) / running_max
        max_dd = drawdown.min()
        
        trough_idx = drawdown.idxmin()
        peak_before_trough = prices[:trough_idx].idxmax()
        
        return max_dd * 100, peak_before_trough, trough_idx
    
    def calculate_drawdown_series(self, prices: pd.Series) -> pd.Series:
        """Calculate drawdown series for charting."""
        running_max = prices.expanding().max()
        return ((prices - running_max) / running_max * 100).dropna()
    
    def calculate_volatility(self, returns: pd.Series, annualize: bool = True) -> float:
        """Calculate annualized volatility."""
        vol = returns.std()
        if annualize:
            vol *= np.sqrt(252)  # Trading days per year
        return vol * 100
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """Calculate Sharpe Ratio. Uses lower risk-free rate (3%) for better representation."""
        if len(returns) < 2:
            return 0.0
        annualized_return = returns.mean() * 252
        annualized_vol = returns.std() * np.sqrt(252)
        if annualized_vol == 0:
            return 0.0
        excess_return = annualized_return - risk_free_rate
        return excess_return / annualized_vol
    
    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.03, target_return: float = 0) -> float:
        """Calculate Sortino Ratio (downside risk adjusted)."""
        if len(returns) < 2:
            return 0.0
        annualized_return = returns.mean() * 252
        downside_returns = returns[returns < target_return]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        if downside_std == 0:
            return 0
        excess_return = annualized_return - risk_free_rate
        return excess_return / downside_std
    
    def calculate_var_cvar(self, returns: pd.Series, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate Value at Risk and Conditional VaR.
        VaR: Maximum expected loss at given confidence level
        CVaR: Expected loss given that loss exceeds VaR
        """
        var_level = 1 - confidence
        var = np.percentile(returns, var_level * 100) * 100
        cvar = returns[returns <= var_level].mean() * 100
        return var, cvar
    
    def calculate_calmar_ratio(self, returns: pd.Series, prices: pd.Series) -> float:
        """Calculate Calmar Ratio (return / max drawdown)."""
        if len(returns) < 2:
            return 0.0
        total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
        max_dd, _, _ = self.calculate_max_drawdown(prices)
        return abs(total_return / max_dd) if max_dd != 0 else 0
    
    def calculate_win_rate(self, returns: pd.Series) -> float:
        """Calculate percentage of positive return days."""
        if len(returns) == 0:
            return 0.0
        return (returns > 0).sum() / len(returns) * 100
    
    def calculate_profit_factor(self, returns: pd.Series) -> float:
        """Calculate ratio of gross profits to gross losses."""
        gains = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        return gains / losses if losses != 0 else float('inf') if gains > 0 else 0
    
    def calculate_rolling_sharpe(self, returns: pd.Series, window: int = 20) -> pd.Series:
        """Calculate rolling Sharpe ratio."""
        rolling_mean = returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()
        return np.sqrt(252) * rolling_mean / rolling_std
    
    def run_backtest(self, holdings: List[Dict], period: str = "6M") -> Dict:
        """
        Run comprehensive backtest on portfolio holdings.
        
        Args:
            holdings: List of dicts with {ticker, quantity, avg_price}
            period: "1M", "3M", "6M", "1Y"
            
        Returns:
            Dict with comprehensive metrics
        """
        period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}.get(period, 180)
        end_date = datetime.today()
        start_date = end_date - timedelta(days=period_days)
        
        if not holdings:
            return {"error": "No holdings provided"}
        
        total_invested = sum(h.get("quantity", 0) * h.get("avg_price", 0) for h in holdings)
        if total_invested == 0:
            return {"error": "Total invested value is zero"}
        
        weights = {}
        for h in holdings:
            value = h.get("quantity", 0) * h.get("avg_price", 0)
            weights[h["ticker"]] = value / total_invested
        
        stock_data = {}
        for ticker in weights:
            prices = self.fetch_price_series(ticker, start_date, end_date)
            if prices is not None and len(prices) > 5:
                returns = self.calculate_returns(prices)
                stock_data[ticker] = {
                    "prices": prices,
                    "returns": returns,
                    "weight": weights[ticker]
                }
        
        if not stock_data:
            print(f"[ERROR] Backtest failed: Could not fetch data for holdings: {[h['ticker'] for h in holdings]}")
            return {"error": "Could not fetch data for holdings. Check if tickers are valid."}
        
        portfolio_prices = None
        portfolio_returns_list = []
        
        for ticker, data in stock_data.items():
            if portfolio_prices is None:
                portfolio_prices = data["prices"] * data["weight"]
            else:
                portfolio_prices = portfolio_prices.add(data["prices"] * data["weight"], fill_value=0)
            portfolio_returns_list.append(data["returns"] * data["weight"])
        
        portfolio_returns = pd.concat(portfolio_returns_list, axis=1).sum(axis=1).dropna()
        
        max_dd, peak_date, trough_date = self.calculate_max_drawdown(portfolio_prices)
        drawdown_series = self.calculate_drawdown_series(portfolio_prices)
        volatility = self.calculate_volatility(portfolio_returns)
        sharpe = self.calculate_sharpe_ratio(portfolio_returns)
        sortino = self.calculate_sortino_ratio(portfolio_returns)
        var_95, cvar_95 = self.calculate_var_cvar(portfolio_returns, 0.95)
        var_99, cvar_99 = self.calculate_var_cvar(portfolio_returns, 0.99)
        calmar = self.calculate_calmar_ratio(portfolio_returns, portfolio_prices)
        win_rate = self.calculate_win_rate(portfolio_returns)
        profit_factor = self.calculate_profit_factor(portfolio_returns)
        
        total_return = (portfolio_prices.iloc[-1] / portfolio_prices.iloc[0] - 1) * 100 if len(portfolio_prices) > 1 else 0
        annualized_return = ((1 + total_return / 100) ** (365 / period_days) - 1) * 100 if period_days > 0 else 0
        
        best_day = portfolio_returns.max() * 100 if len(portfolio_returns) > 0 else 0
        worst_day = portfolio_returns.min() * 100 if len(portfolio_returns) > 0 else 0
        
        rolling_sharpe = self.calculate_rolling_sharpe(portfolio_returns, min(20, len(portfolio_returns)))
        avg_rolling_sharpe = rolling_sharpe.dropna().mean() if len(rolling_sharpe.dropna()) > 0 else 0
        
        holdings_performance = []
        for ticker, data in stock_data.items():
            ticker_return = (data["prices"].iloc[-1] / data["prices"].iloc[0] - 1) * 100 if len(data["prices"]) > 1 else 0
            holdings_performance.append({
                "ticker": ticker,
                "return": round(ticker_return, 2),
                "weight": round(data["weight"] * 100, 2),
                "contribution": round(ticker_return * data["weight"], 2)
            })
        
        return {
            "period": period,
            "period_days": period_days,
            "start_date": str(start_date.date()),
            "end_date": str(end_date.date()),
            "data_points": len(portfolio_returns),
            "summary": {
                "total_return": round(total_return, 2),
                "annualized_return": round(annualized_return, 2),
                "volatility": round(volatility, 2),
                "sharpe_ratio": round(sharpe, 2),
                "sortino_ratio": round(sortino, 2),
                "calmar_ratio": round(calmar, 2),
                "max_drawdown": round(max_dd, 2),
                "max_drawdown_peak": str(peak_date.date()) if peak_date else None,
                "max_drawdown_trough": str(trough_date.date()) if trough_date else None,
                "var_95": round(var_95, 2),
                "cvar_95": round(cvar_95, 2),
                "var_99": round(var_99, 2),
                "cvar_99": round(cvar_99, 2),
                "win_rate": round(win_rate, 2),
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "inf",
                "best_day": round(best_day, 2),
                "worst_day": round(worst_day, 2),
            },
            "holdings_performance": sorted(holdings_performance, key=lambda x: x["return"], reverse=True),
            "path_metrics": {
                "daily_returns": portfolio_returns.tolist()[-90:] if len(portfolio_returns) > 90 else portfolio_returns.tolist(),
                "drawdown_series": drawdown_series.tolist()[-90:] if len(drawdown_series) > 90 else drawdown_series.tolist(),
                "price_series": portfolio_prices.tolist()[-90:] if len(portfolio_prices) > 90 else portfolio_prices.tolist(),
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


def compare_scenarios(current_holdings: List[Dict], proposed_holdings: List[Dict], period: str = "6M") -> Dict:
    """Compare two portfolio scenarios."""
    engine = BacktestEngine()
    
    current_result = engine.run_backtest(current_holdings, period) if current_holdings else None
    proposed_result = engine.run_backtest(proposed_holdings, period)
    
    if current_result and "error" not in current_result:
        current_metrics = current_result["summary"]
        proposed_metrics = proposed_result["summary"] if "error" not in proposed_result else {}
        
        impact = {
            "return_change": round(proposed_metrics.get("total_return", 0) - current_metrics.get("total_return", 0), 2),
            "volatility_change": round(proposed_metrics.get("volatility", 0) - current_metrics.get("volatility", 0), 2),
            "sharpe_change": round(proposed_metrics.get("sharpe_ratio", 0) - current_metrics.get("sharpe_ratio", 0), 2),
            "max_dd_change": round(proposed_metrics.get("max_drawdown", 0) - current_metrics.get("max_drawdown", 0), 2),
            "sharpe_improvement": "better" if proposed_metrics.get("sharpe_ratio", 0) > current_metrics.get("sharpe_ratio", 0) else "worse",
            "risk_improvement": "better" if proposed_metrics.get("max_drawdown", 0) < current_metrics.get("max_drawdown", 0) else "worse",
        }
    else:
        impact = {"error": "Could not compare scenarios"}
        current_metrics = current_result["summary"] if current_result and "error" not in current_result else {}
    
    return {
        "period": period,
        "current": current_result,
        "proposed": proposed_result,
        "impact": impact,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
