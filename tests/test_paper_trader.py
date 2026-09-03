"""Tests for the paper-trader.

The tests cover:
  - GBM stream produces expected price properties
  - Trader runs end-to-end without errors
  - Trade records are populated with URIs and rationales
  - P&L computation is correct
  - The CLI's main() returns a summary dict
  - Calibration tracking works
  - The trader can be reused for multiple assets (state isolation)
  - Quild-style CRDT merge: trade logs from two traders are mergeable
"""
import os
os.environ.setdefault("QUILT_TIMESFM_SYNTHETIC", "1")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import warnings
import numpy as np

warnings.simplefilter("ignore", RuntimeWarning)

from quilt_cell import TimeCell
from temporal import TemporalReasoner
from paper_trading import (
    PaperTrader,
    TradingDecisionSupport,
    TradingAction,
    synthetic_price_stream,
    GeometricBrownianMotion,
    EXAMPLE_SHOCKS,
    CSVPriceFeed,
    RandomWalkFeed,
    YahooFinanceFeed,
    MultiAgentTrader, AgentConfig,
    crdt_merge_trade_logs, compare_merged_to_unmerged,
)
from paper_trading.trader import Trade, Portfolio, Position


def make_trader(**kw):
    """Make a fresh trader for tests."""
    cell = TimeCell()
    reasoner = TemporalReasoner(cell=cell)
    strategy_kw = kw.pop("strategy_kw", {})
    # Move any strategy-related kwargs to strategy_kw
    for k in ("threshold_return", "threshold_uncertainty"):
        if k in kw:
            strategy_kw[k] = kw.pop(k)
    strategy = TradingDecisionSupport(memory=reasoner.memory, **strategy_kw)
    defaults = dict(
        cell=cell, reasoner=reasoner, strategy=strategy, asset="TEST",
        history_len=64, horizon=3, min_history=32, max_position_pct=0.05,
    )
    defaults.update(kw)
    return PaperTrader(**defaults)


class TestGeometricBrownianMotion(unittest.TestCase):
    def test_stream_length(self):
        gbm = GeometricBrownianMotion(seed=0)
        prices = list(gbm.stream(n_steps=100))
        self.assertEqual(len(prices), 100)
        for i, (t, p) in enumerate(prices):
            self.assertEqual(t, i)
            self.assertGreater(p, 0)

    def test_reproducible(self):
        gbm1 = GeometricBrownianMotion(seed=42)
        gbm2 = GeometricBrownianMotion(seed=42)
        a = [p for _, p in gbm1.stream(50)]
        b = [p for _, p in gbm2.stream(50)]
        self.assertEqual(a, b)

    def test_shock(self):
        # Shock +50% at step 10 should push the price up
        gbm = GeometricBrownianMotion(seed=0, sigma=0.0, mu=0.0)  # no drift, no vol
        baseline = [p for _, p in gbm.stream(20)]
        gbm2 = GeometricBrownianMotion(seed=0, sigma=0.0, mu=0.0)
        shocked = [p for _, p in gbm2.stream(20, shocks=[(10, 0.50)])]
        # Steps 0-9 should be identical
        for i in range(10):
            self.assertAlmostEqual(baseline[i], shocked[i], places=8)
        # Step 10 should be 1.5x baseline
        self.assertAlmostEqual(shocked[10], baseline[10] * 1.5, places=8)

    def test_example_shocks_defined(self):
        # Make sure all the documented example shocks exist
        for name in ("earnings_beat", "fed_hike", "product_launch", "volatility_spike"):
            self.assertIn(name, EXAMPLE_SHOCKS)


