"""Moving averages use only prices available at each session's close."""
from numbers import Integral

def add_features(df, fast=5, slow=20):
    if (isinstance(fast, bool) or isinstance(slow, bool) or
            not isinstance(fast, Integral) or not isinstance(slow, Integral) or
            not 1 <= fast < slow):
        raise ValueError('Windows must be integers satisfying 1 <= fast < slow.')
    result = df.copy()
    result['ma_fast'] = result['close'].rolling(fast, min_periods=fast).mean()
    result['ma_slow'] = result['close'].rolling(slow, min_periods=slow).mean()
    result['signal'] = (result['ma_fast'] > result['ma_slow']).astype(int)
    result['ready'] = result['ma_slow'].notna()
    return result
