from data import load_data
from features import add_features
from metrics import calc_sharpe, max_drawdown

def backtest():
    df = load_data("../data/daily.csv")
    df = add_features(df)

    # 简单策略：5日均线上穿20日均线买入，下穿卖出
    df['signal'] = 0
    df.loc[df['ma5']>df['ma20'],'signal'] = 1

    df['strategy_return'] = df['return'] * df['signal'].shift(1)
    df['cum_strategy'] = (1 + df['strategy_return']).cumprod()
    df['cum_bench'] = (1 + df['return']).cumprod()

    sharpe = calc_sharpe(df['strategy_return'])
    mdd = max_drawdown(df['cum_strategy'])
    print(f"回测结果：夏普比率={sharpe:.2f}, 最大回撤={mdd:.2%}")

if __name__ == "__main__":
    backtest()
