#!/usr/bin/env python3
"""Paper-trading CLI: run the trader on a price stream and print the result.

Usage:
    # Synthetic (default)
    python -m paper_trading --steps 500 --drift 0.10 --vol 0.15
    python -m paper_trading --steps 200 --shock earnings_beat

    # Real data from a CSV file (e.g. AAPL.csv with date,close columns)
    python -m paper_trading --csv data/AAPL.csv --asset AAPL

    # Real data from Yahoo Finance
    python -m paper_trading --ticker AAPL --start 2020-01-01 --end 2024-12-31
"""
import argparse
import os
import sys

from quilt_cell import TimeCell
from temporal import TemporalReasoner

from . import (
    PaperTrader,
    TradingDecisionSupport,
    synthetic_price_stream,
    CSVPriceFeed,
    YahooFinanceFeed,
    EXAMPLE_SHOCKS,
)


def main():
    p = argparse.ArgumentParser(description="Quilt paper trader")
    # Source
    src = p.add_mutually_exclusive_group()
    src.add_argument("--csv", type=str, default=None,
                     help="path to a CSV file with date,close columns")
    src.add_argument("--ticker", type=str, default=None,
                     help="Yahoo Finance ticker (e.g. AAPL, ^GSPC)")
    p.add_argument("--start", type=str, default="2020-01-01",
                   help="start date (for --ticker)")
    p.add_argument("--end", type=str, default="2024-12-31",
                   help="end date (for --ticker)")
    # Synthetic params
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--drift", type=float, default=0.10,
                   help="annualized drift (e.g. 0.10 = 10%/year)")
    p.add_argument("--vol", type=float, default=0.15,
                   help="annualized volatility (e.g. 0.15 = 15%/year)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--shock", choices=list(EXAMPLE_SHOCKS.keys()) + ["none"], default="none")
    # Trading params
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--threshold-return", type=float, default=0.005)
    p.add_argument("--threshold-uncertainty", type=float, default=0.4)
    p.add_argument("--asset", type=str, default="ASSET")
    p.add_argument("--verbose", action="store_true",
                   help="print each trade as it happens")
    args = p.parse_args()

    # Resolve the data source
    if args.csv:
        feed = CSVPriceFeed(args.csv)
        stream = feed.stream()
        source_label = (
            f"CSV {args.csv} ({len(feed)} rows, "
            f"total return {feed.total_return:+.2%})"
        )
        if args.asset == "ASSET":
            args.asset = os.path.splitext(os.path.basename(args.csv))[0].upper()
    elif args.ticker:
        feed = YahooFinanceFeed(args.ticker, args.start, args.end)
        stream = feed.stream()
        source_label = (
            f"Yahoo {args.ticker} {args.start}..{args.end} "
            f"({len(feed)} rows)"
        )
        if args.asset == "ASSET":
            args.asset = args.ticker.upper()
    else:
        shocks = EXAMPLE_SHOCKS[args.shock] if args.shock != "none" else None
        stream = synthetic_price_stream(
            n_steps=args.steps, seed=args.seed,
            drift=args.drift, vol=args.vol, shocks=shocks,
        )
        source_label = (
            f"synthetic GBM, drift {args.drift:.2%}, vol {args.vol:.2%}, "
            f"{args.steps} steps, seed {args.seed}, shock {args.shock}"
        )

    cell = TimeCell()
    reasoner = TemporalReasoner(cell=cell)
    strategy = TradingDecisionSupport(
        memory=reasoner.memory,
        threshold_return=args.threshold_return,
        threshold_uncertainty=args.threshold_uncertainty,
    )
    trader = PaperTrader(
        cell=cell, reasoner=reasoner, strategy=strategy, asset=args.asset,
        horizon=args.horizon,
    )
    result = trader.run(stream, verbose=args.verbose)
    print()
    print(f"=== Summary for {args.asset} ===")
    print(f"source      = {source_label}")
    print(f"horizon     = {args.horizon}")
    print(f"n_trades    = {result['n_trades']}")
    print(f"actions     = {result['n_actions']}")
    print(f"final value = ${result['final_value']:,.2f}")
    print(f"P&L         = ${result['total_pnl']:+,.2f} ({result['pnl_pct']:+.2%})")
    # Show last 5 trades
    print()
    print("=== Last 5 trades ===")
    for t in result['trade_log'][-5:]:
        actual_str = (
            f"{t['actual_price']:7.2f}" if t['actual_price'] is not None
            else "  --.-- "
        )
        err_str = (
            f"{t['prediction_error']:.3f}" if t['prediction_error'] is not None
            else "  -- "
        )
        pnl_str = (
            f"{t['realized_pnl']:+.2f}" if t['realized_pnl'] is not None
            else "  --.-- "
        )
        print(
            f"  step {t['step']:4d}: {t['action']:11s} @ "
            f"${t['current_price']:7.2f}  "
            f"forecast mean = ${t['forecast_mean']:7.2f}  "
            f"actual = {actual_str}  "
            f"error = {err_str}  "
            f"P&L = ${pnl_str}"
        )


if __name__ == "__main__":
    main()
