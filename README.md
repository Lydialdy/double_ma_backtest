# A 股双均线策略回测

这是一个 Python 量化练习项目：用 5/20 日均线决定持有或空仓，再和买入持有策略比较。计算用 pandas 和 NumPy，真实 A 股行情通过 AKShare 下载。

除了计算收益，也检查了几个容易出错的地方：信号什么时候可用、什么时候成交、买卖费用如何扣除，以及第一次亏损是否计入回撤。下面列出了运行方法和具体假设。

## 快速运行

建议使用 Python 3.11 或更高版本。在项目根目录执行：

```bash
python -m pip install -r requirements.txt
python -m src.run_research --demo
python -m unittest discover -s tests -v
```

无需行情接口即可运行演示。内置数据是固定随机种子生成的**合成测试样本**，不对应真实证券，演示收益不能用来判断策略效果。

合成样本的输出见 [演示报告](examples/demo_output/summary.md)。

## 使用真实 A 股行情

```bash
python -m pip install -r requirements-market.txt
python -m src.download_data --symbol 000001 --start 20200101 --end 20251231
python -m src.run_research --fast 5 --slow 20 --cost-bps 10
```

默认 CSV 保存于项目内的 `data/daily.csv`。下载时同时记录标的、复权口径、查询日期和数据源版本。
也可传入自己的 CSV（至少包含 `date,open,close`）：

```bash
python -m src.run_research --data data/daily.csv --start 2022-01-01 --end 2025-12-31 --output outputs/ping_an
```

`--start` 前的数据仍用于均线预热。程序不会静默填补缺失价格；重复日期、无效价格和不一致的 OHLC 会报错。
原有 `python src/download_data.py` 和 `python src/run_research.py` 入口也可使用，默认路径不依赖启动位置。

## 平安银行样本结果

使用 2026-10-30 下载的平安银行（000001）前复权日线，查询区间为 2020–2025 年。
共 1,455 条行情，前 20 个交易日用于均线预热；评价区间为 2020-02-07 至 2025-12-31，共 1,435 个交易日。
参数固定为 5/20 日均线，单边成本 10 bps，年度无风险利率假设为 0。

| 指标 | 双均线策略 | 买入持有 |
|---|---:|---:|
| 累计收益 | -37.49% | -6.34% |
| 年化收益 | -7.92% | -1.14% |
| 夏普比率 | -0.21 | 0.14 |
| 最大回撤 | -61.55% | -69.28% |

![Ping An Bank equity and drawdown](examples/ping_an_2020_2025/performance.svg)

这组参数在该样本中没有跑赢买入持有。回撤较小并不代表策略有效：累计收益仍为负，且这里没有做样本外检验。
我保留了这个结果，后续研究可以先检查换手成本和不同市场阶段的表现，再考虑多标的验证。
完整 [报告](examples/ping_an_2020_2025/summary.md)、[每日流水](examples/ping_an_2020_2025/daily.csv)
和 [交易记录](examples/ping_an_2020_2025/trades.csv) 均可查看。
数据源版本、下载时间和输入文件校验和记录在 [metrics.json](examples/ping_an_2020_2025/metrics.json)。
复权数据以后可能调整，重新下载的数值不一定与这一快照完全相同。

## 策略与成交约定

| 项目 | 实现 |
|---|---|
| 信号 | 5 日均线 > 20 日均线时持有，否则空仓；窗口可配置 |
| 成交时间 | t 日收盘信号，在 t+1 日开盘执行 |
| 持仓 | 只做多，全仓或现金；不使用杠杆 |
| 成本 | 每次买卖扣除可配置的单边成本，默认 10 bps 为示例假设 |
| 基准 | 同一评价区间的买入持有策略，起始开盘买入并扣除相同成本 |
| 期末 | 按最后收盘价计价，不强制平仓 |
| 指标 | 累计收益、年化收益、年化波动率、夏普比率、最大回撤、持仓比例和交易次数 |

逐日收益分为“原持仓承担的隔夜收益”和“开盘调仓后的日内收益”。最大回撤包含初始本金，避免漏掉第一次下跌。
完整公式、复权口径和限制见 [回测方法](docs/methodology.md)。

## 输出文件

一次运行生成五个文件，默认位于 `outputs/`：

| 文件 | 内容 |
|---|---|
| `daily.csv` | 价格、均线、信号、仓位、换手、成本、净收益、净值和回撤 |
| `trades.csv` | 买卖日期、开盘参考价、仓位变化和成本率 |
| `metrics.json` | 策略与基准指标、参数、数据校验和及运行环境版本 |
| `summary.md` | 可阅读的结果表及关键假设 |
| `performance.svg` | 净值与回撤对比图，可在浏览器直接查看 |

合成演示和真实行情结果放在不同目录，报告中分别标明数据类型。日常运行使用本地价格文件重新生成结果。

## 验证覆盖

标准库 unittest 测试覆盖：手工核算的交易收益、次日开盘成交、买卖成本、未来价格不影响过去结果、
相同评价区间、初始亏损回撤、零波动率夏普比率、无效数据拒绝、输入不被修改和跨工作目录运行。
可用以下命令重新生成合成样本与报告：

```bash
python examples/generate_synthetic.py
python -m src.run_research --demo --output examples/demo_output
```

## 项目结构

```text
src/
  data.py             # 数据读取与校验
  download_data.py    # AKShare 下载及来源记录
  features.py         # 均线与信号
  backtest.py         # 次日开盘执行与收益计算
  metrics.py          # 绩效指标
  report.py           # Markdown 和 SVG 报告
  run_research.py     # 命令行入口
tests/                # 可手工核验的回归测试
examples/             # 合成测试数据与完整示例输出
docs/methodology.md   # 公式、假设与研究限制
```

## 研究边界

这是学习与研究项目。它使用连续比例仓位，不模拟整手、最低佣金、成交量、涨跌停或完整交易所规则；
现金收益设为零。前复权行情也不等同于严格的历史时点数据。单标的、单参数结果不足以证明策略有效，
进一步研究应固定参数并使用多标的和独立样本。项目不提供投资建议。

## English overview

A Python learning project for daily A-share moving-average backtesting. Signals formed at the close execute at the next session's open.
The engine separates overnight and intraday returns, applies configurable one-way costs, and compares against buy-and-hold
over identical dates. It exports daily and trade ledgers, metrics with input hashes, and equity/drawdown charts.
Offline examples use clearly labeled synthetic data. See the methodology for assumptions and limitations.
