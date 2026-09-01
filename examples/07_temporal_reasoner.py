"""Example 07: temporal reasoner — agents with future-state memory.

The 5 examples show:
1. Basic forecast object with explainability
2. Scenarios: optimistic/baseline/pessimistic
3. Counterfactual reasoning: "what if X changes?"
4. Lifecycle tracking: record outcomes, learn from history
5. Decision support: recommend_actions()

This is the pivot from forecasting to future-state memory.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from quilt_cell import TimeCell
from temporal import (
    TemporalReasoner, ForecastObject,
    ScenarioGenerator, CounterfactualReasoner,
    ExplainabilityEngine, LifecycleTracker, AgentMemory,
    DecisionSupport, parse_quf_uri, make_quf_uri,
    ForecastMetrics,
)


def main() -> None:
    # ── 1. Basic forecast object with explainability ─────────────
    print("=" * 60)
    print("1. ForecastObject with explainability")
    print("=" * 60)
    cell = TimeCell()
    t = np.linspace(0, 8 * np.pi, 128)
    cell.bind_context(np.sin(t))
    tr = TemporalReasoner(cell)
    fo = tr.forecast_object("sales", horizon=8)
    print(f"Forecast URI: {fo.uri}")
    print(f"ID: {fo.id}")
    print(f"Trend: {fo.trend}")
    print(f"Confidence: {fo.confidence:.2f}")
    print(f"Forecast: {fo.forecast[:3]}...")
    print(f"Major drivers: {fo.major_drivers[:2]}")
    print(f"Important covariates: {fo.important_covariates}")
    print(f"Uncertainty sources: {fo.uncertainty_sources}")
    print(f"Rationale: {fo.prediction_rationale}")

    # ── 2. Scenarios ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. Scenarios: optimistic/baseline/pessimistic")
    print("=" * 60)
    scs = tr.scenarios(3)
    for s in scs:
        print(f"\n  {s.name.upper()}")
        print(f"    assumption: {s.assumption}")
        print(f"    forecast: {[round(x, 2) for x in s.forecast]}")
        print(f"    probability: {s.probability:.2f}")

    # ── 3. Counterfactual reasoning ─────────────────────────────
    print("\n" + "=" * 60)
    print("3. Counterfactual reasoning: 'what if X changes?'")
    print("=" * 60)
    for var, delta in [
        ("context_mean", 0.20),
        ("context_trend", 0.15),
        ("context_volatility", 0.30),
    ]:
        cf = tr.counterfactual(var, delta)
        print(f"\n  '{var}' {delta:+.0%}:")
        print(f"    baseline sum:   {cf['baseline_sum']:.2f}")
        print(f"    counterfactual: {cf['counterfactual_sum']:.2f}")
        print(f"    impact total:   {cf['impact_total']:+.2f}")
        print(f"    confidence:     {cf['confidence']:.2f}")

    # ── 4. Lifecycle tracking + learning from history ───────────
    print("\n" + "=" * 60)
    print("4. Lifecycle tracking: forecast → actual → learn")
    print("=" * 60)
    print("Simulating 10 days of forecasts for 'cpu-load'...")
    for day in range(10):
        # Simulate a CPU load that varies slightly
        np.random.seed(day)
        new_t = np.linspace(0, 8 * np.pi, 128) + day * 0.1
        cell.bind_context(np.sin(new_t) + 0.1 * np.random.randn(128))
        fo = tr.forecast_object("cpu-load", horizon=8)
        # Simulate the actual outcome (close to forecast)
        actual = [v + np.random.normal(0, 0.05) for v in fo.forecast]
        tr.record_outcome(fo, actual)
    learn = tr.learn_from_history("cpu-load")
    print(f"  Total forecasts: {learn['n_forecasts']}")
    print(f"  Recorded outcomes: {learn['n_recorded_outcomes']}")
    print(f"  Mean error: {learn['mean_error']:.3f}")
    print(f"  Mean calibration: {learn['mean_calibration']:.3f}")
    print(f"  Error trend: {learn['error_trend']}")
    print(f"  Calibration trend: {learn['calibration_trend']}")

    # ── 5. Decision support ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. Decision support: recommend_actions()")
    print("=" * 60)
    # Make a forecast with a spike
    spike_cell = TimeCell()
    spike_context = np.concatenate([np.sin(np.linspace(0, 8 * np.pi, 100)),
                                    np.linspace(0, 30, 28)])
    spike_cell.bind_context(spike_context)
    tr2 = TemporalReasoner(spike_cell, memory=tr.memory)
    fo2 = tr2.forecast_object("demand", horizon=8)
    print(f"Forecast trend: {fo2.trend}")
    print(f"Forecast max: {max(fo2.forecast):.2f}")
    print(f"Forecast mean: {sum(fo2.forecast) / len(fo2.forecast):.2f}")
    actions = tr2.recommend_actions(fo2)
    print(f"\nRecommended actions:")
    for a in actions:
        print(f"  → {a['action']}")
        print(f"    expected benefit: {a['expected_benefit']:.2f}")
        print(f"    confidence: {a['confidence']:.2f}")
        print(f"    rationale: {a['rationale']}")

    # ── 6. quf:// URI scheme ────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. quf:// URI scheme (semantic forecast calculus)")
    print("=" * 60)
    uri = make_quf_uri("revenue", 90, 3)
    print(f"  URI: {uri}")
    parsed = parse_quf_uri(uri)
    print(f"  Parsed: {parsed}")
    # Roundtrip
    print(f"  Roundtrip: scheme={parsed['scheme']}, kind={parsed['kind']}, "
          f"source={parsed['source']}, horizon={parsed['horizon']}, version={parsed['version']}")

    # ── 7. Evaluation metrics ───────────────────────────────────
    print("\n" + "=" * 60)
    print("7. Evaluation metrics")
    print("=" * 60)
    if fo2.prediction_error is not None:
        print(f"  MAE:  {fo2.prediction_error:.3f}")
        print(f"  Calibration: {fo2.calibration_score:.3f}")


if __name__ == "__main__":
    # Disable real TimesFM for the example
    import quilt_cell
    quilt_cell._TIMESFM_AVAILABLE = False

    main()