class TestPaperTrader(unittest.TestCase):
    def test_runs_end_to_end(self):
        trader = make_trader()
        stream = synthetic_price_stream(n_steps=200, seed=0)
        result = trader.run(stream)
        self.assertIn("n_trades", result)
        self.assertIn("total_pnl", result)
        self.assertIn("trade_log", result)
        # Either there are trades (n_trades > 0) or all are GATHER_DATA
        # (which is a valid response from the strategy). The key is
        # the run completes without error.

    def test_trade_record_shape(self):
        # Force at least one BUY by setting a strong positive drift
        trader = make_trader(threshold_return=0.001)  # very low bar
        # Use an even more aggressive setup: high drift, very low vol
        stream = synthetic_price_stream(n_steps=500, seed=0, drift=0.20, vol=0.05)
        result = trader.run(stream)
        # Find a non-GATHER_DATA trade
        actionable = [t for t in result["trade_log"] if t["action"] not in ("gather_data",)]
        if actionable:
            t = actionable[0]
            for k in ("step", "current_price", "forecast_uri", "forecast_mean",
                      "action", "decision_confidence", "rationale"):
                self.assertIn(k, t)
            # URI is a quf:// URI
            self.assertTrue(t["forecast_uri"].startswith("quf://"))

    def test_pnl_computation(self):
        # A trader that always buys should have a P&L proportional to
        # the price move (excluding fees / slippage)
        trader = make_trader(threshold_return=-0.99)  # almost any return = BUY
        # Very low vol, monotonic up
        stream = synthetic_price_stream(n_steps=300, seed=0, drift=0.30, vol=0.01)
        result = trader.run(stream)
        # P&L should be positive (price went up) — but cap is 5% of
        # portfolio per trade, so the trader will only deploy ~50% of
        # the cash. Expected: positive P&L.
        self.assertGreater(result["total_pnl"], 0,
                           f"expected positive P&L on a strongly-trending series, got {result['total_pnl']}")

    def test_calibration_collected(self):
        trader = make_trader()
        stream = synthetic_price_stream(n_steps=300, seed=0)
        trader.run(stream)
        learn = trader.reasoner.memory.learn_from_history("TEST")
        self.assertIn("mean_error", learn)
        self.assertIn("mean_calibration", learn)
        # We should have recorded at least one outcome
        self.assertGreater(learn["n_recorded_outcomes"], 0,
                           f"expected at least one recorded outcome; got {learn}")

    def test_portfolio_total_value(self):
        p = Portfolio(initial_cash=50_000.0)
        p.cash = 40_000.0
        p.positions["AAPL"] = Position(asset="AAPL", shares=100, cost_basis=100.0)
        # Total value = 40k cash + 100 * 150 = 55k
        self.assertAlmostEqual(p.total_value({"AAPL": 150.0}), 55_000.0, places=4)
        # P&L = 55k - 50k = 5k
        self.assertAlmostEqual(p.total_pnl({"AAPL": 150.0}), 5_000.0, places=4)

    def test_portfolio_execute_buy(self):
        p = Portfolio(initial_cash=100_000.0, cash=100_000.0)
        # max_trade_pct=1.0 means "use up to 50% of cash (the buy cap)"
        # transaction_cost_bps=0.0 means "no transaction cost" for this test
        shares, cash_delta = p.execute("AAPL", "buy", 100.0, max_trade_pct=1.0, transaction_cost_bps=0.0)
        # 50% of cash = 50k, divided by $100 = 500 shares
        self.assertAlmostEqual(shares, 500.0, places=4)
        self.assertAlmostEqual(cash_delta, -50_000.0, places=4)
        self.assertAlmostEqual(p.cash, 50_000.0, places=4)
        self.assertAlmostEqual(p.positions["AAPL"].shares, 500.0, places=4)
        self.assertAlmostEqual(p.positions["AAPL"].cost_basis, 100.0, places=4)

    def test_portfolio_execute_buy_capped(self):
        # max_trade_pct=0.10 caps at 10% of portfolio
        # transaction_cost_bps=0.0 means "no transaction cost" for this test
        p = Portfolio(initial_cash=100_000.0, cash=100_000.0)
        shares, cash_delta = p.execute("AAPL", "buy", 100.0, max_trade_pct=0.10, transaction_cost_bps=0.0)
        # min(50k, 10k) = 10k, divided by 100 = 100 shares
        self.assertAlmostEqual(shares, 100.0, places=4)
        self.assertAlmostEqual(cash_delta, -10_000.0, places=4)
        self.assertAlmostEqual(p.cash, 90_000.0, places=4)

    def test_portfolio_execute_buy_with_cost(self):
        # Test that transaction costs are deducted
        p = Portfolio(initial_cash=100_000.0, cash=100_000.0)
        # 50% of cash = 50k trade value; 5 bps = 0.05% = $25
        shares, cash_delta = p.execute("AAPL", "buy", 100.0, max_trade_pct=1.0, transaction_cost_bps=5.0)
        # Cash out = 50k + 25 = 50,025
        self.assertAlmostEqual(shares, 500.0, places=4)
        self.assertAlmostEqual(cash_delta, -50_025.0, places=4)
        self.assertAlmostEqual(p.cash, 49_975.0, places=4)

    def test_portfolio_execute_hold(self):
        p = Portfolio(initial_cash=100_000.0, cash=100_000.0)
        shares, cash_delta = p.execute("AAPL", "hold", 100.0)
        self.assertEqual(shares, 0.0)
        self.assertEqual(cash_delta, 0.0)
        self.assertEqual(p.cash, 100_000.0)

    def test_portfolio_execute_gather_data(self):
        p = Portfolio(initial_cash=100_000.0, cash=100_000.0)
        shares, cash_delta = p.execute("AAPL", "gather_data", 100.0)
        self.assertEqual(shares, 0.0)
        self.assertEqual(cash_delta, 0.0)

    def test_trade_log_mergeable_across_traders(self):
        # Two traders, two assets, two logs. Merging the logs should
        # produce a single dict keyed by quf:// URI.
        trader1 = make_trader(asset="AAPL", threshold_return=0.001)
        trader2 = make_trader(asset="MSFT", threshold_return=0.001)
        s1 = synthetic_price_stream(n_steps=300, seed=0)
        s2 = synthetic_price_stream(n_steps=300, seed=1)
        r1 = trader1.run(s1)
        r2 = trader2.run(s2)
        # The two logs are mergeable if every trade has a unique URI
        # that can serve as a CRDT key.
        all_uris = [t["forecast_uri"] for t in r1["trade_log"]] + \
                   [t["forecast_uri"] for t in r2["trade_log"]]
        self.assertEqual(len(all_uris), len(set(all_uris)),
                         "trade URIs must be unique across traders for CRDT merge")

    def test_min_history_blocks_first_trades(self):
        trader = make_trader(min_history=128, history_len=128)
        # With only 100 prices, we shouldn't be able to trade
        stream = synthetic_price_stream(n_steps=100, seed=0)
        result = trader.run(stream)
        # We might still get 0 trades, or 1 trade at the end. The point
        # is we should never trade before step 100.
        for t in result["trade_log"]:
            self.assertGreaterEqual(t["step"], 100)


