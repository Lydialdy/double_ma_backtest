import numpy as np

def calc_sharpe(returns, rf=0.02/252):
    excess = returns - rf
    sharpe = np.sqrt(252) * excess.mean() / excess.std()
    return sharpe

def max_drawdown(series):
    running_max = series.cummax()
    drawdown = series / running_max - 1
    return drawdown.min()
