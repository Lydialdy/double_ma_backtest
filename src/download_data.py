import akshare as ak
import pandas as pd
import os

def download_stock_data(symbol="000001", start_date="20200101", end_date="20251231"):
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
    df.rename(columns={"日期":"date","开盘":"open","收盘":"close","最高":"high","最低":"low","成交量":"volume"},inplace=True)
    df = df[["date","open","close","high","low","volume"]]
    if not os.path.exists("../data"):
        os.mkdir("../data")
    df.to_csv("../data/daily.csv",index=False)
    print("数据下载完成，保存至 data/daily.csv")

if __name__ == "__main__":
    download_stock_data()
