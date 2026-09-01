"""Example 02: stock price forecasting (univariate with past-only covariates).

The covariate is daily trading volume, used to inform the price forecast.

This example uses the synthetic forecast (no torch required).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell


def main() -> None:
    # ── 1. Generate 252 days (1 year) of synthetic stock data ────────
    days = 252
    t = np.arange(days)

    # Random walk price
    np.random.seed(42)
    drift = 0.0003
    vol = 0.015
    log_returns = np.random.normal(drift, vol, days)
    price = 100.0 * np.exp(np.cumsum(log_returns))

    # Volume (with weekly cycle, opposite of price moves)
    volume = (
        1_000_000
        + 200_000 * np.sin(2 * np.pi * t / 5)  # 5-day cycle
        + 100_000 * (log_returns ** 2) * 100    # vol clustering
    )

    # ── 2. Build the cell with covariate ─────────────────────────────
    cell = TimeCell()
    cell.bind_context(price)
    cell.bind_past_only_covariate(volume)
    cell.set_horizon(5)
    cell.forecast_()

    point = cell.read_point(0)
    q10 = cell.read_quantile(0.1, 0)
    q90 = cell.read_quantile(0.9, 0)

    # ── 3. Print summary ─────────────────────────────────────────────
    last = price[-1]
    print(f"Last price: ${last:.2f}")
    print(f"\n5-day forecast:")
    for t in range(5):
        change = point[t] - last
        pct = 100 * change / last
        print(f"  day +{t+1}: ${point[t]:.2f} ({pct:+.2f}%)  "
              f"90% CI: ${q10[t]:.2f} - ${q90[t]:.2f}")

    print(f"\nPROFIT SCENARIO (entry at ${last:.2f}, exit at ${point[-1]:.2f}):")
    print(f"  expected profit = ${point[-1] - last:.2f} per share")
    print(f"  90% CI lower bound = ${q10[-1] - last:.2f} per share")
    print(f"  90% CI upper bound = ${q90[-1] - last:.2f} per share")

    # ── 4. Plot ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # Price
        ax1.plot(t, price, color='#f0883e', label='price history')
        horizon_t = np.arange(days, days + 5)
        ax1.plot(horizon_t, point, color='#7ee787', label='forecast')
        ax1.fill_between(horizon_t, q10, q90, color='#d29922', alpha=0.3,
                          label='90% CI')
        ax1.axvline(days, color='#8b949e', linestyle='--', alpha=0.5)
        ax1.set_ylabel('price ($)')
        ax1.set_title('Quilt time.cell: 5-day stock price forecast')
        ax1.legend()
        ax1.grid(alpha=0.3)

        # Volume
        ax2.bar(t, volume, color='#a371f7', alpha=0.6, width=1.0)
        ax2.set_xlabel('day')
        ax2.set_ylabel('volume')
        ax2.set_title('Trading volume (past-only covariate)')
        ax2.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig('stock_forecast.png', dpi=120)
        print("\nWrote stock_forecast.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
