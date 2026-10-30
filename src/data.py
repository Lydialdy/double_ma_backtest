"""Read and validate daily prices without silently repairing invalid observations."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / 'data' / 'daily.csv'

def validate_prices(frame):
    missing = {'date', 'open', 'close'}.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    df = frame.copy()
    if df.empty:
        raise ValueError('Price data is empty.')
    df['date'] = pd.to_datetime(df['date'], errors='raise')
    if df['date'].isna().any() or df['date'].duplicated().any():
        raise ValueError('Dates must be non-null and unique.')
    if not df['date'].eq(df['date'].dt.normalize()).all():
        raise ValueError('Expected daily observations, not intraday timestamps.')
    for column in ('open', 'close', 'high', 'low'):
        if column in df:
            df[column] = pd.to_numeric(df[column], errors='raise')
            if not np.isfinite(df[column]).all() or (df[column] <= 0).any():
                raise ValueError(f'{column} must contain finite positive prices.')
    if {'high', 'low'}.issubset(df.columns):
        if ((df['high'] < df[['open', 'close']].max(axis=1)) |
                (df['low'] > df[['open', 'close']].min(axis=1)) |
                (df['low'] > df['high'])).any():
            raise ValueError('Inconsistent OHLC prices.')
    return df.sort_values('date').reset_index(drop=True)

def load_data(file_path=DEFAULT_DATA):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f'Price CSV not found: {path}. Download prices or run with --demo.')
    return validate_prices(pd.read_csv(path))
