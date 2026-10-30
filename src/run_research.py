"""Run a backtest and export daily ledger, trades, metrics and an SVG chart."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np
import pandas as pd
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backtest import BacktestConfig, run_backtest
from src.data import DEFAULT_DATA, ROOT, load_data
from src.report import write_chart, write_summary

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--data', type=Path, default=None)
    group.add_argument('--demo', action='store_true', help='Use synthetic example prices.')
    parser.add_argument('--fast', type=int, default=5)
    parser.add_argument('--slow', type=int, default=20)
    parser.add_argument('--cost-bps', type=float, default=10.0, help='Illustrative one-way combined cost in bps.')
    parser.add_argument('--risk-free', type=float, default=0.0, help='Assumed ANNUAL risk-free rate, as a decimal.')
    parser.add_argument('--start', help='Inclusive evaluation start, YYYY-MM-DD.')
    parser.add_argument('--end', help='Inclusive evaluation end, YYYY-MM-DD.')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args(argv)
    input_path = (ROOT / 'examples' / 'synthetic_prices.csv') if args.demo else (args.data or DEFAULT_DATA)
    try:
        prices = load_data(input_path)
        daily, metrics, trades = run_backtest(prices,
            BacktestConfig(args.fast, args.slow, args.cost_bps, args.risk_free), args.start, args.end)
    except (ValueError, FileNotFoundError, TypeError) as exc:
        parser.exit(2, f'Backtest failed: {exc}\n')
    is_demo = args.demo or input_path.resolve() == (ROOT / 'examples' / 'synthetic_prices.csv').resolve()
    label = 'SYNTHETIC DEMO - not market performance' if is_demo else f'CSV backtest: {input_path.name}'
    metrics['data'] = {'label':label, 'synthetic_demo':is_demo,
        'file':input_path.name, 'sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'input_rows':len(prices)}
    sidecar = input_path.with_suffix('.metadata.json')
    if sidecar.is_file():
        metrics['data']['source_metadata'] = json.loads(sidecar.read_text(encoding='utf-8'))
        source = metrics['data']['source_metadata']
        if not is_demo and source.get('symbol'):
            adjustment = source.get('adjust') or 'unadjusted'
            label = f"A-share {source['symbol']} | AKShare / Eastmoney | {adjustment} daily prices"
            metrics['data']['label'] = label
    metrics['environment'] = {'python':platform.python_version(), 'pandas':pd.__version__, 'numpy':np.__version__}
    args.output.mkdir(parents=True, exist_ok=True)
    daily.to_csv(args.output / 'daily.csv', index=False, date_format='%Y-%m-%d')
    trades.to_csv(args.output / 'trades.csv', index=False, date_format='%Y-%m-%d')
    (args.output / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    write_chart(daily, args.output / 'performance.svg', label)
    write_summary(metrics, args.output / 'summary.md')
    print((args.output / 'summary.md').read_text(encoding='utf-8'))
    print(f'Outputs: {args.output.resolve()}')

if __name__ == '__main__':
    main()