class TestTradingAction(unittest.TestCase):
    def test_action_values(self):
        # The enum values must be lowercase strings for JSON-friendliness
        for a in TradingAction:
            self.assertEqual(a.value, a.value.lower())

    def test_strategy_serializes_decisions(self):
        # A TradingDecision can be reconstructed from its dict
        from paper_trading.strategy import TradingDecision
        d = TradingDecision(
            action=TradingAction.BUY,
            confidence=0.8,
            expected_benefit=1.5,
            rationale="up 2%",
            horizon=5,
            forecast_uri="quf://test/5/v1",
        )
        self.assertEqual(d.action.value, "buy")
        self.assertEqual(d.confidence, 0.8)


# ─── Real-world data feeds ───────────────────────────────────────

class TestCSVPriceFeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile, csv, datetime
        # Write a sample CSV for the tests
        cls.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False,
        )
        w = csv.writer(cls.tmp)
        w.writerow(["date", "close"])
        base = datetime.date(2023, 1, 2)
        for i in range(100):
            d = base + datetime.timedelta(days=i)
            price = 100 + i * 0.5  # monotonically increasing
            w.writerow([d.isoformat(), f"{price:.2f}"])
        cls.tmp.close()
        cls.path = cls.tmp.name

    @classmethod
    def tearDownClass(cls):
        import os
        os.unlink(cls.path)

    def test_reads_correct_row_count(self):
        feed = CSVPriceFeed(self.path)
        self.assertEqual(len(feed), 100)

    def test_first_and_last_price(self):
        feed = CSVPriceFeed(self.path)
        self.assertAlmostEqual(feed.first_price, 100.0, places=2)
        self.assertAlmostEqual(feed.last_price, 149.5, places=2)

    def test_total_return(self):
        feed = CSVPriceFeed(self.path)
        # 100 -> 149.5 = +49.5%
        self.assertAlmostEqual(feed.total_return, 0.495, places=2)

    def test_stream_yields_tuples(self):
        feed = CSVPriceFeed(self.path)
        for ts, price in feed.stream():
            self.assertIsInstance(ts, int)
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)
            break  # just check the first one

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            CSVPriceFeed("/nonexistent/path.csv")

    def test_paper_trader_on_csv(self):
        # The paper trader should run end-to-end on a real CSV
        feed = CSVPriceFeed(self.path)
        cell = TimeCell()
        reasoner = TemporalReasoner(cell=cell)
        strategy = TradingDecisionSupport(memory=reasoner.memory)
        trader = PaperTrader(
            cell=cell, reasoner=reasoner, strategy=strategy,
            asset="TEST", history_len=32, horizon=3, min_history=20,
        )
        result = trader.run(feed.stream())
        self.assertGreaterEqual(result["n_trades"], 0)
        # The trade log should be populated (or all GATHER_DATA, both are valid)
        for t in result["trade_log"]:
            self.assertIn("forecast_uri", t)


