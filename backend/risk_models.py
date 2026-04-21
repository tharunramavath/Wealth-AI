"""
Dynamic Risk Models
- Regime Detection (Normal vs Crisis)
- Dynamic Correlation Matrices
- Stress Testing with Crisis Scenarios
- Comprehensive Risk Scoring
"""

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')


class MarketRegimeDetector:
    """Detect market regimes (bull, bear, high volatility)."""
    
    REGIMES = {
        "BULL_NORMAL": {"emoji": "🟢", "description": "Low volatility bull market"},
        "BULL_HIGH_VOL": {"emoji": "🟡", "description": "High volatility bull market"},
        "BEAR_NORMAL": {"emoji": "🔴", "description": "Moderate bear market"},
        "BEAR_HIGH_VOL": {"emoji": "🚨", "description": "High volatility crash"},
        "SIDEWAYS": {"emoji": "⚪", "description": "Ranging market"},
    }
    
    def __init__(self):
        self.sp500 = yf.Ticker("SPY")
        
    def detect_regime(self, lookback_days: int = 90) -> Dict:
        """Detect current market regime."""
        try:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=lookback_days)
            
            hist = self.sp500.history(start=start_date, end=end_date, timeout=10)
            if hist is None or hist.empty or 'Close' not in hist.columns:
                return self._default_regime()
            
            closes = hist['Close'].dropna()
            returns = closes.pct_change().dropna()
            
            if len(returns) < 20:
                return self._default_regime()
            
            volatility = returns.std() * np.sqrt(252) * 100
            recent_return = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
            trend = "BULL" if closes.iloc[-1] > closes.iloc[0] else "BEAR"
            
            avg_vol = 0.15
            vol_threshold_high = avg_vol * 1.5
            vol_threshold_very_high = avg_vol * 2.0
            
            if trend == "BULL":
                if volatility > vol_threshold_very_high:
                    regime = "BULL_HIGH_VOL"
                else:
                    regime = "BULL_NORMAL"
            else:
                if volatility > vol_threshold_high:
                    regime = "BEAR_HIGH_VOL"
                else:
                    regime = "BEAR_NORMAL"
            
            if abs(recent_return) < 5:
                regime = "SIDEWAYS"
            
            return {
                "regime": regime,
                "emoji": self.REGIMES[regime]["emoji"],
                "description": self.REGIMES[regime]["description"],
                "metrics": {
                    "volatility": round(volatility, 2),
                    "recent_return": round(recent_return, 2),
                    "trend": trend,
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Regime detection error: {e}")
            return self._default_regime()
    
    def _default_regime(self) -> Dict:
        return {
            "regime": "SIDEWAYS",
            "emoji": "⚪",
            "description": "Market regime unknown",
            "metrics": {"volatility": 15, "recent_return": 0, "trend": "SIDEWAYS"},
            "timestamp": datetime.now().isoformat()
        }


class DynamicCorrelationModel:
    """Calculate correlations with regime-aware adjustments."""
    
    def __init__(self):
        self.base_correlation = {
            ("Technology", "Technology"): 0.85,
            ("Financials", "Financials"): 0.80,
            ("Energy", "Energy"): 0.75,
            ("Technology", "Communication Services"): 0.70,
            ("Financials", "Technology"): 0.60,
            ("Energy", "Technology"): 0.40,
        }
        self.crisis_correlation_multiplier = 1.5
        
    def get_correlation(self, sector1: str, sector2: str, regime: str) -> float:
        """Get correlation adjusted for market regime."""
        key = tuple(sorted([sector1, sector2]))
        base = self.base_correlation.get(key, 0.50)
        
        if "CRISIS" in regime or "BEAR_HIGH" in regime:
            base = min(1.0, base * self.crisis_correlation_multiplier)
        
        if sector1 == sector2:
            base = 0.90
        
        return round(base, 3)
    
    def build_correlation_matrix(self, tickers: List[str], sectors: List[str], regime: str) -> pd.DataFrame:
        """Build correlation matrix for tickers."""
        n = len(tickers)
        matrix = np.eye(n)
        
        for i in range(n):
            for j in range(i + 1, n):
                corr = self.get_correlation(sectors[i], sectors[j], regime)
                matrix[i, j] = corr
                matrix[j, i] = corr
        
        df = pd.DataFrame(matrix, index=tickers, columns=tickers)
        return df


class StressTestEngine:
    """Run stress tests on portfolios under crisis scenarios."""
    
    SCENARIOS = {
        "2008_CRISIS": {
            "name": "2008 Financial Crisis",
            "shock_multiplier": 0.65,
            "vol_multiplier": 2.5,
            "correlation_shift": 1.0,
            "recovery_days": 730,
        },
        "COVID_2020": {
            "name": "COVID Crash",
            "shock_multiplier": 0.70,
            "vol_multiplier": 3.0,
            "correlation_shift": 1.0,
            "recovery_days": 365,
        },
        "DOTCOM_2000": {
            "name": "Dot-com Bubble",
            "shock_multiplier": 0.50,
            "vol_multiplier": 2.0,
            "correlation_shift": 0.7,
            "recovery_days": 1460,
        },
        "RATE_HIKE": {
            "name": "Interest Rate Hike",
            "shock_multiplier": 0.85,
            "vol_multiplier": 1.8,
            "correlation_shift": 0.8,
            "recovery_days": 365,
        },
        "INFLATION_2022": {
            "name": "Inflation Shock 2022",
            "shock_multiplier": 0.80,
            "vol_multiplier": 2.2,
            "correlation_shift": 0.9,
            "recovery_days": 730,
        },
        "SECTOR_ROTATION": {
            "name": "Sector Rotation",
            "shock_multiplier": 0.90,
            "vol_multiplier": 1.5,
            "correlation_shift": 0.6,
            "recovery_days": 180,
        },
    }
    
    def run_stress_test(self, holdings: List[Dict], scenario_name: str = "2008_CRISIS") -> Dict:
        """Run stress test for a specific scenario."""
        scenario = self.SCENARIOS.get(scenario_name, self.SCENARIOS["2008_CRISIS"])
        
        if not holdings:
            return {"error": "No holdings provided"}
        
        total_value = sum(h.get("quantity", 0) * h.get("avg_price", 0) for h in holdings)
        if total_value == 0:
            return {"error": "Total value is zero"}
        
        results = []
        for h in holdings:
            ticker = h["ticker"]
            quantity = h.get("quantity", 0)
            avg_price = h.get("avg_price", 0)
            sector = h.get("sector", "Unknown")
            
            base_value = quantity * avg_price
            shock_value = base_value * scenario["shock_multiplier"]
            loss = base_value - shock_value
            
            volatility_factor = self._get_sector_volatility(sector)
            stressed_vol = volatility_factor * scenario["vol_multiplier"]
            
            results.append({
                "ticker": ticker,
                "sector": sector,
                "base_value": round(base_value, 2),
                "stressed_value": round(shock_value, 2),
                "absolute_loss": round(loss, 2),
                "percentage_loss": round((1 - scenario["shock_multiplier"]) * 100, 2),
                "stressed_volatility": round(stressed_vol, 2),
            })
        
        total_base = sum(r["base_value"] for r in results)
        total_stressed = sum(r["stressed_value"] for r in results)
        total_loss = total_base - total_stressed
        
        sector_losses = defaultdict(float)
        for r in results:
            sector_losses[r["sector"]] += r["absolute_loss"]
        
        worst_case = max(results, key=lambda x: x["percentage_loss"]) if results else None
        
        return {
            "scenario": scenario_name,
            "scenario_name": scenario["name"],
            "portfolio_summary": {
                "total_base_value": round(total_base, 2),
                "total_stressed_value": round(total_stressed, 2),
                "total_loss": round(total_loss, 2),
                "total_loss_pct": round((total_loss / total_base) * 100, 2) if total_base > 0 else 0,
                "recovery_days": scenario["recovery_days"],
            },
            "holdings_impact": sorted(results, key=lambda x: x["percentage_loss"], reverse=True),
            "sector_impact": {k: round(v, 2) for k, v in sector_losses.items()},
            "worst_holding": worst_case,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def run_all_stress_tests(self, holdings: List[Dict]) -> Dict:
        """Run all stress test scenarios."""
        all_results = {}
        for scenario_name in self.SCENARIOS:
            result = self.run_stress_test(holdings, scenario_name)
            if "error" not in result:
                all_results[scenario_name] = {
                    "scenario_name": result["scenario_name"],
                    "total_loss_pct": result["portfolio_summary"]["total_loss_pct"],
                    "total_loss": result["portfolio_summary"]["total_loss"],
                }
        
        worst_scenario = min(all_results.items(), key=lambda x: x[1]["total_loss_pct"]) if all_results else (None, {})
        
        return {
            "all_scenarios": all_results,
            "worst_case": {
                "scenario": worst_scenario[0] if worst_scenario[0] else "N/A",
                "scenario_name": worst_scenario[1].get("scenario_name", "N/A") if worst_scenario[1] else "N/A",
                "total_loss_pct": worst_scenario[1].get("total_loss_pct", 0) if worst_scenario[1] else 0,
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _get_sector_volatility(self, sector: str) -> float:
        """Get base sector volatility."""
        volatility_map = {
            "Technology": 0.28,
            "Financials": 0.22,
            "Energy": 0.25,
            "Healthcare": 0.18,
            "Consumer": 0.20,
            "Real Estate": 0.24,
            "Utilities": 0.15,
            "Materials": 0.23,
            "Industrials": 0.21,
            "Communication Services": 0.26,
            "Unknown": 0.22,
        }
        return volatility_map.get(sector, 0.22)


class RiskScorer:
    """Calculate comprehensive risk scores."""
    
    def __init__(self):
        self.max_score = 100
        
    def calculate_risk_score(self, holdings: List[Dict], returns: Optional[pd.Series] = None) -> Dict:
        """Calculate comprehensive risk score (0-100)."""
        if not holdings:
            return {"error": "No holdings"}
        
        scores = {
            "concentration_risk": self._concentration_score(holdings),
            "volatility_risk": self._volatility_score(holdings),
            "correlation_risk": self._correlation_score(holdings),
            "sector_risk": self._sector_score(holdings),
        }
        
        if returns is not None and len(returns) > 20:
            scores["drawdown_risk"] = self._drawdown_score(returns)
            scores["tail_risk"] = self._tail_risk_score(returns)
        
        total_score = sum(scores.values()) / len(scores)
        
        risk_level = "LOW"
        if total_score > 60:
            risk_level = "HIGH"
        elif total_score > 40:
            risk_level = "MEDIUM"
        
        return {
            "overall_score": round(total_score, 1),
            "risk_level": risk_level,
            "components": {k: round(v, 1) for k, v in scores.items()},
            "recommendations": self._get_recommendations(scores),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _concentration_score(self, holdings: List[Dict]) -> float:
        """Score based on position concentration."""
        total = sum(h.get("quantity", 0) * h.get("avg_price", 0) for h in holdings)
        if total == 0:
            return 50
        
        weights = [(h.get("quantity", 0) * h.get("avg_price", 0)) / total for h in holdings]
        max_weight = max(weights) * 100
        
        if max_weight > 50:
            return 80
        elif max_weight > 30:
            return 60
        elif max_weight > 20:
            return 40
        return 20
    
    def _volatility_score(self, holdings: List[Dict]) -> float:
        """Score based on holding volatility estimates."""
        sector_vol = {
            "Technology": 0.28, "Financials": 0.22, "Energy": 0.25,
            "Healthcare": 0.18, "Consumer": 0.20, "Unknown": 0.22
        }
        
        total_weighted_vol = 0
        total_weight = 0
        
        for h in holdings:
            sector = h.get("sector", "Unknown")
            vol = sector_vol.get(sector, 0.22)
            value = h.get("quantity", 0) * h.get("avg_price", 0)
            total_weighted_vol += vol * value
            total_weight += value
        
        if total_weight == 0:
            return 50
        
        avg_vol = total_weighted_vol / total_weight
        return min(100, avg_vol * 300)
    
    def _correlation_score(self, holdings: List[Dict]) -> float:
        """Score based on sector correlation."""
        sectors = [h.get("sector", "Unknown") for h in holdings]
        unique_sectors = set(sectors)
        
        if len(unique_sectors) >= 5:
            return 20
        elif len(unique_sectors) >= 3:
            return 40
        elif len(unique_sectors) == 2:
            return 60
        return 80
    
    def _sector_score(self, holdings: List[Dict]) -> float:
        """Score based on sector distribution."""
        total = sum(h.get("quantity", 0) * h.get("avg_price", 0) for h in holdings)
        if total == 0:
            return 50
        
        sector_values = defaultdict(float)
        for h in holdings:
            sector = h.get("sector", "Unknown")
            sector_values[sector] += h.get("quantity", 0) * h.get("avg_price", 0)
        
        sector_weights = {k: v / total for k, v in sector_values.items()}
        max_weight = max(sector_weights.values())
        
        return max_weight * 100
    
    def _drawdown_score(self, returns: pd.Series) -> float:
        """Score based on historical drawdowns."""
        if len(returns) < 2:
            return 50
        
        prices = (1 + returns).cumprod()
        running_max = prices.cummax()
        drawdowns = (prices - running_max) / running_max
        max_dd = abs(drawdowns.min())
        
        if max_dd > 0.3:
            return 90
        elif max_dd > 0.2:
            return 70
        elif max_dd > 0.1:
            return 50
        return 30
    
    def _tail_risk_score(self, returns: pd.Series) -> float:
        """Score based on tail risk (skewness and kurtosis)."""
        if len(returns) < 20:
            return 50
        
        skew = returns.skew()
        kurt = returns.kurtosis()
        
        tail_score = 50
        if kurt > 3:
            tail_score += 20
        if abs(skew) > 0.5:
            tail_score += 10
        
        return min(100, tail_score)
    
    def _get_recommendations(self, scores: Dict) -> List[str]:
        """Generate recommendations based on risk scores."""
        recs = []
        if scores.get("concentration_risk", 0) > 60:
            recs.append("Reduce position concentration - consider rebalancing")
        if scores.get("correlation_risk", 0) > 60:
            recs.append("Add uncorrelated assets to reduce portfolio correlation")
        if scores.get("sector_risk", 0) > 60:
            recs.append("Diversify across more sectors")
        if scores.get("drawdown_risk", 0) > 70:
            recs.append("Consider adding defensive positions (bonds, utilities)")
        if scores.get("volatility_risk", 0) > 70:
            recs.append("High volatility - consider hedging strategies")
        return recs if recs else ["Portfolio risk appears well-managed"]


def comprehensive_risk_analysis(holdings: List[Dict], returns: Optional[pd.Series] = None) -> Dict:
    """Run comprehensive risk analysis combining all models."""
    regime_detector = MarketRegimeDetector()
    stress_engine = StressTestEngine()
    risk_scorer = RiskScorer()
    
    regime = regime_detector.detect_regime()
    stress_results = stress_engine.run_all_stress_tests(holdings)
    risk_score = risk_scorer.calculate_risk_score(holdings, returns)
    
    return {
        "market_regime": regime,
        "stress_tests": stress_results,
        "risk_score": risk_score,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
