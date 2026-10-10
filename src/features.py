import pandas as pd

def add_features(df):
    # 简单均线因子
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['return'] = df['close'].pct_change()
    df.dropna(inplace=True)
    return df
