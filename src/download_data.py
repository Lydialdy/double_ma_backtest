"""Download AKShare prices and retain parameters alongside the local CSV."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import DEFAULT_DATA, validate_prices

def download_stock_data(symbol='000001', start_date='20200101', end_date='20251231',
                        output=DEFAULT_DATA, adjust='qfq'):
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError('Install requirements-market.txt to download real market prices.') from exc
    if len(symbol) != 6 or not symbol.isdigit():
        raise ValueError('Expected a six-digit A-share symbol.')
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    if start > end:
        raise ValueError('Start date must be on or before end date.')
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period='daily', start_date=start_date,
                              end_date=end_date, adjust=adjust)
    except Exception as exc:
        raise RuntimeError(f'AKShare request failed: {exc}. Retry later or use a local CSV.') from exc
    if df.empty:
        raise ValueError('No prices returned. Check the symbol, date range and data provider.')
    df = df.rename(columns={'日期':'date', '开盘':'open', '收盘':'close',
                            '最高':'high', '最低':'low', '成交量':'volume'})
    df = validate_prices(df[['date', 'open', 'close', 'high', 'low', 'volume']])
    path = Path(output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, date_format='%Y-%m-%d')
    metadata = {'source':'AKShare stock_zh_a_hist / Eastmoney', 'symbol':symbol,
                'requested_start':start_date, 'requested_end':end_date, 'adjust':adjust,
                'retrieved_utc':datetime.now(timezone.utc).isoformat(),
                'akshare_version':getattr(ak, '__version__', 'unknown'), 'rows':len(df)}
    path.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', default='000001')
    parser.add_argument('--start', default='20200101')
    parser.add_argument('--end', default='20251231')
    parser.add_argument('--adjust', choices=['qfq', 'hfq', ''], default='qfq')
    parser.add_argument('--output', type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    try:
        path = download_stock_data(args.symbol, args.start, args.end, args.output, args.adjust)
    except (ValueError, RuntimeError, KeyError) as exc:
        parser.exit(2, f'Download failed: {exc}\n')
    print(f'Saved prices: {path}')

if __name__ == '__main__':
    main()
