"""Performance metrics with an explicit initial-capital reference."""
import numpy as np
import pandas as pd

def calc_sharpe(returns, rf=0.0, periods=252):
    """rf is an ANNUAL assumed rate; return NaN when volatility is zero."""
    values = pd.Series(returns, dtype=float)
    if values.empty or not np.isfinite(values).all():
        raise ValueError('Returns must be non-empty and finite.')
    if not np.isfinite(rf) or rf <= -1 or periods <= 0:
        raise ValueError('Invalid risk-free rate or annualization factor.')
    daily_rf = (1.0 + rf) ** (1.0 / periods) - 1.0
    volatility = values.std(ddof=1)
    if not np.isfinite(volatility) or volatility <= 1e-15:
        return float('nan')
    return float(np.sqrt(periods) * (values.mean() - daily_rf) / volatility)

def drawdown_series(equity, initial=1.0):
    values = pd.Series(equity, dtype=float)
    if values.empty or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError('Equity must be non-empty, finite and positive.')
    if not np.isfinite(initial) or initial <= 0:
        raise ValueError('Initial equity must be finite and positive.')
    peaks = np.maximum.accumulate(np.r_[initial, values.to_numpy()])[1:]
    return pd.Series(values.to_numpy() / peaks - 1.0, index=values.index)

def max_drawdown(series, initial=1.0):
    return float(drawdown_series(series, initial).min())

def summarize(returns, rf=0.0, periods=252):
    values = pd.Series(returns, dtype=float)
    if values.empty or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError('Returns must be finite, non-empty and greater than -100%.')
    equity = (1 + values).cumprod()
    sharpe = calc_sharpe(values, rf, periods)
    volatility = float(values.std(ddof=1) * np.sqrt(periods))
    return {
        'sessions': len(values),
        'total_return': float(equity.iloc[-1] - 1),
        'annualized_return': float(equity.iloc[-1] ** (periods / len(values)) - 1),
        'annualized_volatility': volatility if np.isfinite(volatility) else None,
        'sharpe': sharpe if np.isfinite(sharpe) else None,
        'max_drawdown': max_drawdown(equity),
    }
