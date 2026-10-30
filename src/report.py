"""Portable SVG and Markdown reports without a plotting backend."""
from html import escape
import numpy as np

def format_value(key, value):
    if value is None:
        return 'N/A'
    return f'{value:.2f}' if key == 'sharpe' else f'{value:.2%}'

def write_summary(metrics, path):
    lines = ['# Moving Average Backtest', '', metrics['data']['label'], '',
        f"Evaluation: {metrics['start']} to {metrics['end']} ({metrics['strategy']['sessions']} sessions).", '',
        '| Metric | Strategy | Buy and hold |', '|---|---:|---:|']
    for key, label in [('total_return','Total return'), ('annualized_return','Annualized return'),
                       ('annualized_volatility','Annualized volatility'), ('sharpe','Sharpe ratio'),
                       ('max_drawdown','Maximum drawdown')]:
        lines.append(f"| {label} | {format_value(key, metrics['strategy'][key])} | {format_value(key, metrics['buy_and_hold'][key])} |")
    c = metrics['configuration']
    lines += ['', f"Windows: {c['fast']}/{c['slow']} sessions; one-way cost: {c['cost_bps']:g} bps; assumed annual risk-free rate: {c['risk_free_rate']:.2%}.",
        f"Entries: {metrics['strategy']['entries']}; exits: {metrics['strategy']['exits']}; intraday exposure: {metrics['strategy']['exposure_fraction']:.1%}.",
        '', metrics['execution'], '', 'Costs are illustrative. Fractional positions are assumed; no volume, limit-up/limit-down or lot-size constraints are simulated.',
        'Annualization uses 252 sessions. Cash earns zero. The baseline and strategy use the same evaluation dates.',
        '', f"Input SHA-256: {metrics['data']['sha256']}", '']
    path.write_text('\n'.join(lines), encoding='utf-8')

def write_chart(daily, path, label):
    width, height, left, right = 1000, 650, 80, 965
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text {font-family:Arial,sans-serif;fill:#25324a;font-size:13px;} .title {font-size:23px;font-weight:bold;} .small {font-size:12px;}</style>',
        '<text x="80" y="36" class="title">Moving average strategy and buy and hold</text>',
        f'<text x="80" y="61">{escape(label)}</text>',
        '<text x="80" y="88">Blue: strategy</text><text x="230" y="88">Orange: buy and hold</text>']
    x = np.linspace(left, right, len(daily) + 1)
    for top, bottom, cols, initial, title in [
        (125, 355, ['strategy_equity','benchmark_equity'], 1.0, 'Equity (initial capital = 1)'),
        (425, 565, ['strategy_drawdown','benchmark_drawdown'], 0.0, 'Drawdown from initial capital and subsequent peaks'),
    ]:
        arrays = [np.r_[initial, daily[col].to_numpy()] for col in cols]
        low, high = min(a.min() for a in arrays), max(a.max() for a in arrays)
        span = max(high - low, 0.02)
        low -= span * .06
        high += span * .06
        def y(a):
            return bottom - (a - low) / (high - low) * (bottom - top)
        parts.append(f'<text x="80" y="{top-14}">{title}</text>')
        for tick in np.linspace(low, high, 5):
            yy = y(tick)
            text = f'{tick:.2f}' if initial else f'{tick:.0%}'
            parts += [f'<line x1="{left}" y1="{yy:.2f}" x2="{right}" y2="{yy:.2f}" stroke="#e0e5eb"/>',
                f'<text x="70" y="{yy+4:.2f}" text-anchor="end">{text}</text>']
        for array, color in zip(arrays, ['#1460a5','#c17423']):
            points = ' '.join(f'{xx:.2f},{yy:.2f}' for xx,yy in zip(x,y(array)))
            parts.append(f'<polyline points="{points}" stroke="{color}" stroke-width="2" fill="none"/>')
    parts += [f'<text x="{left}" y="592">{daily.date.iloc[0].date()}</text>',
        f'<text x="{right}" y="592" text-anchor="end">{daily.date.iloc[-1].date()}</text>',
        '<text x="80" y="625" class="small">Next-open execution; costs included; terminal positions marked to market. See summary.md for assumptions.</text>', '</svg>']
    path.write_text('\n'.join(parts), encoding='utf-8')
