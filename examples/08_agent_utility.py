"""Example 08: agent utility — the 4th metric.

Demonstrates the agent_utility metric, which combines:
1. -MAE (negative mean absolute error)
2. (1 - |calibration - 0.9|) × 0.5
3. 0.3 × n_actions (number of recommended actions)

The metric rewards forecasts that are not just accurate but also
actionable and well-calibrated.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell
from temporal import (
    TemporalReasoner, ForecastMetrics,
    LifecycleTracker, ForecastObject,
)


def make_forecast(tr, source, horizon=8, noise_level=0.0):
    """Build a fresh forecast for a source."""
    cell = TimeCell()
    t = np.linspace(0, 8 * np.pi, 128)
    cell.bind_context(np.sin(t) + np.random.normal(0, noise_level, 128))
    new_tr = TemporalReasoner(cell, memory=tr.memory)
    return new_tr.forecast_object(source, horizon=horizon)


def main() -> None:
    import quilt_cell
    quilt_cell._TIMESFM_AVAILABLE = False

    print("=" * 60)
    print("Agent utility: comparing 3 forecast models")
    print("=" * 60)

    cell = TimeCell()
    cell.bind_context(np.sin(np.linspace(0, 8 * np.pi, 128)))
    tr = TemporalReasoner(cell)

    # ── 1. Model A: accurate, no actions ───────────────────────
    np.random.seed(0)
    fo_a = make_forecast(tr, "model_a", noise_level=0.01)
    actual_a = [v + np.random.normal(0, 0.05) for v in fo_a.forecast]
    fo_a_updated = tr.record_outcome(fo_a, actual_a)
    actions_a = []  # no actions recommended
    u_a = ForecastMetrics.agent_utility(fo_a_updated, actual_a, actions_a)
    print(f"\nModel A (accurate, no actions):")
    print(f"  MAE:         {ForecastMetrics.mae(fo_a_updated, actual_a):.3f}")
    print(f"  Calibration: {ForecastMetrics.calibration(fo_a_updated, actual_a):.3f}")
    print(f"  Actions:     {len(actions_a)}")
    print(f"  Agent utility: {u_a:.3f}")

    # ── 2. Model B: slightly less accurate, more actions ──────
    np.random.seed(1)
    fo_b = make_forecast(tr, "model_b", noise_level=0.1)
    actual_b = [v + np.random.normal(0, 0.2) for v in fo_b.forecast]
    fo_b_updated = tr.record_outcome(fo_b, actual_b)
    actions_b = [
        {"action": "increase capacity", "expected_benefit": 5.0,
         "confidence": 0.7, "rationale": "forecast shows growth"},
        {"action": "hedge uncertainty", "expected_benefit": 0.0,
         "confidence": 0.5, "rationale": "wide CI"},
    ]
    u_b = ForecastMetrics.agent_utility(fo_b_updated, actual_b, actions_b)
    print(f"\nModel B (less accurate, 2 actions):")
    print(f"  MAE:         {ForecastMetrics.mae(fo_b_updated, actual_b):.3f}")
    print(f"  Calibration: {ForecastMetrics.calibration(fo_b_updated, actual_b):.3f}")
    print(f"  Actions:     {len(actions_b)}")
    print(f"  Agent utility: {u_b:.3f}")

    # ── 3. Model C: very accurate, many actions ───────────────
    np.random.seed(2)
    fo_c = make_forecast(tr, "model_c", noise_level=0.001)
    actual_c = [v + np.random.normal(0, 0.01) for v in fo_c.forecast]
    fo_c_updated = tr.record_outcome(fo_c, actual_c)
    actions_c = [
        {"action": "increase capacity", "expected_benefit": 5.0,
         "confidence": 0.8, "rationale": "..."},
        {"action": "hedge uncertainty", "expected_benefit": 0.0,
         "confidence": 0.5, "rationale": "..."},
        {"action": "monitor", "expected_benefit": 0.0,
         "confidence": 0.9, "rationale": "..."},
    ]
    u_c = ForecastMetrics.agent_utility(fo_c_updated, actual_c, actions_c)
    print(f"\nModel C (very accurate, 3 actions):")
    print(f"  MAE:         {ForecastMetrics.mae(fo_c_updated, actual_c):.3f}")
    print(f"  Calibration: {ForecastMetrics.calibration(fo_c_updated, actual_c):.3f}")
    print(f"  Actions:     {len(actions_c)}")
    print(f"  Agent utility: {u_c:.3f}")

    # ── 4. The verdict ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Verdict")
    print("=" * 60)
    models = [("A (accurate, no actions)", u_a),
              ("B (less accurate, 2 actions)", u_b),
              ("C (very accurate, 3 actions)", u_c)]
    models.sort(key=lambda x: -x[1])
    for name, u in models:
        print(f"  {name}: utility = {u:.3f}")
    print(f"\nWinner: {models[0][0]}")
    print(f"  (Note: by MAE alone, A wins. By agent utility, C wins.)")

    # ── 5. Pinball loss (the 9-quantile metric) ───────────────
    print("\n" + "=" * 60)
    print("Pinball loss (the 9-quantile metric)")
    print("=" * 60)
    for name, fo, actual in [("A", fo_a_updated, actual_a),
                              ("B", fo_b_updated, actual_b),
                              ("C", fo_c_updated, actual_c)]:
        pl = ForecastMetrics.pinball_loss(fo, actual)
        print(f"  Model {name}: pinball loss = {pl:.3f}")


if __name__ == "__main__":
    main()
