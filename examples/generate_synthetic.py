"""Deterministic TEST data only. These are not observations of any real security."""
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    rng=np.random.default_rng(42)
    n=320
    # A simple random walk, without a built-in trend or crossover pattern.
    returns=rng.normal(0,.012,n)
    close=100*np.exp(np.cumsum(returns))
    previous=np.r_[100,close[:-1]]
    opening=previous*np.exp(rng.normal(0,.004,n))
    frame=pd.DataFrame({'date':pd.bdate_range('2024-01-01',periods=n),
        'open':opening, 'close':close,
        'high':np.maximum(opening,close)*1.005, 'low':np.minimum(opening,close)*.995})
    frame.to_csv(Path(__file__).with_name('synthetic_prices.csv'),index=False,
        date_format='%Y-%m-%d',float_format='%.8f')

if __name__ == '__main__':
    main()
