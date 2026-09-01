"""Example 03: demand planning (multivariate, 3 channels).

Three correlated demand series (skus A, B, C) are forecasted jointly.
The cell's 3 variates share the quantile intervals — useful for
portfolio decisions like "what's the worst case for A *and* B *and* C?".

This example uses the synthetic forecast (no torch required).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell


def main() -> None:
    # ── 1. Generate 3 correlated demand series ────────────────────────
    days = 365
    t = np.arange(days)
    np.random.seed(7)

    # Common factor (e.g., weather, holiday)
    common = np.sin(2 * np.pi * t / 365) * 5 + np.random.randn(days) * 0.5

    # 3 SKUs: shared + idiosyncratic
    sku_a = 50 + common * 2 + np.random.randn(days) * 3
    sku_b = 30 + common * 1.5 + np.random.randn(days) * 2
    sku_c = 20 + common * 1.0 + np.random.randn(days) * 1.5

    # ── 2. Build the cell ────────────────────────────────────────────
    # Multivariate: stack as [days, 3]
    context = np.stack([sku_a, sku_b, sku_c], axis=1)

    cell = TimeCell()
    cell.bind_context(context)
    cell.set_horizon(30)
    cell.forecast_()

    # ── 3. Print the 30-day forecast for each SKU ────────────────────
    print("30-day demand forecast (3 SKUs):")
    print(f"  {'SKU':<8} {'mean':>8} {'min':>8} {'max':>8} {'q10 mean':>10} {'q90 mean':>10}")
    for v, name in enumerate(['SKU A', 'SKU B', 'SKU C']):
        pt = cell.read_point(v)
        q10 = cell.read_quantile(0.1, v)
        q90 = cell.read_quantile(0.9, v)
        print(f"  {name:<8} {pt.mean():>8.1f} {pt.min():>8.1f} {pt.max():>8.1f} "
              f"{q10.mean():>10.1f} {q90.mean():>10.1f}")

    # ── 4. Worst-case portfolio analysis (joint 10th percentile) ────
    print("\nWorst-case scenario (joint 10th percentile, day +30):")
    q10_a = cell.read_quantile(0.1, 0)[-1]
    q10_b = cell.read_quantile(0.1, 1)[-1]
    q10_c = cell.read_quantile(0.1, 2)[-1]
    total_low = q10_a + q10_b + q10_c
    print(f"  worst-case combined demand = {total_low:.1f} units")

    print("\nBest-case scenario (joint 90th percentile, day +30):")
    q90_a = cell.read_quantile(0.9, 0)[-1]
    q90_b = cell.read_quantile(0.9, 1)[-1]
    q90_c = cell.read_quantile(0.9, 2)[-1]
    total_high = q90_a + q90_b + q90_c
    print(f"  best-case combined demand = {total_high:.1f} units")

    # ── 5. Plot ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        horizon_t = np.arange(days, days + 30)
        for v, (name, color) in enumerate([
            ('SKU A', '#7ee787'),
            ('SKU B', '#58a6ff'),
            ('SKU C', '#d29922'),
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
            ax.axvline(days, color='#8b949e', linestyle='--', alpha=0.5)
            ax.set_ylabel(f'{name} demand')
            ax.legend()
            ax.grid(alpha=0.3)
        axes[-1].set_xlabel('day')
        plt.suptitle('Quilt time.cell: 30-day demand planning (3 SKUs)')
        plt.tight_layout()
        plt.savefig('demand_forecast.png', dpi=120)
        print("\nWrote demand_forecast.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
