import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
from src.backtest import BacktestConfig, run_backtest
from src.data import ROOT, validate_prices
from src.features import add_features
from src.metrics import calc_sharpe, max_drawdown


def prices():
    return pd.DataFrame({'date':pd.date_range('2024-01-01', periods=8),
        'open':[10,10,12,15,30,12,8,10], 'close':[10,12,14,20,10,8,12,14]})


class ExecutionTests(unittest.TestCase):
    def test_next_open_and_overnight_returns_match_hand_calculation(self):
        daily, metrics, trades = run_backtest(prices(), BacktestConfig(1,2,0))
        expected = [14/12-1,20/14-1,10/20-1,12/10-1,0,14/10-1]
        np.testing.assert_allclose(daily.strategy_return, expected)
        self.assertEqual(daily.position.tolist(), [1,1,1,0,0,1])
        self.assertEqual(trades.side.tolist(), ['BUY','SELL','BUY'])
        self.assertAlmostEqual(metrics['buy_and_hold']['total_return'],14/12-1)

    def test_cost_on_entry_and_exit_only(self):
        free, _, _ = run_backtest(prices(), BacktestConfig(1,2,0))
        paid, metrics, _ = run_backtest(prices(), BacktestConfig(1,2,100))
        np.testing.assert_allclose(paid.cost_fraction, [.01,0,0,.01,0,.01])
        self.assertAlmostEqual(paid.strategy_equity.iloc[-1],free.strategy_equity.iloc[-1] * .99**3)
        self.assertAlmostEqual(metrics['buy_and_hold']['total_return'],14/12*.99-1)

    def test_no_same_day_close_used_for_position(self):
        original, _, _ = run_backtest(prices(), BacktestConfig(1,2,0))
        changed = prices()
        changed.loc[4,'close'] = 100
        revised, _, _ = run_backtest(changed, BacktestConfig(1,2,0))
        np.testing.assert_array_equal(original.position.iloc[:3], revised.position.iloc[:3])
        self.assertNotEqual(original.position.iloc[3], revised.position.iloc[3])

    def test_future_prices_do_not_change_past_results(self):
        original, _, _ = run_backtest(prices(), BacktestConfig(1,2,10))
        changed = prices()
        changed.loc[6:,['open','close']] *= 3
        revised, _, _ = run_backtest(changed, BacktestConfig(1,2,10))
        pd.testing.assert_frame_equal(original.iloc[:4], revised.iloc[:4])

    def test_later_window_keeps_warmup_but_starts_in_cash(self):
        daily, metrics, _ = run_backtest(prices(), BacktestConfig(1,2,0), start='2024-01-04')
        self.assertEqual(daily.date.iloc[0], pd.Timestamp('2024-01-04'))
        self.assertEqual(daily.previous_position.iloc[0], 0)
        self.assertAlmostEqual(daily.strategy_return.iloc[0],20/15-1)
        self.assertAlmostEqual(metrics['buy_and_hold']['total_return'],14/15-1)

    def test_flat_prices_remain_cash_and_sharpe_is_null(self):
        frame=prices(); frame[['open','close']] = 10.0
        daily, metrics, trades=run_backtest(frame, BacktestConfig(1,2,10))
        self.assertTrue(daily.strategy_return.eq(0).all())
        self.assertIsNone(metrics['strategy']['sharpe'])
        self.assertTrue(trades.empty)
        json.dumps(metrics, allow_nan=False)

    def test_input_is_not_mutated(self):
        frame=prices(); original=frame.copy(deep=True)
        run_backtest(frame, BacktestConfig(1,2,0))
        pd.testing.assert_frame_equal(frame, original)


class MetricTests(unittest.TestCase):
    def test_first_loss_is_in_drawdown(self):
        self.assertAlmostEqual(max_drawdown([.8,.9]),-.2)

    def test_drawdown_tracks_new_peak(self):
        self.assertAlmostEqual(max_drawdown([1.1,1.2,.9,1.3]),-.25)

    def test_zero_volatility_sharpe_is_nan(self):
        self.assertTrue(np.isnan(calc_sharpe([0,0,0])))

    def test_annual_rf_is_converted_consistently(self):
        values=np.array([.01,-.02,.03,.005])
        expected=np.sqrt(252)*(values.mean()-((1.02)**(1/252)-1))/values.std(ddof=1)
        self.assertAlmostEqual(calc_sharpe(values, rf=.02),expected)

    def test_invalid_metrics_rejected(self):
        for values in ([], [np.nan], [np.inf], [0], [-1]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                max_drawdown(values)


class ValidationTests(unittest.TestCase):
    def test_unsorted_rows_are_sorted(self):
        pd.testing.assert_frame_equal(validate_prices(prices().iloc[::-1]),prices())

    def test_duplicate_dates_rejected(self):
        with self.assertRaises(ValueError):
            validate_prices(pd.concat([prices(),prices().iloc[:1]]))

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            validate_prices(prices().drop(columns='open'))

    def test_invalid_prices_rejected(self):
        for value in (0,-1,np.nan,np.inf,'bad'):
            with self.subTest(value=value):
                frame=prices().astype({'close':object}); frame.loc[0,'close']=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_prices(frame)

    def test_inconsistent_ohlc_rejected(self):
        frame=prices(); frame['high']=1; frame['low']=2
        with self.assertRaises(ValueError):
            validate_prices(frame)

    def test_invalid_windows_rejected(self):
        for fast,slow in [(0,2),(2,2),(3,2),(1.5,2),(True,2)]:
            with self.subTest(fast=fast,slow=slow), self.assertRaises(ValueError):
                add_features(prices(),fast,slow)

    def test_invalid_costs_rejected(self):
        for value in [-1,10000,np.inf,np.nan]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_backtest(prices(),BacktestConfig(1,2,value))

    def test_short_and_empty_windows_rejected(self):
        with self.assertRaises(ValueError):
            run_backtest(prices(),BacktestConfig(5,20,0))
        with self.assertRaises(ValueError):
            run_backtest(prices(),BacktestConfig(1,2,0),start='2025-01-01')
        with self.assertRaises(ValueError):
            run_backtest(prices(),BacktestConfig(1,2,0),start='2025-01-01',end='2024-01-01')


class CommandLineTests(unittest.TestCase):
    def test_demo_works_outside_project_directory_and_exports_all_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'src'/'run_research.py'),'--demo',
                '--output',str(Path(folder)/'results')],cwd=folder,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            out=Path(folder)/'results'
            self.assertEqual({p.name for p in out.iterdir()},
                {'daily.csv','trades.csv','metrics.json','summary.md','performance.svg'})
            metrics=json.loads((out/'metrics.json').read_text())
            self.assertTrue(metrics['data']['synthetic_demo'])
            self.assertIn('SYNTHETIC',result.stdout)
            self.assertIn('SYNTHETIC',metrics['data']['label'])
            self.assertEqual(metrics['strategy']['sessions'],300)


if __name__ == '__main__':
    unittest.main()
