"""Example 05: multi-variate sensor fusion with past-and-future covariates.

3 sensor channels (temperature, pressure, vibration) are forecasted jointly.
The past-and-future covariate is a planned maintenance window — a known
upcoming event that the cell can use to refine the forecast.

This example uses the synthetic forecast (no torch required).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell


def main() -> None:
    # ── 1. Generate 3 sensor channels ────────────────────────────────
    days = 365
    t = np.arange(days)
    np.random.seed(21)

    temperature = 25 + 5 * np.sin(2 * np.pi * t / 365) + np.random.randn(days) * 0.5
    pressure = 100 + 3 * np.cos(2 * np.pi * t / 365) + np.random.randn(days) * 0.3
    vibration = 0.5 + 0.1 * np.sin(2 * np.pi * t / 30) + np.random.randn(days) * 0.05

    # ── 2. Past-and-future covariate: planned maintenance windows ────
    # The covariate is 1.0 during a maintenance window, 0.0 otherwise.
    # It must have length (context_len + horizon) = 365 + 30 = 395.
    maintenance = np.zeros(395)
    maintenance[200:202] = 1.0  # maintenance in the past
    maintenance[370:373] = 1.0  # maintenance in the forecast window

    # ── 3. Build the cell ────────────────────────────────────────────
    context = np.stack([temperature, pressure, vibration], axis=1)
    cell = TimeCell()
    cell.bind_context(context)
    cell.bind_past_future_covariate(maintenance)
    cell.set_horizon(30)
    cell.forecast_()

    # ── 4. Print the 30-day forecast for each channel ────────────────
    print("30-day sensor forecast (3 channels):\n")
    for v, name in enumerate(['Temperature (°C)', 'Pressure (kPa)', 'Vibration (g)']):
        pt = cell.read_point(v)
        q10 = cell.read_quantile(0.1, v)
        q90 = cell.read_quantile(0.9, v)
        print(f"  {name}:")
        print(f"    mean = {pt.mean():.2f}, std = {pt.std():.2f}")
        print(f"    90% CI width = {(q90 - q10).mean():.2f}")
        print(f"    day +30 forecast: {pt[-1]:.2f}  CI: [{q10[-1]:.2f}, {q90[-1]:.2f}]")

    # ── 5. Maintenance-window effect ─────────────────────────────────
    # If the forecast is supposed to be different during the maintenance
    # window (370-372), check it.
    print("\nMaintenance-window effect (days 370-372):")
    for v, name in enumerate(['Temp', 'Pressure', 'Vibration']):
        pt = cell.read_point(v)
        before = pt[5]  # day +5 (before window)
        during = pt[10]  # day +10 (during window)
        after = pt[15]  # day +15 (after window)
        print(f"  {name}: before={before:.2f}, during={during:.2f}, after={after:.2f}")

    # ── 6. Plot ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        horizon_t = np.arange(days, days + 30)
        for v, (name, color) in enumerate([
            ('Temperature (°C)', '#7ee787'),
            ('Pressure (kPa)', '#58a6ff'),
            ('Vibration (g)', '#d29922'),
        ]):
            ax = axes[v]
            series = context[:, v]
            ax.plot(t, series, color='#f0883e', label=f'{name} history')
            pt = cell.read_point(v)
            q10 = cell.read_quantile(0.1, v)
            q90 = cell.read_quantile(0.9, v)
            ax.plot(horizon_t, pt, color=color, label='forecast')
            ax.fill_between(horizon_t, q10, q90, color=color, alpha=0.3,
                            label='90% CI')
            # Mark the maintenance window
            ax.axvspan(370, 373, color='#a371f7', alpha=0.2,
                       label='maintenance')
            ax.axvline(days, color='#8b949e', linestyle='--', alpha=0.5)
            ax.set_ylabel(name)
            ax.legend(loc='upper right', fontsize=9)
            ax.grid(alpha=0.3)
        axes[-1].set_xlabel('day')
        plt.suptitle('Quilt time.cell: 3-channel sensor fusion '
                     'with maintenance covariate')
        plt.tight_layout()
        plt.savefig('multivariate_forecast.png', dpi=120)
        print("\nWrote multivariate_forecast.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
