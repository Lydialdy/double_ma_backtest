"""Long/cash strategy: observe close t, change exposure at open t+1."""
from dataclasses import asdict, dataclass
import numpy as np
import pandas as pd
from .data import validate_prices
from .features import add_features
from .metrics import drawdown_series, summarize

@dataclass(frozen=True)
class BacktestConfig:
    fast: int = 5
    slow: int = 20
    cost_bps: float = 10.0
    risk_free_rate: float = 0.0

def run_backtest(prices, config=None, start=None, end=None):
    config = config or BacktestConfig()
    if not np.isfinite(config.cost_bps) or not 0 <= config.cost_bps < 10000:
        raise ValueError('One-way costs must satisfy 0 <= cost_bps < 10,000.')
    if not np.isfinite(config.risk_free_rate) or config.risk_free_rate <= -1:
        raise ValueError('Annual risk-free rate must be finite and greater than -100%.')
    if start is not None and end is not None and pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError('Start date must be on or before end date.')
    df = add_features(validate_prices(prices), config.fast, config.slow)
    df['previous_close'] = df['close'].shift(1)
    df['position'] = df['signal'].shift(1, fill_value=0)
    eligible = df['ready'].shift(1, fill_value=False)
    if start is not None:
        eligible &= df['date'] >= pd.Timestamp(start)
    if end is not None:
        eligible &= df['date'] <= pd.Timestamp(end)
    df = df.loc[eligible].copy().reset_index(drop=True)
    if len(df) < 2:
        raise ValueError('Need at least two evaluation sessions after the slow-window warm-up.')
    # Every evaluation starts in cash; preserve pre-start prices only for indicators.
    df['previous_position'] = df['position'].shift(1, fill_value=0)
    df['turnover'] = (df['position'] - df['previous_position']).abs()
    overnight_factor = 1 + df['previous_position'] * (df['open'] / df['previous_close'] - 1)
    intraday_factor = 1 + df['position'] * (df['close'] / df['open'] - 1)
    df['cost_fraction'] = df['turnover'] * config.cost_bps / 10000.0
    df['gross_return'] = overnight_factor * intraday_factor - 1
    df['strategy_return'] = overnight_factor * (1 - df['cost_fraction']) * intraday_factor - 1
    # Benchmark enters at the same first open, pays entry cost, and holds to final close.
    df['benchmark_return'] = df['close'] / df['previous_close'] - 1
    df.loc[0, 'benchmark_return'] = (df.loc[0, 'close'] / df.loc[0, 'open']) * (1 - config.cost_bps / 10000.0) - 1
    df['strategy_equity'] = (1 + df['strategy_return']).cumprod()
    df['benchmark_equity'] = (1 + df['benchmark_return']).cumprod()
    df['strategy_drawdown'] = drawdown_series(df['strategy_equity'])
    df['benchmark_drawdown'] = drawdown_series(df['benchmark_equity'])
    metrics = {
        'configuration': asdict(config),
        'start': str(df['date'].iloc[0].date()),
        'end': str(df['date'].iloc[-1].date()),
        'execution': 'Previous close signal; next session open execution; terminal positions marked to market.',
        'strategy': summarize(df['strategy_return'], config.risk_free_rate),
        'buy_and_hold': summarize(df['benchmark_return'], config.risk_free_rate),
    }
    changes = df['position'] - df['previous_position']
    metrics['strategy'].update({
        'entries': int((changes > 0).sum()), 'exits': int((changes < 0).sum()),
        'exposure_fraction': float(df['position'].mean()),
        'terminal_position': int(df['position'].iloc[-1]),
    })
    trades = df.loc[changes.ne(0), ['date', 'open', 'previous_position', 'position', 'cost_fraction']].copy()
    trades['side'] = np.where(trades['position'].eq(1), 'BUY', 'SELL')
    return df, metrics, trades
