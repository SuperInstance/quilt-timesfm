"""Example 04: anomaly detection via quantile intervals.

The 90% prediction interval gives a statistical band: any actual value
that falls outside the band is a "1-in-10" anomaly (or stronger, if
the actual is far from the band).

The time cell's quantiles are exactly this: 9 quantile prediction
intervals, one per output token. We use them to flag anomalies.

This example uses the synthetic forecast (no torch required).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell


def main() -> None:
    # ── 1. Generate a clean history, then a "test window" ────────────
    days = 365
    t = np.arange(days)
    np.random.seed(13)

    history = (
        10.0
        + 3.0 * np.sin(2 * np.pi * t / 30)   # 30-day cycle
        + 1.0 * np.random.randn(days)         # noise
    )

    # Test window: 30 days, with 2 injected anomalies
    test_window = (
        10.0
        + 3.0 * np.sin(2 * np.pi * np.arange(30) / 30)
        + 1.0 * np.random.randn(30)
    )
    # Inject anomalies
    test_window[5] += 8.0   # 8-sigma spike on day +5
    test_window[20] -= 7.0  # 7-sigma drop on day +20

    # ── 2. Forecast from the clean history ───────────────────────────
    cell = TimeCell()
    cell.bind_context(history)
    cell.set_horizon(30)
    cell.forecast_()

    point = cell.read_point(0)
    q10 = cell.read_quantile(0.1, 0)
    q90 = cell.read_quantile(0.9, 0)
    q01 = cell.read_quantile(0.05, 0)  # 95% band
    q99 = cell.read_quantile(0.95, 0)

    # ── 3. Compare test_window to the prediction interval ─────────────
    print("Anomaly detection report (30-day test window):\n")
    anomalies_90 = []
    anomalies_95 = []
    for t in range(30):
        actual = test_window[t]
        # 90% band
        if actual < q10[t] or actual > q90[t]:
            anomalies_90.append(t)
        # 95% band
        if actual < q01[t] or actual > q99[t]:
            anomalies_95.append(t)
        marker = " ← ANOMALY" if t in anomalies_95 else ""
        print(f"  day +{t+1:2d}: actual={actual:6.2f}  "
              f"90%CI=[{q10[t]:5.2f}, {q90[t]:5.2f}]  "
              f"point={point[t]:5.2f}{marker}")

    print(f"\nFound {len(anomalies_90)} anomalies at the 90% level:")
    for t in anomalies_90:
        actual = test_window[t]
        band = "above" if actual > q90[t] else "below"
        print(f"  day +{t+1}: {actual:.2f} ({band} the 90% band)")
    print(f"\nFound {len(anomalies_95)} anomalies at the 95% level:")
    for t in anomalies_95:
        actual = test_window[t]
        band = "above" if actual > q99[t] else "below"
        print(f"  day +{t+1}: {actual:.2f} ({band} the 95% band)")

    # ── 4. Plot ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(np.arange(days), history, color='#f0883e', label='history (365d)')
        horizon_t = np.arange(days, days + 30)
        ax.plot(horizon_t, point, color='#7ee787', label='forecast (median)')
        ax.fill_between(horizon_t, q10, q90, color='#d29922', alpha=0.3,
                          label='90% CI')
        ax.fill_between(horizon_t, q01, q99, color='#d29922', alpha=0.15,
                          label='95% CI')
        ax.plot(horizon_t, test_window, color='#ff7b72',
                label='test window (with 2 anomalies)', linewidth=2)
        # Mark the injected anomalies
        for t in anomalies_95:
            ax.scatter(days + t, test_window[t], color='#ff7b72',
                       s=80, zorder=10, edgecolor='white', linewidth=1.5)
        ax.axvline(days, color='#8b949e', linestyle='--', alpha=0.5)
        ax.set_xlabel('day')
        ax.set_ylabel('value')
        ax.set_title('Quilt time.cell: anomaly detection via 9 quantile bands')
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig('anomaly_detection.png', dpi=120)
        print("\nWrote anomaly_detection.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