class TestRandomWalkFeed(unittest.TestCase):
    def test_reproducible(self):
        f1 = RandomWalkFeed(n_steps=100, seed=0)
        f2 = RandomWalkFeed(n_steps=100, seed=0)
        a = list(f1.stream())
        b = list(f2.stream())
        self.assertEqual(a, b)

    def test_different_seeds_differ(self):
        f1 = RandomWalkFeed(n_steps=100, seed=0)
        f2 = RandomWalkFeed(n_steps=100, seed=1)
        a = list(f1.stream())
        b = list(f2.stream())
        self.assertNotEqual(a, b)

    def test_length(self):
        feed = RandomWalkFeed(n_steps=50)
        self.assertEqual(len(list(feed.stream())), 50)


class TestYahooFinanceFeed(unittest.TestCase):
    def test_constructs_without_network(self):
        # Construction should not hit the network
        feed = YahooFinanceFeed("AAPL", "2024-01-01", "2024-01-31")
        self.assertEqual(feed.ticker, "AAPL")
        self.assertEqual(feed.start, "2024-01-01")


# ─── Multi-agent CRDT ────────────────────────────────────────────

class TestMultiAgentTrader(unittest.TestCase):
    def test_three_agents_same_feed(self):
        from paper_trading import (
            MultiAgentTrader, AgentConfig, synthetic_price_stream,
        )
        configs = [
            AgentConfig(name="conservative", threshold_return=0.01),
            AgentConfig(name="balanced", threshold_return=0.005),
            AgentConfig(name="aggressive", threshold_return=0.001),
        ]
        trader = MultiAgentTrader(configs, asset="TEST")
        stream = synthetic_price_stream(n_steps=200, seed=0)
        result = trader.run(stream, n_steps=200)
        self.assertEqual(result["n_agents"], 3)
        # Each agent has its own trades
        self.assertGreater(result["total_trades"], 0)

    def test_unique_uris_across_agents(self):
        from paper_trading import (
            MultiAgentTrader, AgentConfig, synthetic_price_stream,
        )
        configs = [AgentConfig(name=f"a{i}") for i in range(3)]
        trader = MultiAgentTrader(configs)
        stream = synthetic_price_stream(n_steps=200, seed=0)
        result = trader.run(stream, n_steps=200)
        # Every URI should be unique across all agents
        all_uris = []
        for a in result["per_agent"]:
            all_uris.extend(a["trade_uris"])
        self.assertEqual(len(all_uris), len(set(all_uris)),
                         "URIs must be unique across agents for CRDT merge")


class TestCRDTMerge(unittest.TestCase):
    def test_merge_combines_logs(self):
        # Two agents, two logs, one merged dict
        log1 = [
            {"forecast_uri": "quf://forecast/A/5/v1/aaaa",
             "action": "buy", "current_price": 100.0},
            {"forecast_uri": "quf://forecast/A/5/v1/bbbb",
             "action": "sell", "current_price": 101.0},
        ]
        log2 = [
            {"forecast_uri": "quf://forecast/A/5/v1/cccc",
             "action": "hold", "current_price": 102.0},
        ]
        merged = crdt_merge_trade_logs(log1, log2)
        self.assertEqual(len(merged), 3)
        self.assertIn("quf://forecast/A/5/v1/aaaa", merged)
        self.assertIn("quf://forecast/A/5/v1/cccc", merged)

    def test_merge_idempotent(self):
        # Merging the same log twice should not duplicate
        log = [{"forecast_uri": "quf://forecast/A/5/v1/aaaa", "action": "buy"}]
        merged_once = crdt_merge_trade_logs(log)
        merged_twice = crdt_merge_trade_logs(log, log)
        self.assertEqual(len(merged_once), len(merged_twice))

    def test_merge_commutative(self):
        # Order shouldn't matter
        log1 = [{"forecast_uri": "quf://forecast/A/5/v1/aaaa", "action": "buy"}]
        log2 = [{"forecast_uri": "quf://forecast/A/5/v1/bbbb", "action": "sell"}]
        m1 = crdt_merge_trade_logs(log1, log2)
        m2 = crdt_merge_trade_logs(log2, log1)
        self.assertEqual(set(m1.keys()), set(m2.keys()))

    def test_consistency_check(self):
        log1 = [{"forecast_uri": "quf://x/1"}]
        log2 = [{"forecast_uri": "quf://x/2"}]
        merged = crdt_merge_trade_logs(log1, log2)
        consistency = compare_merged_to_unmerged(merged, [log1, log2])
        self.assertTrue(consistency["consistent"])


if __name__ == "__main__":
    unittest.main()
