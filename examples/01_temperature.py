"""Example 01: temperature forecasting (univariate, no covariates).

Loads 365 days of synthetic daily temperature, forecasts the next 30 days,
plots the history + forecast + 90% prediction interval.

This example uses the synthetic forecast (no torch required) so it works
on any platform. To use the real TimesFM 3.0, set QUILT_USE_REAL_TIMESFM=1.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell


def main() -> None:
    # ── 1. Generate 365 days of synthetic daily temperature ──────────
    days = 365
    t = np.arange(days)
    temp = (
        15.0                          # mean
        + 10.0 * np.sin(2 * np.pi * t / 365)  # yearly cycle
        + 3.0 * np.sin(2 * np.pi * t / 7)     # weekly cycle
        + 1.5 * np.random.randn(days)         # noise
    )

    # ── 2. Build the cell ────────────────────────────────────────────
    cell = TimeCell()
    print(f"cell.kind_name() = {cell.kind_name()!r}")
    print(f"cell.kind_count() = {cell.kind_count()}")
    print(f"cell.opcode_count() = {cell.opcode_count()}")
    cell.bind_context(temp)
    cell.set_horizon(30)

    # ── 3. Run the forecast ──────────────────────────────────────────
    cell.forecast_()
    point = cell.read_point(0)
    q10 = cell.read_quantile(0.1, 0)
    q90 = cell.read_quantile(0.9, 0)

    # ── 4. Print a summary ───────────────────────────────────────────
    print("\nForecast summary (next 30 days):")
    print(f"  min point = {point.min():.1f}°C")
    print(f"  max point = {point.max():.1f}°C")
    print(f"  mean point = {point.mean():.1f}°C")
    print(f"  90% CI width = {(q90 - q10).mean():.2f}°C")
    print(f"  5 hottest forecast days:")
    top5 = np.argsort(point)[-5:][::-1]
    for t in top5:
        print(f"    day +{t+1}: {point[t]:.1f}°C "
              f"(90% CI: {q10[t]:.1f} - {q90[t]:.1f})")

    # ── 5. Plot ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(t, temp, color='#f0883e', label='history (365 days)')
        horizon_t = np.arange(365, 365 + 30)
        ax.plot(horizon_t, point, color='#7ee787', label='forecast (30 days)')
        ax.fill_between(horizon_t, q10, q90, color='#d29922', alpha=0.3,
                        label='90% prediction interval')
        ax.axvline(365, color='#8b949e', linestyle='--', alpha=0.5)
        ax.set_xlabel('day')
        ax.set_ylabel('temperature (°C)')
        ax.set_title('Quilt time.cell: daily temperature forecast')
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig('temperature_forecast.png', dpi=120)
        print("\nWrote temperature_forecast.png")
    except ImportError:
        print("\n(matplotlib not installed; skipping plot)")


if __name__ == "__main__":
    main()
