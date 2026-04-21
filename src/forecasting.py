"""
Time Series Forecasting Module
- GARCH: Volatility forecasting
- Prophet: Price trend forecasting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False
    print("arch package not installed. Install with: pip install arch")

try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    try:
        from prophet import Prophet
        HAS_PROPHET = True
    except ImportError:
        HAS_PROPHET = False
        print("prophet package not installed. Install with: pip install prophet")


def forecast_volatility_garch(returns: pd.Series, horizon: int = 30) -> dict:
    """
    Forecast volatility using GARCH(1,1) model.
    
    Args:
        returns: Daily returns series
        horizon: Forecast horizon in days
    
    Returns:
        Dictionary with volatility forecasts and confidence intervals
    """
    if not HAS_ARCH:
        return {
            "error": "GARCH model not available. Install arch package: pip install arch",
            "method": "GARCH"
        }
    
    try:
        returns_clean = returns.dropna()
        if len(returns_clean) < 50:
            return {
                "error": "Insufficient data for GARCH. Need at least 50 days.",
                "method": "GARCH"
            }
        
        model = arch_model(returns_clean * 100, vol='Garch', p=1, q=1, dist='normal')
        result = model.fit(disp='off')
        
        forecast = result.forecast(horizon=horizon, reindex=False)
        variance_forecast = forecast.variance.iloc[-1].values
        volatility_forecast = np.sqrt(variance_forecast) / 100
        
        daily_vol = volatility_forecast
        annual_vol = volatility_forecast * np.sqrt(252)
        
        current_vol = result.conditional_volatility.iloc[-1] / 100
        
        return {
            "method": "GARCH(1,1)",
            "current_volatility": round(current_vol * 100, 2),
            "forecast_horizon": horizon,
            "daily_volatility": [round(v * 100, 4) for v in daily_vol],
            "annual_volatility": [round(v * 100, 2) for v in annual_vol],
            "mean_forecast_vol": round(np.mean(annual_vol) * 100, 2),
            "dates": [(datetime.today() + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(horizon)],
            "interpretation": _interpret_volatility(np.mean(annual_vol)),
            "model_params": {
                "alpha": round(result.params.get('alpha[1]', 0), 4),
                "beta": round(result.params.get('beta[1]', 0), 4),
                "omega": round(result.params.get('omega', 0), 4),
            }
        }
    except Exception as e:
        return {
            "error": f"GARCH forecast failed: {str(e)}",
            "method": "GARCH"
        }


def _interpret_volatility(vol: float) -> str:
    """Interpret volatility level."""
    if vol < 0.10:
        return "Very Low - Stable market conditions"
    elif vol < 0.15:
        return "Low - Normal market conditions"
    elif vol < 0.25:
        return "Moderate - Elevated uncertainty"
    elif vol < 0.35:
        return "High - Significant market stress"
    else:
        return "Very High - Extreme volatility"


def forecast_price_prophet(price_data: pd.DataFrame, days: int = 30) -> dict:
    """
    Forecast prices using Facebook Prophet.
    
    Args:
        price_data: DataFrame with 'date' and 'close' columns
        days: Forecast horizon in days
    
    Returns:
        Dictionary with trend forecast and confidence intervals
    """
    if not HAS_PROPHET:
        return {
            "error": "Prophet not available. Install with: pip install prophet",
            "method": "Prophet"
        }
    
    try:
        df = price_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        prophet_df = df[['date', 'close']].rename(columns={'date': 'ds', 'close': 'y'})
        
        if len(prophet_df) < 30:
            return {
                "error": "Insufficient data for Prophet. Need at least 30 days.",
                "method": "Prophet"
            }
        
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.95,
            changepoint_prior_scale=0.05
        )
        model.fit(prophet_df)
        
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)
        
        future_only = forecast[forecast['ds'] > prophet_df['ds'].max()]
        
        if len(future_only) == 0:
            future_only = forecast.tail(days)
        
        last_price = prophet_df['y'].iloc[-1]
        predicted_price = future_only['yhat'].iloc[-1]
        trend_direction = "UPWARD" if predicted_price > last_price else "DOWNWARD"
        change_pct = ((predicted_price - last_price) / last_price) * 100
        
        result = {
            "method": "Prophet",
            "forecast_horizon": days,
            "last_price": round(float(last_price), 2),
            "predicted_price": round(float(predicted_price), 2),
            "expected_change_pct": round(float(change_pct), 2),
            "trend_direction": trend_direction,
            "trend_line": [round(float(v), 2) for v in future_only['yhat'].values],
            "upper_bound": [round(float(v), 2) for v in future_only['yhat_upper'].values],
            "lower_bound": [round(float(v), 2) for v in future_only['yhat_lower'].values],
            "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in future_only['ds'].values],
            "historical_dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in prophet_df['ds'].tail(30).values],
            "historical_prices": [round(float(v), 2) for v in prophet_df['y'].tail(30).values],
            "trend_interpretation": _interpret_trend(trend_direction, abs(float(change_pct))),
            "confidence_interval": "95%"
        }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Prophet forecast failed: {str(e)}",
            "method": "Prophet"
        }


def _interpret_trend(direction: str, change_pct: float) -> str:
    """Interpret trend based on direction and magnitude."""
    if direction == "UPWARD":
        if change_pct > 15:
            return f"Strong bullish trend expected (+{change_pct:.1f}%)"
        elif change_pct > 5:
            return f"Moderate bullish trend (+{change_pct:.1f}%)"
        elif change_pct > 1:
            return f"Slight upward movement (+{change_pct:.1f}%)"
        else:
            return "Sideways trend expected"
    else:
        if change_pct > 15:
            return f"Strong bearish trend expected ({change_pct:.1f}%)"
        elif change_pct > 5:
            return f"Moderate bearish trend ({change_pct:.1f}%)"
        elif change_pct > 1:
            return f"Slight downward movement ({change_pct:.1f}%)"
        else:
            return "Sideways trend expected"


def calculate_var_cvar(returns: pd.Series, confidence: float = 0.95) -> dict:
    """Calculate Value at Risk and Conditional VaR."""
    try:
        returns_clean = returns.dropna()
        if len(returns_clean) < 30:
            return {"error": "Need at least 30 days of data"}
        
        var_level = 1 - confidence
        var_threshold = np.percentile(returns_clean, var_level * 100)
        
        cvar_mask = returns_clean <= var_threshold
        cvar = returns_clean[cvar_mask].mean() if cvar_mask.sum() > 0 else var_threshold
        
        return {
            "confidence_level": f"{confidence * 100}%",
            "var_daily": round(var_threshold * 100, 4),
            "var_annual": round(var_threshold * np.sqrt(252) * 100, 2),
            "cvar_daily": round(cvar * 100, 4),
            "cvar_annual": round(cvar * np.sqrt(252) * 100, 2),
            "interpretation": f"With {confidence*100}% confidence, worst daily loss should not exceed {abs(var_threshold)*100:.2f}%"
        }
    except Exception as e:
        return {"error": str(e)}


def get_full_forecast(price_data: pd.DataFrame, returns: pd.Series = None, forecast_days: int = 30) -> dict:
    """Get comprehensive forecast combining Prophet and GARCH."""
    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "forecast_days": forecast_days
    }
    
    result["price_forecast"] = forecast_price_prophet(price_data, days=forecast_days)
    
    if returns is not None:
        result["volatility_forecast"] = forecast_volatility_garch(returns, horizon=forecast_days)
        result["risk_metrics"] = calculate_var_cvar(returns)
    
    return result
