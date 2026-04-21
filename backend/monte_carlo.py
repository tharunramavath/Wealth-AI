"""
Monte Carlo Simulation Engine
Generates 1,000+ possible future scenarios using Geometric Brownian Motion
Shows "Cone of Uncertainty" with probability distributions
"""

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


class MonteCarloEngine:
    def __init__(
        self,
        num_simulations: int = 1000,
        initial_value: float = 100000,
        risk_free_rate: float = 0.05
    ):
        self.num_simulations = num_simulations
        self.initial_value = initial_value
        self.risk_free_rate = risk_free_rate
        self.trading_days = 252
        
    def fetch_historical_data(self, ticker: str, days: int = 365) -> Optional[Dict]:
        """Fetch historical data and calculate returns, volatility."""
        try:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=days)
            
            hist = yf.Ticker(ticker).history(start=start_date, end=end_date, timeout=10)
            if hist is None or hist.empty or 'Close' not in hist.columns:
                return None
            
            closes = hist['Close'].dropna()
            if len(closes) < 30:
                return None
            
            returns = closes.pct_change().dropna()
            
            return {
                "prices": closes,
                "returns": returns,
                "current_price": closes.iloc[-1],
                "mean_return": returns.mean(),
                "std_return": returns.std(),
                "annualized_return": returns.mean() * self.trading_days,
                "annualized_vol": returns.std() * np.sqrt(self.trading_days),
            }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None
    
    def gbm_simulation(
        self,
        current_price: float,
        mu: float,
        sigma: float,
        days: int,
        num_paths: int = None
    ) -> np.ndarray:
        """
        Geometric Brownian Motion simulation.
        
        dS = μSdt + σSdW
        
        S(t) = S(0) * exp((μ - σ²/2)t + σW(t))
        
        Returns: Array of shape (num_simulations, days+1)
        """
        if num_paths is None:
            num_paths = self.num_simulations
            
        dt = 1 / self.trading_days
        num_steps = days
        
        Z = np.random.standard_normal((num_paths, num_steps))
        
        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt) * Z
        
        log_returns = drift + diffusion
        log_returns_cumulative = np.cumsum(log_returns, axis=1)
        
        paths = current_price * np.exp(np.column_stack([
            np.zeros(num_paths),
            log_returns_cumulative
        ]))
        
        return paths
    
    def gbm_with_jumps(
        self,
        current_price: float,
        mu: float,
        sigma: float,
        days: int,
        jump_prob: float = 0.001,
        jump_mean: float = -0.05,
        jump_std: float = 0.10
    ) -> np.ndarray:
        """
        GBM with Poisson jumps for crash scenarios.
        """
        dt = 1 / self.trading_days
        num_steps = days
        num_paths = self.num_simulations
        
        Z = np.random.standard_normal((num_paths, num_steps))
        jumps = np.random.poisson(jump_prob * dt, (num_paths, num_steps))
        jump_sizes = np.random.normal(jump_mean, jump_std, (num_paths, num_steps))
        
        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt) * Z
        
        log_returns = drift + diffusion + jumps * jump_sizes
        log_returns_cumulative = np.cumsum(log_returns, axis=1)
        
        paths = current_price * np.exp(np.column_stack([
            np.zeros(num_paths),
            log_returns_cumulative
        ]))
        
        return paths
    
    def run_simulation(
        self,
        holdings: List[Dict],
        horizon_days: int = 90,
        include_jumps: bool = True
    ) -> Dict:
        """
        Run Monte Carlo simulation for portfolio.
        
        Returns probability distributions and confidence intervals.
        """
        if not holdings:
            return {"error": "No holdings provided"}
        
        total_invested = sum(h.get("quantity", 0) * h.get("avg_price", 0) for h in holdings)
        if total_invested == 0:
            return {"error": "Total invested value is zero"}
        
        weights = {}
        stock_data = {}
        
        for h in holdings:
            ticker = h["ticker"]
            value = h.get("quantity", 0) * h.get("avg_price", 0)
            weights[ticker] = value / total_invested
            
            data = self.fetch_historical_data(ticker, days=365)
            if data:
                stock_data[ticker] = data
        
        if not stock_data:
            return {"error": "Could not fetch data for any holdings"}
        
        portfolio_paths = None
        initial_values = []
        
        for ticker, data in stock_data.items():
            weight = weights.get(ticker, 0)
            if weight == 0:
                continue
                
            initial_value = self.initial_value * weight
            
            if include_jumps:
                paths = self.gbm_with_jumps(
                    current_price=data["current_price"],
                    mu=data["annualized_return"],
                    sigma=data["annualized_vol"],
                    days=horizon_days
                )
            else:
                paths = self.gbm_simulation(
                    current_price=data["current_price"],
                    mu=data["annualized_return"],
                    sigma=data["annualized_vol"],
                    days=horizon_days
                )
            
            scaled_paths = paths * (initial_value / data["current_price"])
            
            if portfolio_paths is None:
                portfolio_paths = scaled_paths
            else:
                portfolio_paths = portfolio_paths + scaled_paths
            
            initial_values.append(initial_value)
        
        if portfolio_paths is None:
            return {"error": "Could not simulate any paths"}
        
        final_values = portfolio_paths[:, -1]
        initial_total = sum(initial_values)
        
        returns = (final_values - initial_total) / initial_total * 100
        
        percentiles = {
            "p5": np.percentile(final_values, 5),
            "p10": np.percentile(final_values, 10),
            "p25": np.percentile(final_values, 25),
            "p50": np.percentile(final_values, 50),
            "p75": np.percentile(final_values, 75),
            "p90": np.percentile(final_values, 90),
            "p95": np.percentile(final_values, 95),
        }
        
        probabilities = {
            "above_initial": (final_values >= initial_total).mean(),
            "above_10pct": (final_values >= initial_total * 1.10).mean(),
            "above_20pct": (final_values >= initial_total * 1.20).mean(),
            "below_initial": (final_values < initial_total).mean(),
            "below_10pct": (final_values < initial_total * 0.90).mean(),
            "below_20pct": (final_values < initial_total * 0.80).mean(),
        }
        
        expected_shortfall_5 = final_values[final_values <= np.percentile(final_values, 5)].mean()
        expected_shortfall_10 = final_values[final_values <= np.percentile(final_values, 10)].mean()
        
        percentiles_return = {
            k: round((v - initial_total) / initial_total * 100, 2) 
            for k, v in percentiles.items()
        }
        
        path_sample_indices = np.linspace(0, self.num_simulations - 1, 100).astype(int)
        sampled_paths = portfolio_paths[path_sample_indices]
        
        day_indices = np.linspace(0, horizon_days, min(30, horizon_days + 1)).astype(int)
        cone_data = {
            "days": day_indices.tolist(),
            "p5": [],
            "p25": [],
            "p50": [],
            "p75": [],
            "p95": []
        }
        
        for day in day_indices:
            values_at_day = portfolio_paths[:, day]
            cone_data["p5"].append(round(np.percentile(values_at_day, 5), 2))
            cone_data["p25"].append(round(np.percentile(values_at_day, 25), 2))
            cone_data["p50"].append(round(np.percentile(values_at_day, 50), 2))
            cone_data["p75"].append(round(np.percentile(values_at_day, 75), 2))
            cone_data["p95"].append(round(np.percentile(values_at_day, 95), 2))
        
        return {
            "config": {
                "num_simulations": self.num_simulations,
                "horizon_days": horizon_days,
                "initial_value": round(initial_total, 2),
                "include_jumps": include_jumps,
            },
            "statistics": {
                "mean_final": round(final_values.mean(), 2),
                "median_final": round(np.percentile(final_values, 50), 2),
                "std_final": round(final_values.std(), 2),
                "mean_return": round(returns.mean(), 2),
                "median_return": round(np.percentile(returns, 50), 2),
                "std_return": round(returns.std(), 2),
            },
            "percentiles_value": {k: round(v, 2) for k, v in percentiles.items()},
            "percentiles_return": percentiles_return,
            "probabilities": {k: round(v * 100, 2) for k, v in probabilities.items()},
            "expected_shortfall": {
                "at_5pct": round(expected_shortfall_5, 2),
                "at_10pct": round(expected_shortfall_10, 2),
                "avg_loss_at_5pct": round(initial_total - expected_shortfall_5, 2),
                "avg_loss_at_10pct": round(initial_total - expected_shortfall_10, 2),
            },
            "cone_of_uncertainty": cone_data,
            "sample_paths": sampled_paths[:, ::max(1, horizon_days // 20)].tolist(),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def compare_scenarios_mc(
        self,
        current_holdings: List[Dict],
        proposed_holdings: List[Dict],
        horizon_days: int = 90
    ) -> Dict:
        """Compare two scenarios using Monte Carlo."""
        current_sim = self.run_simulation(current_holdings, horizon_days) if current_holdings else None
        proposed_sim = self.run_simulation(proposed_holdings, horizon_days)
        
        if current_sim and "error" not in current_sim:
            current_stats = current_sim["statistics"]
            proposed_stats = proposed_sim.get("statistics", {})
            
            comparison = {
                "mean_return_change": round(
                    proposed_stats.get("mean_return", 0) - current_stats.get("mean_return", 0), 2
                ),
                "median_return_change": round(
                    proposed_stats.get("median_return", 0) - current_stats.get("median_return", 0), 2
                ),
                "risk_reduction": round(
                    current_stats.get("std_return", 0) - proposed_stats.get("std_return", 0), 2
                ),
                "prob_improvement": round(
                    proposed_sim["probabilities"]["above_initial"] - 
                    current_sim["probabilities"]["above_initial"], 2
                ) * 100,
            }
            
            winner = "proposed" if proposed_stats.get("median_return", 0) > current_stats.get("median_return", 0) else "current"
            if proposed_stats.get("median_return", 0) == current_stats.get("median_return", 0):
                winner = "tie"
        else:
            comparison = {}
            winner = "proposed"
        
        return {
            "horizon_days": horizon_days,
            "current": current_sim,
            "proposed": proposed_sim,
            "comparison": comparison,
            "recommendation": self._generate_recommendation(comparison, winner),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _generate_recommendation(self, comparison: Dict, winner: str) -> Dict:
        """Generate recommendation based on Monte Carlo comparison."""
        if winner == "current":
            return {
                "action": "KEEP_CURRENT",
                "message": "The proposed changes may not improve your risk-adjusted returns based on 1,000 simulations.",
                "confidence": "medium"
            }
        elif winner == "proposed":
            prob_better = comparison.get("prob_improvement", 0)
            if prob_better > 20:
                return {
                    "action": "IMPLEMENT",
                    "message": f"High confidence ({prob_better:.1f}% probability) that proposed changes improve outcomes.",
                    "confidence": "high"
                }
            elif prob_better > 10:
                return {
                    "action": "CONSIDER",
                    "message": f"Moderate confidence ({prob_better:.1f}% probability) that proposed changes improve outcomes.",
                    "confidence": "medium"
                }
            else:
                return {
                    "action": "CAUTION",
                    "message": "Low probability of improvement. Consider additional analysis.",
                    "confidence": "low"
                }
        else:
            return {
                "action": "NEUTRAL",
                "message": "Both scenarios show similar expected outcomes.",
                "confidence": "low"
            }


def quick_monte_carlo(tickers: List[str], weights: List[float], initial_value: float = 100000, horizon_days: int = 90) -> Dict:
    """Quick single-call Monte Carlo for a list of tickers."""
    holdings = [{"ticker": t, "quantity": w * 100, "avg_price": 100} for t, w in zip(tickers, weights)]
    engine = MonteCarloEngine(initial_value=initial_value)
    return engine.run_simulation(holdings, horizon_days)
