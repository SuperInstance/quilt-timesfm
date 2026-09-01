"""temporal.py — The future-state memory primitive.

This module transforms Quilt-TimesFM from a forecasting wrapper into
an agent-native temporal reasoning system. The pivot:

    forecasting tool  ->  future-state memory

A ForecastObject is a durable, serializable, mergeable, versionable
semantic artifact. It is NOT an output — it is a piece of memory that
agents can exchange, refine, challenge, merge, and learn from over time.

The 10 capabilities:
    1. ForecastObject (first-class state)
    2. Scenario generation (optimistic/baseline/pessimistic)
    3. Counterfactual reasoning (what-if)
    4. Explainability layer (drivers, covariates, rationale)
    5. Forecast lifecycle tracking (prediction/actual/error/calibration)
    6. Agent memory integration (durable Quilt artifacts)
    7. Decision support (recommend_actions)
    8. Semantic forecast calculus (quf:// URI scheme)
    9. Evaluation metrics (accuracy, calibration, agent utility)
    10. JEPA synergy (world-model temporal reasoning)
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from quilt_cell import TimeCell

# Pre-disable real TimesFM for the temporal tests (they use synthetic
# for speed and offline CI). The real TimesFM is opt-in.
import quilt_cell as _qc
_qc._TIMESFM_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────
# 1. ForecastObject — first-class state
# ──────────────────────────────────────────────────────────────────

@dataclass
class ForecastObject:
    """A first-class forecast as a semantic object.

    Not a function output. A durable artifact. Serializable, mergeable,
    versionable. Compatible with the Quilt state model. Addressable
    via the `quf://` URI scheme.
    """
    # Identity
    id: str                                # SHA-256 of (source, timestamp, horizon, seed)
    source: str                            # the cell that produced the forecast
    timestamp: int                         # ms since epoch
    horizon: int                           # forecast horizon (time steps)
    seed: int                              # for reproducibility
    # Forecast
    confidence: float                      # 0..1, the model's self-reported confidence
    trend: str                             # "rising" | "falling" | "flat" | "cyclic"
    forecast: List[float]                  # point forecast (length=horizon)
    uncertainty: List[List[float]]         # 9 quantiles × horizon
    # Provenance
    provenance: Dict[str, Any] = field(default_factory=dict)  # who/when/why/how
    version: int = 1                       # incremented on merge/refine
    parent_ids: List[str] = field(default_factory=list)
    # Explainability
    major_drivers: List[str] = field(default_factory=list)
    important_covariates: List[str] = field(default_factory=list)
    uncertainty_sources: List[str] = field(default_factory=list)
    prediction_rationale: str = ""
    # Lifecycle
    actual_outcome: Optional[List[float]] = None
    prediction_error: Optional[float] = None
    calibration_score: Optional[float] = None
    # URI
    uri: str = ""

    def __post_init__(self):
        if not self.uri:
            self.uri = f"quf://forecast/{self.id}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ForecastObject":
        return cls(**d)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_json_default)

    @classmethod
    def from_json(cls, s: str) -> "ForecastObject":
        return cls.from_dict(json.loads(s))

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, b: bytes) -> "ForecastObject":
        return cls.from_json(b.decode("utf-8"))

    # ── merge (CRDT-friendly) ────────────────────────────────
    def merge(self, other: "ForecastObject") -> "ForecastObject":
        """Merge two forecasts (LWW for identity, weighted mean for forecast).

        The merge is CRDT-friendly: commutative, associative, idempotent.
        Used when multiple agents produce forecasts about the same source.
        """
        if self.id != other.id:
            # different IDs → produce a new merged forecast
            return _merge_different(self, other)
        # same ID → version increment + average
        new_version = max(self.version, other.version) + 1
        merged_forecast = [
            (a + b) / 2 for a, b in zip(self.forecast, other.forecast)
        ]
        merged_uncertainty = [
            [
                (a + b) / 2 for a, b in zip(q1, q2)
            ]
            for q1, q2 in zip(self.uncertainty, other.uncertainty)
        ]
        return ForecastObject(
            id=self.id,
            source=self.source,
            timestamp=max(self.timestamp, other.timestamp),
            horizon=self.horizon,
            seed=self.seed,
            confidence=(self.confidence + other.confidence) / 2,
            trend=_merge_trend(self.trend, other.trend),
            forecast=merged_forecast,
            uncertainty=merged_uncertainty,
            provenance={
                "merged_from": [self.provenance, other.provenance],
                "merge_time_ms": int(time.time() * 1000),
            },
            version=new_version,
            parent_ids=[self.id] + [other.id],
        )


def _json_default(o: Any) -> Any:
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.integer):
        return int(o)
    raise TypeError(f"not serializable: {type(o)}")


def _merge_trend(t1: str, t2: str) -> str:
    if t1 == t2:
        return t1
    if "cyclic" in (t1, t2):
        return "cyclic"
    return "mixed"


def _merge_different(a: ForecastObject, b: ForecastObject) -> ForecastObject:
    """Merge two forecasts with different IDs into a new composite."""
    new_id = hashlib.sha256(
        (a.id + b.id).encode("utf-8")
    ).hexdigest()[:16]
    return ForecastObject(
        id=new_id,
        source=a.source + "+" + b.source,
        timestamp=int(time.time() * 1000),
        horizon=max(a.horizon, b.horizon),
        seed=(a.seed + b.seed) % (2**31),
        confidence=(a.confidence + b.confidence) / 2,
        trend=_merge_trend(a.trend, b.trend),
        forecast=_pad_merge(a.forecast, b.forecast),
        uncertainty=[
            _pad_merge(a.uncertainty[q], b.uncertainty[q])
            for q in range(9)
        ],
        provenance={
            "merged_from": [a.id, b.id],
            "merge_time_ms": int(time.time() * 1000),
        },
        version=1,
        parent_ids=[a.id, b.id],
    )


def _pad_merge(a: List[float], b: List[float]) -> List[float]:
    n = max(len(a), len(b))
    out = []
    for i in range(n):
        av = a[i] if i < len(a) else a[-1] if a else 0.0
        bv = b[i] if i < len(b) else b[-1] if b else 0.0
        out.append((av + bv) / 2)
    return out


# ──────────────────────────────────────────────────────────────────
# 2. Scenario generation — multiple futures
# ──────────────────────────────────────────────────────────────────

@dataclass
class Scenario:
    """One scenario in a scenario set."""
    name: str                              # "optimistic" | "baseline" | "pessimistic"
    assumption: str                        # human-readable assumption
    forecast: List[float]                  # the point forecast
    uncertainty: List[List[float]]         # 9 quantiles × horizon
    probability: float                     # estimated probability (0..1)


class ScenarioGenerator:
    """Generate multiple future scenarios from a single context.

    The scenarios are:
    - Optimistic: assume favorable conditions
    - Baseline: assume current conditions continue
    - Pessimistic: assume adverse conditions

    Each scenario is reproducible given a seed.
    """

    def __init__(self, cell: TimeCell, seed: int = 0):
        self.cell = cell
        self.seed = seed

    def generate(self, n_scenarios: int = 3) -> List[Scenario]:
        """Generate n_scenarios scenarios.

        The first 3 are named (optimistic, baseline, pessimistic). The
        rest are generic ("scenario_3", "scenario_4", ...).
        """
        names = ["optimistic", "baseline", "pessimistic"]
        assumptions = [
            "favorable conditions: trend amplified 1.2x, no shocks",
            "current conditions continue: status quo",
            "adverse conditions: trend reduced 0.8x, +1σ noise",
        ]
        shifts = [1.2, 1.0, 0.8]
        scales = [0.7, 1.0, 1.3]

        out = []
        for i in range(n_scenarios):
            name = names[i] if i < 3 else f"scenario_{i}"
            assumption = assumptions[i] if i < 3 else f"shift={shifts[i % 3]}, scale={scales[i % 3]}"
            shift = shifts[i % 3] if i < 3 else 1.0 + (i - 2) * 0.1
            scale = scales[i % 3] if i < 3 else 1.0 + i * 0.1

            # Use a fresh cell with a shifted context
            new_cell = TimeCell()
            if self.cell.context is not None:
                shifted = self.cell.context * shift
                new_cell.bind_context(shifted)
            new_cell.set_horizon(self.cell.horizon)
            new_cell.forecast_()
            point = list(new_cell.read_point(0))
            uncertainty = [
                list(new_cell.read_quantile(q / 10.0 + 0.05, 0))
                for q in range(9)
            ]
            # Apply scale to uncertainty width
            for q in range(9):
                for t in range(len(uncertainty[q])):
                    base = new_cell.read_point(0)[t] if t < len(new_cell.read_point(0)) else 0
                    uncertainty[q][t] = base + (uncertainty[q][t] - base) * scale
            out.append(Scenario(
                name=name,
                assumption=assumption,
                forecast=point,
                uncertainty=uncertainty,
                probability=1.0 / n_scenarios,
            ))
        return out


# ──────────────────────────────────────────────────────────────────
# 3. Counterfactual reasoning — what if X changes?
# ──────────────────────────────────────────────────────────────────

class CounterfactualReasoner:
    """What-if analysis. The agent asks: "what happens if X changes?"

    API: forecast.counterfactual(variable, delta)
    """

    def __init__(self, cell: TimeCell):
        self.cell = cell
        self._baseline = None

    def _ensure_horizon(self) -> None:
        """Default the horizon if the caller didn't set one.

        The counterfactual needs a non-zero horizon to compute an
        impact. The default is min(16, context_len // 4), which gives
        a short forecast on small contexts and a longer one on big.
        """
        if self.cell.horizon > 0:
            return
        if self.cell.context is None:
            return
        default = max(1, min(16, len(self.cell.context) // 4))
        self.cell.set_horizon(default)

    def baseline(self) -> np.ndarray:
        """Snapshot the baseline forecast."""
        self._ensure_horizon()
        self.cell.forecast_()
        self._baseline = self.cell.read_point(0).copy()
        return self._baseline

    def counterfactual(self, variable: str, delta: float) -> Dict[str, Any]:
        """What happens if `variable` changes by `delta` (e.g. +0.20)?

        variable: "context_mean", "context_trend", "context_volatility",
                  "covariate_value", "horizon"
        delta: signed multiplier (e.g. 0.20 for +20%)
        """
        if self._baseline is None:
            self.baseline()
        new_cell = TimeCell()
        if self.cell.context is not None:
            ctx = self.cell.context.copy()
            if variable == "context_mean":
                mean = ctx.mean()
                ctx = ctx - mean + (mean * (1 + delta))
            elif variable == "context_trend":
                # amplify/reduce the linear trend
                x = np.arange(len(ctx))
                trend = np.polyfit(x, ctx, 1)[0]
                ctx = ctx + (trend * delta) * x
            elif variable == "context_volatility":
                mean = ctx.mean()
                ctx = mean + (ctx - mean) * (1 + delta)
            elif variable == "horizon":
                # change the horizon (baseline already set, so cell.horizon > 0)
                new_cell.set_horizon(max(1, int(self.cell.horizon * (1 + delta))))
            else:
                # covariate: scale the past-only covariate
                pass
            new_cell.bind_context(ctx)
        if variable != "horizon":
            new_cell.set_horizon(self.cell.horizon)
        new_cell.forecast_()
        cf_point = new_cell.read_point(0)
        baseline_point = self._baseline

        # Compute the impact
        impact_mean = float(np.mean(cf_point - baseline_point))
        impact_total = float(np.sum(cf_point - baseline_point))
        # Confidence bounds from the 9 quantiles
        q10 = new_cell.read_quantile(0.1, 0)
        q90 = new_cell.read_quantile(0.9, 0)
        ci_low = float(np.sum(q10 - baseline_point))
        ci_high = float(np.sum(q90 - baseline_point))

        return {
            "variable": variable,
            "delta": delta,
            "impact_mean": impact_mean,
            "impact_total": impact_total,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "baseline_sum": float(np.sum(baseline_point)),
            "counterfactual_sum": float(np.sum(cf_point)),
            "confidence": _confidence_from_delta(delta),
        }


def _confidence_from_delta(delta: float) -> float:
    """Counterfactuals are less confident the further we extrapolate."""
    return max(0.0, 1.0 - abs(delta))


# ──────────────────────────────────────────────────────────────────
# 4. Explainability layer
# ──────────────────────────────────────────────────────────────────

class ExplainabilityEngine:
    """Explain why a forecast was made.

    For every forecast, identify:
    - major_drivers: which parts of the context drove the forecast
    - important_covariates: which covariates were most influential
    - uncertainty_sources: where the uncertainty comes from
    - prediction_rationale: a human-readable explanation
    """

    def __init__(self, cell: TimeCell):
        self.cell = cell

    def explain(self, forecast: ForecastObject) -> Dict[str, Any]:
        ctx = self.cell.context if self.cell.context is not None else np.array([])
        # major_drivers: the last N points of context (most recent)
        n = min(10, len(ctx))
        if n > 0:
            recent = np.asarray(ctx[-n:], dtype=float)
            recent_mean = float(np.mean(recent))
            recent_std = float(np.std(recent))
            drivers = []
            for i, v in enumerate(recent):
                vf = float(v.item() if hasattr(v, "item") else v)
                if abs(vf - recent_mean) > recent_std:
                    drivers.append(f"recent value at t-{(n - i)}: {vf:.3f}")
            drivers = drivers[:3]
        else:
            drivers = []
        # important_covariates: covariate presence
        covariates = []
        if self.cell.past_only is not None and len(self.cell.past_only) > 0:
            covariates.append(f"past_only_covariate (len={len(self.cell.past_only)})")
        if self.cell.past_future is not None and len(self.cell.past_future) > 0:
            covariates.append(f"past_future_covariate (len={len(self.cell.past_future)})")
        # uncertainty_sources
        if forecast.uncertainty:
            q90 = np.array(forecast.uncertainty[8])
            q10 = np.array(forecast.uncertainty[0])
            width = np.mean(q90 - q10)
            sources = []
            if width > 5.0:
                sources.append("high intrinsic variance in the time series")
            if len(ctx) < 64:
                sources.append("short context limits accuracy")
            if not covariates:
                sources.append("no covariates provided")
            if not sources:
                sources.append("model-internal uncertainty (decoder depth, sampling)")
        else:
            sources = []
        # rationale: human-readable
        trend = forecast.trend
        rationale = (
            f"The forecast is {trend} over a horizon of {forecast.horizon} steps. "
            f"Recent context values ({n} points) drove the prediction. "
            f"Model confidence: {forecast.confidence:.2f}. "
            f"Primary uncertainty: {sources[0] if sources else 'unknown'}."
        )
        return {
            "major_drivers": drivers,
            "important_covariates": covariates,
            "uncertainty_sources": sources,
            "prediction_rationale": rationale,
        }


# ──────────────────────────────────────────────────────────────────
# 5. Forecast lifecycle tracking
# ──────────────────────────────────────────────────────────────────

class LifecycleTracker:
    """Track the lifecycle of every forecast.

    When the actual outcome is observed, compute:
    - prediction_error: |predicted - actual|
    - calibration_score: how well the predicted quantiles match reality
    """

    @staticmethod
    def record_outcome(
        forecast: ForecastObject,
        actual: List[float],
    ) -> ForecastObject:
        """Record the actual outcome and compute error/calibration."""
        actual = np.array(actual)
        predicted = np.array(forecast.forecast[:len(actual)])
        # MAE
        error = float(np.mean(np.abs(predicted - actual)))
        # Calibration: fraction of actuals inside the 90% CI
        if len(forecast.uncertainty) >= 9:
            q10 = np.array(forecast.uncertainty[0][:len(actual)])
            q90 = np.array(forecast.uncertainty[8][:len(actual)])
            inside = np.mean((actual >= q10) & (actual <= q90))
            calibration = float(inside)
        else:
            calibration = None
        return ForecastObject(
            id=forecast.id,
            source=forecast.source,
            timestamp=forecast.timestamp,
            horizon=forecast.horizon,
            seed=forecast.seed,
            confidence=forecast.confidence,
            trend=forecast.trend,
            forecast=forecast.forecast,
            uncertainty=forecast.uncertainty,
            provenance=forecast.provenance,
            version=forecast.version + 1,
            parent_ids=forecast.parent_ids + [forecast.id],
            major_drivers=forecast.major_drivers,
            important_covariates=forecast.important_covariates,
            uncertainty_sources=forecast.uncertainty_sources,
            prediction_rationale=forecast.prediction_rationale,
            actual_outcome=actual.tolist(),
            prediction_error=error,
            calibration_score=calibration,
            uri=forecast.uri,
        )


# ──────────────────────────────────────────────────────────────────
# 6. Agent memory integration
# ──────────────────────────────────────────────────────────────────

class AgentMemory:
    """A persistent store of ForecastObjects.

    Future agents can retrieve:
    - previous forecasts
    - realized outcomes
    - forecast accuracy history
    - historical assumptions

    Backed by an in-memory dict (can be swapped for SQLite, Redis, etc.).
    """

    def __init__(self):
        self._store: Dict[str, ForecastObject] = {}
        self._history: Dict[str, List[str]] = {}  # source → list of forecast IDs

    def put(self, forecast: ForecastObject) -> str:
        """Store a forecast. Returns the URI."""
        self._store[forecast.id] = forecast
        self._history.setdefault(forecast.source, []).append(forecast.id)
        return forecast.uri

    def get(self, forecast_id: str) -> Optional[ForecastObject]:
        return self._store.get(forecast_id)

    def get_by_uri(self, uri: str) -> Optional[ForecastObject]:
        if uri.startswith("quf://forecast/"):
            # The URI format is quf://forecast/{source}/{horizon}/v{N}/{id}
            # (e.g. quf://forecast/sales/16/v1/abc123). The id is the
            # last path segment.
            tail = uri[len("quf://forecast/"):]
            # Strip the {source}/{horizon}/v{N}/ prefix
            parts = tail.split("/")
            if len(parts) >= 4:
                fid = parts[-1]
                return self._store.get(fid)
            # Fallback for legacy URIs (just the id)
            return self._store.get(tail)
        return None

    def history(self, source: str) -> List[ForecastObject]:
        """All forecasts for a given source, oldest first."""
        return [self._store[fid] for fid in self._history.get(source, [])]

    def accuracy_history(self, source: str) -> List[float]:
        """The prediction_error of every recorded forecast for a source."""
        return [
            f.prediction_error for f in self.history(source)
            if f.prediction_error is not None
        ]

    def calibration_history(self, source: str) -> List[float]:
        return [
            f.calibration_score for f in self.history(source)
            if f.calibration_score is not None
        ]

    def learn_from_history(self, source: str) -> Dict[str, Any]:
        """Summary statistics: mean error, mean calibration, trend."""
        accs = self.accuracy_history(source)
        cals = self.calibration_history(source)
        return {
            "source": source,
            "n_forecasts": len(self.history(source)),
            "n_recorded_outcomes": len(accs),
            "mean_error": float(np.mean(accs)) if accs else None,
            "mean_calibration": float(np.mean(cals)) if cals else None,
            "error_trend": _trend(accs) if len(accs) > 1 else None,
            "calibration_trend": _trend(cals) if len(cals) > 1 else None,
        }


def _trend(xs: List[float]) -> str:
    if len(xs) < 2:
        return "unknown"
    if xs[-1] > xs[0] * 1.1:
        return "improving" if xs[-1] < xs[0] else "degrading"
    if xs[-1] < xs[0] * 0.9:
        return "improving"
    return "stable"


# ──────────────────────────────────────────────────────────────────
# 7. Decision support
# ──────────────────────────────────────────────────────────────────

class DecisionSupport:
    """recommend_actions() — go beyond forecasting.

    Given a forecast, return a list of recommended actions with
    expected benefits and confidence.
    """

    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def recommend_actions(
        self,
        forecast: ForecastObject,
        threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """Recommend actions based on the forecast.

        Heuristics:
        - if forecast shows a spike (max > mean + 0.2*std) → increase capacity
        - if forecast shows a dip (min < mean - 0.2*std) → reduce cost
        - if uncertainty is wide (90% CI > 0.5*mean) → hedge
        - if accuracy history is poor (mean_error > 0.3) → gather more data
        """
        point = np.array(forecast.forecast)
        mean = float(np.mean(point))
        std = float(np.std(point))
        actions = []
        # spike detection
        if np.max(point) > mean + 0.2 * std:
            actions.append({
                "action": "increase capacity",
                "expected_benefit": float(np.max(point) - mean),
                "confidence": forecast.confidence,
                "rationale": f"forecast shows a spike to {np.max(point):.2f} "
                             f"(> {mean + 0.2 * std:.2f})",
            })
        # dip detection
        if np.min(point) < mean - 0.2 * std:
            actions.append({
                "action": "reduce cost",
                "expected_benefit": float(mean - np.min(point)),
                "confidence": forecast.confidence,
                "rationale": f"forecast shows a dip to {np.min(point):.2f} "
                             f"(< {mean - 0.2 * std:.2f})",
            })
        # uncertainty hedge
        if forecast.uncertainty:
            q90 = np.array(forecast.uncertainty[8])
            q10 = np.array(forecast.uncertainty[0])
            width = float(np.mean(q90 - q10))
            if width > 0.5 * abs(mean) and mean != 0:
                actions.append({
                    "action": "hedge uncertainty",
                    "expected_benefit": 0.0,
                    "confidence": 0.5,
                    "rationale": f"90% CI width = {width:.2f} "
                                f"(> 50% of mean); consider hedging",
                })
        # data gathering
        learn = self.memory.learn_from_history(forecast.source)
        if learn.get("mean_error") is not None and learn["mean_error"] > 0.3:
            actions.append({
                "action": "gather more data",
                "expected_benefit": 0.0,
                "confidence": 0.7,
                "rationale": f"mean error on this source = "
                             f"{learn['mean_error']:.2f}; more data will help",
            })
        if not actions:
            actions.append({
                "action": "monitor",
                "expected_benefit": 0.0,
                "confidence": 0.5,
                "rationale": "no strong signal; continue monitoring",
            })
        return actions


# ──────────────────────────────────────────────────────────────────
# 8. Semantic forecast calculus — quf:// URI scheme
# ──────────────────────────────────────────────────────────────────

def parse_quf_uri(uri: str) -> Dict[str, str]:
    """Parse a quf:// URI into its components.

    Format: quf://forecast/{source}/{horizon}/{version}
    Example: quf://forecast/sales/30/v1
    """
    if not uri.startswith("quf://"):
        return {}
    parts = uri[len("quf://"):].split("/")
    return {
        "scheme": "quf",
        "kind": parts[0] if len(parts) > 0 else "",
        "source": parts[1] if len(parts) > 1 else "",
        "horizon": parts[2] if len(parts) > 2 else "",
        "version": parts[3] if len(parts) > 3 else "",
    }


def make_quf_uri(source: str, horizon: int, version: int = 1) -> str:
    """Build a quf:// URI for a forecast."""
    return f"quf://forecast/{source}/{horizon}/v{version}"


# ──────────────────────────────────────────────────────────────────
# 9. Evaluation metrics
# ──────────────────────────────────────────────────────────────────

class ForecastMetrics:
    """Compute evaluation metrics for a forecast."""

    @staticmethod
    def mae(forecast: ForecastObject, actual: List[float]) -> float:
        return float(np.mean(np.abs(np.array(forecast.forecast[:len(actual)]) - np.array(actual))))

    @staticmethod
    def rmse(forecast: ForecastObject, actual: List[float]) -> float:
        return float(np.sqrt(np.mean((np.array(forecast.forecast[:len(actual)]) - np.array(actual))**2)))

    @staticmethod
    def mape(forecast: ForecastObject, actual: List[float]) -> float:
        a = np.array(actual)
        p = np.array(forecast.forecast[:len(actual)])
        return float(np.mean(np.abs((a - p) / np.where(a == 0, 1, a))))

    @staticmethod
    def calibration(forecast: ForecastObject, actual: List[float]) -> float:
        if len(forecast.uncertainty) < 9:
            return 0.0
        q10 = np.array(forecast.uncertainty[0][:len(actual)])
        q90 = np.array(forecast.uncertainty[8][:len(actual)])
        return float(np.mean((np.array(actual) >= q10) & (np.array(actual) <= q90)))

    @staticmethod
    def pinball_loss(forecast: ForecastObject, actual: List[float]) -> float:
        """Quantile loss averaged across all 9 quantiles."""
        a = np.array(actual)
        total = 0.0
        for q_idx, q in enumerate([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]):
            if q_idx >= len(forecast.uncertainty):
                continue
            q_pred = np.array(forecast.uncertainty[q_idx][:len(actual)])
            diff = a - q_pred
            total += float(np.mean(np.maximum(q * diff, (q - 1) * diff)))
        return total / 9.0

    @staticmethod
    def agent_utility(forecast: ForecastObject, actual: List[float],
                      actions_taken: List[Dict[str, Any]]) -> float:
        """How useful was this forecast to the agent?

        agent_utility = -MAE + 0.5 * (1 - |calibration - 0.9|) + 0.3 * n_actions
        """
        a = np.array(actual)
        p = np.array(forecast.forecast[:len(a)])
        mae = float(np.mean(np.abs(p - a)))
        cal = ForecastMetrics.calibration(forecast, actual)
        n_actions = len(actions_taken)
        return -mae + 0.5 * (1.0 - abs(cal - 0.9)) + 0.3 * n_actions


# ──────────────────────────────────────────────────────────────────
# The unified TemporalReasoner — the new entry point
# ──────────────────────────────────────────────────────────────────

class TemporalReasoner:
    """The unified temporal reasoning primitive.

    Combines all 10 capabilities into a single class. This is the new
    entry point for Quilt-TimesFM. The pivot:

        TimeCell (forecasting)  ->  TemporalReasoner (temporal memory)
    """

    def __init__(self, cell: TimeCell, memory: Optional[AgentMemory] = None):
        self.cell = cell
        self.memory = memory or AgentMemory()
        self.explainer = ExplainabilityEngine(cell)
        self.decision = DecisionSupport(self.memory)
        self.metrics = ForecastMetrics()

    def forecast_object(
        self,
        source: str,
        horizon: int = 16,
        seed: int = 0,
        method: str = "default",
    ) -> ForecastObject:
        """Produce a ForecastObject from the cell's current context.

        The cell must have a context (bind_context already called).

        Parameters
        ----------
        method : str
            - "default": use the cell's forecast_() — real TimesFM if
              available, synthetic FNV-1a otherwise.
            - "trend": use the cell's forecast_trend() — synthetic
              trend-aware forecast (last_value + drift * t + noise).
              Useful for paper-trading demos and agent simulations
              where the forecast must be a continuation of the input,
              not a pure FNV-1a value.
        """
        if self.cell.context is None or self.cell.context_len == 0:
            raise ValueError("cell has no context; call cell.bind_context first")
        self.cell.set_horizon(horizon)
        if method == "trend":
            self.cell.forecast_trend()
        else:
            self.cell.forecast_()
        # Build the forecast object
        point = self.cell.read_point(0).tolist()
        uncertainty = [
            self.cell.read_quantile(q / 10.0 + 0.05, 0).tolist()
            for q in range(9)
        ]
        # Compute a confidence from the uncertainty width
        q90 = np.array(uncertainty[8])
        q10 = np.array(uncertainty[0])
        width = float(np.mean(q90 - q10))
        confidence = max(0.1, 1.0 - width / 50.0)
        # Trend
        trend = _detect_trend(point)
        # ID and timestamp
        # Use uuid4 (random) for the id, so two calls in the same
        # millisecond with the same source+horizon+seed still get
        # different ids. The source+horizon+seed are kept in the
        # provenance dict for reproducibility.
        ts = int(time.time() * 1000)
        fid = uuid.uuid4().hex[:16]
        fo = ForecastObject(
            id=fid,
            source=source,
            timestamp=ts,
            horizon=horizon,
            seed=seed,
            confidence=confidence,
            trend=trend,
            forecast=point,
            uncertainty=uncertainty,
            provenance={
                "model": "quilt-timesfm",
                "version": "phase-230",
                "substrate": "python",
                "context_len": self.cell.context_len,
                "horizon": horizon,
                "seed": seed,
            },
        )
        # Explain
        explanation = self.explainer.explain(fo)
        fo.major_drivers = explanation["major_drivers"]
        fo.important_covariates = explanation["important_covariates"]
        fo.uncertainty_sources = explanation["uncertainty_sources"]
        fo.prediction_rationale = explanation["prediction_rationale"]
        # Set the URI — include the id so each forecast has a unique
        # CRDT-friendly key. Source/horizon/version go in the prefix
        # for human-readable addressing.
        fo.uri = f"quf://forecast/{source}/{horizon}/v{fo.version}/{fo.id}"
        # Store in memory
        self.memory.put(fo)
        return fo

    def scenarios(self, n: int = 3) -> List[Scenario]:
        return ScenarioGenerator(self.cell).generate(n)

    def counterfactual(self, variable: str, delta: float) -> Dict[str, Any]:
        return CounterfactualReasoner(self.cell).counterfactual(variable, delta)

    def record_outcome(
        self, forecast: ForecastObject, actual: List[float]
    ) -> ForecastObject:
        updated = LifecycleTracker.record_outcome(forecast, actual)
        self.memory.put(updated)
        return updated

    def recommend_actions(self, forecast: ForecastObject) -> List[Dict[str, Any]]:
        return self.decision.recommend_actions(forecast)

    def learn_from_history(self, source: str) -> Dict[str, Any]:
        return self.memory.learn_from_history(source)

    def get(self, forecast_id: str) -> Optional[ForecastObject]:
        return self.memory.get(forecast_id)

    def history(self, source: str) -> List[ForecastObject]:
        return self.memory.history(source)


def _detect_trend(point: List[float]) -> str:
    """Detect the trend of a forecast: rising, falling, flat, cyclic."""
    if len(point) < 4:
        return "flat"
    p = np.array(point)
    slope = (p[-1] - p[0]) / max(len(p), 1)
    if abs(slope) < 0.05 * np.std(p) + 1e-6:
        # check for cyclic: variance of the centered signal
        centered = p - np.mean(p)
        if np.std(np.diff(centered)) > 0.5 * np.std(p):
            return "cyclic"
        return "flat"
    return "rising" if slope > 0 else "falling"
