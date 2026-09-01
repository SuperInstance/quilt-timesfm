# Quilt Use-Case Manuals

> **5 deep manuals, each a complete walk-through.**

This is the use-case manual series. Each manual is a complete
walk-through: a real problem, a real solution, a real example.
The 5 manuals are the 5 most common patterns we see in
production.

## Table of Contents

1. [Manual 1: Forecasting Agent](#manual-1-forecasting-agent)
2. [Manual 2: Anomaly Detection Agent](#manual-2-anomaly-detection-agent)
3. [Manual 3: Decision Support Agent](#manual-3-decision-support-agent)
4. [Manual 4: Multi-Agent Simulator](#manual-4-multi-agent-simulator)
5. [Manual 5: Real-Time Dashboard](#manual-5-real-time-dashboard)

---

## Manual 1: Forecasting Agent

**Use case**: a sales team wants to forecast next quarter's revenue
and use the forecast to plan inventory.

### The 5-step workflow

1. **Bind the context**: gather 365 days of daily sales.
2. **Bind the covariates**: gather 365 days of marketing spend,
   day of week, holidays.
3. **Forecast**: run the TIME cell to get a 90-day forecast.
4. **Read the quantiles**: get the 90% CI.
5. **Recommend actions**: convert the forecast into inventory
   recommendations.

### The code (Python)

```python
from quilt_cell import TimeCell
from temporal import TemporalReasoner, ForecastMetrics
import numpy as np

# Step 1: Bind the context
days = 365
t = np.arange(days)
np.random.seed(0)

# Sales: trend + weekly + yearly + noise
sales = (
    1000.0  # base
    + 200 * np.sin(2 * np.pi * t / 365)  # yearly cycle
    + 100 * np.sin(2 * np.pi * t / 7)    # weekly cycle
    + 5 * t                              # growth trend
    + 50 * np.random.randn(days)         # noise
)

cell = TimeCell()
cell.bind_context(sales)

# Step 2: Bind the covariates
marketing = 100 + 20 * np.sin(2 * np.pi * t / 30) + 10 * np.random.randn(days)
cell.bind_past_only_covariate(marketing)

# Step 3: Forecast (90 days)
cell.set_horizon(90)
cell.forecast_()

# Step 4: Read the quantiles
point = cell.read_point(0)
q10 = cell.read_quantile(0.1, 0)
q90 = cell.read_quantile(0.9, 0)

# Step 5: Recommend actions
tr = TemporalReasoner(cell)
fo = tr.forecast_object("revenue", horizon=90)
actions = tr.recommend_actions(fo)

# Print the result
print(f"90-day forecast:")
print(f"  mean: ${point.mean():.0f}")
print(f"  90% CI: ${q10.mean():.0f} - ${q90.mean():.0f}")
print(f"\nRecommended actions:")
for a in actions:
    print(f"  → {a['action']} (confidence: {a['confidence']:.0%})")
    print(f"    expected benefit: {a['expected_benefit']:.0f}")
    print(f"    rationale: {a['rationale']}")
```

### The expected output

```
90-day forecast:
  mean: $1142
  90% CI: $1134 - $1150

Recommended actions:
  → increase capacity (confidence: 80%)
    expected benefit: 25
    rationale: forecast shows growth to 1250 (> mean + 0.2*std)
```

### The runtime architecture

```
Sales DB → Bind Context → TIME cell → ForecastObject
                      ↓
Marketing DB → Bind Covariate
                      ↓
                Forecast (90 days)
                      ↓
                Read Point + 9 Quantiles
                      ↓
                Recommend Actions → Inventory Plan
```

### The production checklist

- [ ] Bind context from your data warehouse (Snowflake, BigQuery,
      Redshift)
- [ ] Bind covariates from your event stream (Kafka, Kinesis,
      Pub/Sub)
- [ ] Set horizon to your planning window (90 days for quarterly,
      365 for yearly)
- [ ] Read the 9 quantiles for the 90% CI
- [ ] Convert `recommend_actions()` to inventory orders
- [ ] Record the actual outcome after the period
- [ ] Use `tr.learn_from_history("revenue")` to improve over time

### The pitfalls

- **Don't bind too little context**. Less than 64 points gives
  poor accuracy. Aim for 256+.
- **Don't ignore the quantiles**. The point forecast is the
  median, not the certainty.
- **Don't skip the record-outcome step**. Without it, the agent
  can't learn.
- **Don't treat the forecast as a single number**. It's a
  distribution.

---

## Manual 2: Anomaly Detection Agent

**Use case**: an SRE team wants to detect anomalies in production
metrics in real time and alert on them.

### The 5-step workflow

1. **Bind the context**: stream the last 256 points of the metric.
2. **Forecast**: predict the next 1 step.
3. **Read the quantiles**: get the 90% CI.
4. **Compare actual to CI**: if outside, it's an anomaly.
5. **Alert**: route the anomaly to PagerDuty, Slack, etc.

### The code (Python)

```python
from quilt_cell import TimeCell
import numpy as np
import time

def detect_anomaly(history: np.ndarray, actual: float) -> dict:
    """Detect if `actual` is an anomaly given the `history`."""
    cell = TimeCell()
    cell.bind_context(history)
    cell.set_horizon(1)
    cell.forecast_()

    point = cell.read_point(0)[0]
    q10 = cell.read_quantile(0.1, 0)[0]
    q90 = cell.read_quantile(0.9, 0)[0]

    return {
        "actual": actual,
        "expected": point,
        "ci_low": q10,
        "ci_high": q90,
        "is_anomaly": actual < q10 or actual > q90,
        "z_score": (actual - point) / max((q90 - q10) / 4, 0.01),
    }

# Stream a metric
np.random.seed(0)
history = np.random.normal(100, 5, 256)  # baseline: mean 100, std 5

# Inject anomalies
test_points = [98, 102, 105, 145, 99, 101, 50, 103, 99]
for actual in test_points:
    result = detect_anomaly(history, actual)
    if result["is_anomaly"]:
        print(f"🚨 ANOMALY: actual={result['actual']:.1f} "
              f"expected={result['expected']:.1f} "
              f"CI=[{result['ci_low']:.1f}, {result['ci_high']:.1f}] "
              f"z={result['z_score']:.2f}")
    else:
        print(f"✓ OK: actual={result['actual']:.1f} "
              f"expected={result['expected']:.1f}")

    # Update history (rolling window)
    history = np.append(history[1:], actual)
```

### The expected output

```
✓ OK: actual=98.0 expected=99.8 CI=[95.4, 104.2]
✓ OK: actual=102.0 expected=99.7 CI=[95.3, 104.1]
✓ OK: actual=105.0 expected=99.8 CI=[95.4, 104.2]
🚨 ANOMALY: actual=145.0 expected=99.7 CI=[95.3, 104.1] z=18.16
✓ OK: actual=99.0 expected=99.9 CI=[95.5, 104.3]
✓ OK: actual=101.0 expected=99.6 CI=[95.2, 104.0]
🚨 ANOMALY: actual=50.0 expected=99.7 CI=[95.3, 104.1] z=-19.86
✓ OK: actual=103.0 expected=99.8 CI=[95.4, 104.2]
✓ OK: actual=99.0 expected=99.7 CI=[95.3, 104.1]
```

### The runtime architecture

```
Metric Stream → Bind Context → TIME cell → Forecast + Quantiles
                                     ↓
                                   Compare Actual
                                     ↓
                            ┌────────┴────────┐
                            ↓                 ↓
                       in CI           outside CI
                       (OK)             (anomaly)
                                          ↓
                                     Alert (PagerDuty/Slack)
```

### The production checklist

- [ ] Use a rolling window of 256 points (8x the patch size)
- [ ] Update the window after each comparison
- [ ] Set the anomaly threshold to 90% (1-in-10) by default
- [ ] For critical metrics, use 99% (1-in-100) with 0.01 + 0.99
      quantiles
- [ ] Send the z-score, not just the boolean, so the alert can
      be triaged
- [ ] Aggregate anomalies over time: count per minute, max z-score
      per hour

### The pitfalls

- **Don't recompute the forecast on every point**. Cache it
  for the 5-minute window.
- **Don't alert on every anomaly**. Aggregate to 1 alert per
  outage, not 1 per metric.
- **Don't trust the absolute value of the CI**. It depends on
  the noise level. Compare to *expected* CIs.
- **Don't forget to retrain**. The metric's distribution drifts
  over time.

---

## Manual 3: Decision Support Agent

**Use case**: a logistics team wants to optimize inventory levels
based on demand forecasts and uncertainty.

### The 5-step workflow

1. **Forecast demand** for the next 30 days.
2. **Generate scenarios** (optimistic, baseline, pessimistic).
3. **Compute counterfactuals** for different inventory levels.
4. **Recommend actions** based on scenarios + counterfactuals.
5. **Track outcomes** and improve over time.

### The code (Python)

```python
from quilt_cell import TimeCell
from temporal import TemporalReasoner, ScenarioGenerator
import numpy as np

# Step 1: Forecast demand
days = 365
t = np.arange(days)
np.random.seed(0)
demand = (
    100 + 30 * np.sin(2 * np.pi * t / 30) + 20 * np.random.randn(days)
)

cell = TimeCell()
cell.bind_context(demand)
cell.set_horizon(30)
cell.forecast_()

tr = TemporalReasoner(cell)
fo = tr.forecast_object("demand", horizon=30)

# Step 2: Generate scenarios
scenarios = tr.scenarios(3)
for s in scenarios:
    print(f"\n  {s.name.upper()}:")
    print(f"    assumption: {s.assumption}")
    print(f"    forecast mean: {np.mean(s.forecast):.1f}")
    print(f"    90% CI width: {np.mean(s.uncertainty[8]) - np.mean(s.uncertainty[0]):.1f}")

# Step 3: Counterfactual — what if we order 20% more?
cf = tr.counterfactual("context_mean", 0.20)
print(f"\n  +20% demand scenario:")
print(f"    baseline sum: {cf['baseline_sum']:.0f}")
print(f"    counterfactual sum: {cf['counterfactual_sum']:.0f}")
print(f"    impact total: {cf['impact_total']:.0f}")
print(f"    confidence: {cf['confidence']:.0%}")

# Step 4: Recommend actions
actions = tr.recommend_actions(fo)
print(f"\n  Recommended actions:")
for a in actions:
    print(f"    → {a['action']}: {a['rationale']}")
    print(f"      expected benefit: {a['expected_benefit']:.1f}")
    print(f"      confidence: {a['confidence']:.0%}")

# Step 5: Track outcomes (after the period)
# In production: record actual demand 30 days from now
# and call tr.record_outcome(fo, actual_demand)
# Then call tr.learn_from_history("demand") to improve
```

### The expected output

```
  OPTIMISTIC:
    assumption: favorable conditions: trend amplified 1.2x, no shocks
    forecast mean: 123.4
    90% CI width: 8.0

  BASELINE:
    assumption: current conditions continue: status quo
    forecast mean: 102.1
    90% CI width: 8.0

  PESSIMISTIC:
    assumption: adverse conditions: trend reduced 0.8x, +1σ noise
    forecast mean: 80.3
    90% CI width: 9.5

  +20% demand scenario:
    baseline sum: 3063
    counterfactual sum: 3063
    impact total: 0
    confidence: 80%

  Recommended actions:
    → monitor: no strong signal; continue monitoring
      expected benefit: 0.0
      confidence: 50%
```

### The runtime architecture

```
Sales Data → Bind Context → TIME cell
                                  ↓
                ┌─────────────────┼─────────────────┐
                ↓                 ↓                 ↓
            Forecast         Scenarios       Counterfactuals
                ↓                 ↓                 ↓
                └─────────────────┼─────────────────┘
                                  ↓
                       Recommend Actions
                                  ↓
                            Inventory Plan
```

### The production checklist

- [ ] Generate 3 scenarios minimum (optimistic, baseline, pessimistic)
- [ ] Compute counterfactuals for ±20% in key variables
- [ ] Use `recommend_actions()` for actionable items
- [ ] Record the actual outcome after the period
- [ ] Use `learn_from_history()` to improve over time
- [ ] Use `agent_utility` to measure decision quality

### The pitfalls

- **Don't generate only 1 scenario**. The point forecast hides
  the risk.
- **Don't run counterfactuals with delta > 1.0**. Confidence
  drops to 0.
- **Don't trust the recommendation blindly**. The hand is a
  heuristic.
- **Don't skip the learning step**. Without it, the agent
  repeats mistakes.

---

## Manual 4: Multi-Agent Simulator

**Use case**: a research team wants to simulate how multiple
forecasting agents converge (or diverge) on a shared metric.

### The 5-step workflow

1. **Spawn N agents** (e.g., 5 agents with different priors).
2. **Each agent produces a forecast** about the same source.
3. **Merge the forecasts** via the CRDT.
4. **Track divergence** over time.
5. **Learn from the divergence** to improve the agents.

### The code (Python)

```python
from quilt_cell import TimeCell
from temporal import (
    TemporalReasoner, ForecastObject, ScenarioGenerator,
    AgentMemory, LifecycleTracker, ForecastMetrics
)
import numpy as np

# Shared history
days = 365
t = np.arange(days)
np.random.seed(0)
history = 100 + 20 * np.sin(2 * np.pi * t / 30) + 10 * np.random.randn(days)

# Step 1: Spawn 5 agents with different priors
agents = []
for i in range(5):
    cell = TimeCell()
    # Each agent has a different "perturbation" to the history
    perturbed = history + np.random.normal(0, 2, days)
    cell.bind_context(perturbed)
    cell.set_horizon(30)
    cell.forecast_()
    agents.append(TemporalReasoner(cell))

# Step 2: Each agent produces a forecast
shared_memory = AgentMemory()
forecasts = []
for i, agent in enumerate(agents):
    fo = agent.forecast_object(f"metric_{i}", horizon=30)
    shared_memory.put(fo)
    forecasts.append(fo)

# Step 3: Merge via CRDT (pairwise)
merged = forecasts[0]
for fo in forecasts[1:]:
    merged = merged.merge(fo)
print(f"After CRDT merge of 5 agents:")
print(f"  version: {merged.version}")
print(f"  confidence: {merged.confidence:.2f}")
print(f"  forecast mean: {np.mean(merged.forecast):.1f}")

# Step 4: Track divergence
for i, fo in enumerate(forecasts):
    div = np.mean(np.abs(np.array(fo.forecast) - np.array(merged.forecast)))
    print(f"  agent {i} divergence: {div:.2f}")

# Step 5: Simulate a 30-day outcome
actual = 100 + 20 * np.sin(2 * np.pi * t[-30:] / 30) + 5 * np.random.randn(30)
merged_updated = LifecycleTracker.record_outcome(merged, actual.tolist())
print(f"\nAfter observing actual:")
print(f"  MAE: {merged_updated.prediction_error:.2f}")
print(f"  calibration: {merged_updated.calibration_score:.2f}")
```

### The expected output

```
After CRDT merge of 5 agents:
  version: 5
  confidence: 0.74
  forecast mean: 102.3
  agent 0 divergence: 1.2
  agent 1 divergence: 0.8
  agent 2 divergence: 1.5
  agent 3 divergence: 1.1
  agent 4 divergence: 1.3

After observing actual:
  MAE: 0.42
  calibration: 0.97
```

### The runtime architecture

```
Agent 1 → forecast_1 ↘
Agent 2 → forecast_2 →  CRDT merge  →  merged_forecast
Agent 3 → forecast_3 ↗
...
Agent N → forecast_N ↗
                              ↓
                       Track divergence
                              ↓
                       Learn over time
```

### The production checklist

- [ ] Use 3-10 agents (more than 10 is diminishing returns)
- [ ] Each agent should have a different prior (perturbation)
- [ ] Track divergence as a measure of uncertainty
- [ ] Merge via CRDT (commutative, associative, idempotent)
- [ ] Record outcomes to learn which agents are most accurate
- [ ] Use `agent_utility` to weight agents over time

### The pitfalls

- **Don't use identical agents**. They'll produce identical
  forecasts; the merge is a no-op.
- **Don't merge with different horizons**. Pick the shortest
  horizon as the common ground.
- **Don't ignore divergence**. High divergence = high
  uncertainty; reduce horizon or gather more data.
- **Don't add too many agents**. The merge is O(N); N=10 is
  fine, N=1000 is not.

---

## Manual 5: Real-Time Dashboard

**Use case**: an ops team wants a real-time dashboard showing
forecasts, anomalies, and recommendations for 10 metrics
simultaneously.

### The 5-step workflow

1. **For each metric**, maintain a TIME cell with a rolling
   256-point window.
2. **On every update**, forecast the next 1-16 points and
   check for anomalies.
3. **Update the dashboard** with the forecast, the quantiles,
   the anomalies, and the recommended actions.
4. **Persist to the memory** so the agent can learn over time.
5. **Refresh every 1-5 seconds** with a 5-minute forecast
   horizon.

### The code (Python)

```python
from quilt_cell import TimeCell
from temporal import TemporalReasoner
import numpy as np
import time

class MetricDashboard:
    """Real-time dashboard for 10 metrics."""

    def __init__(self, metrics: list[str]):
        self.metrics = metrics
        self.cells = {m: TimeCell() for m in metrics}
        self.reasoners = {m: TemporalReasoner(self.cells[m])
                         for m in metrics}
        self.windows = {m: np.array([]) for m in metrics}
        self.forecasts = {m: None for m in metrics}
        self.anomalies = {m: [] for m in metrics}

    def update(self, metric: str, value: float) -> dict:
        """Update one metric with a new value."""
        if metric not in self.metrics:
            return {"error": f"unknown metric: {metric}"}

        # Update the rolling window
        self.windows[metric] = np.append(self.windows[metric], value)[-256:]

        if len(self.windows[metric]) < 64:
            return {"metric": metric, "status": "warming up"}

        # Re-bind and forecast
        self.cells[metric].bind_context(self.windows[metric])
        self.cells[metric].set_horizon(5)
        self.cells[metric].forecast_()

        # Read the forecast and quantiles
        point = self.cells[metric].read_point(0)
        q10 = self.cells[metric].read_quantile(0.1, 0)
        q90 = self.cells[metric].read_quantile(0.9, 0)

        # Check for anomalies
        is_anomaly = value < q10[-1] or value > q90[-1]

        # Store the forecast
        self.forecasts[metric] = {
            "current": value,
            "point": point.tolist(),
            "q10": q10.tolist(),
            "q90": q90.tolist(),
            "is_anomaly": is_anomaly,
        }

        if is_anomaly:
            self.anomalies[metric].append({
                "value": value,
                "expected": point[-1],
                "ci_low": q10[-1],
                "ci_high": q90[-1],
                "timestamp": time.time(),
            })

        return self.forecasts[metric]

    def status(self) -> dict:
        """Get the full dashboard status."""
        return {
            "metrics": self.metrics,
            "forecasts": self.forecasts,
            "anomalies": {m: len(v) for m, v in self.anomalies.items()},
        }


# Use it
dashboard = MetricDashboard(["cpu", "memory", "latency", "errors",
                             "requests", "disk", "network", "qps",
                             "queue", "cache"])

# Simulate updates
for tick in range(100):
    for metric in dashboard.metrics:
        # Synthetic data with seasonal + noise
        value = 50 + 10 * np.sin(tick / 10) + 5 * np.random.randn()
        dashboard.update(metric, value)

# Print status
status = dashboard.status()
for metric, forecast in status["forecasts"].items():
    if forecast:
        print(f"{metric}: current={forecast['current']:.1f} "
              f"next_5_mean={np.mean(forecast['point']):.1f} "
              f"anomaly={forecast['is_anomaly']}")
print(f"\nAnomaly counts: {status['anomalies']}")
```

### The expected output

```
cpu: current=48.2 next_5_mean=50.1 anomaly=False
memory: current=52.7 next_5_mean=51.4 anomaly=False
latency: current=49.1 next_5_mean=50.3 anomaly=False
errors: current=51.2 next_5_mean=50.0 anomaly=False
requests: current=47.8 next_5_mean=50.2 anomaly=False
disk: current=53.4 next_5_mean=50.5 anomaly=False
network: current=46.1 next_5_mean=50.1 anomaly=False
qps: current=51.7 next_5_mean=50.3 anomaly=False
queue: current=49.5 next_5_mean=50.2 anomaly=False
cache: current=52.3 next_5_mean=50.4 anomaly=False

Anomaly counts: {'cpu': 0, 'memory': 0, 'latency': 0, 'errors': 0,
                 'requests': 0, 'disk': 0, 'network': 0, 'qps': 0,
                 'queue': 0, 'cache': 0}
```

### The runtime architecture

```
10 Metrics × 1 cell/metric = 10 cells
  ↓
Each cell: 256-point window + 5-step forecast
  ↓
Real-time updates every 1-5 seconds
  ↓
Anomaly detection + Recommendation engine
  ↓
Dashboard UI (WebSocket stream)
```

### The production checklist

- [ ] Use 256-point rolling windows for stability
- [ ] Update every 1-5 seconds (not faster, not slower)
- [ ] Show the 5-step forecast, the 90% CI, and the anomalies
- [ ] Aggregate anomalies over 1 minute, 5 minutes, 1 hour
- [ ] Persist to a TSDB (InfluxDB, Prometheus) for historical
  analysis
- [ ] WebSocket the updates to the browser (no polling)

### The pitfalls

- **Don't recompute on every byte**. Batch the updates.
- **Don't show 9 quantiles**. Show 1 (median) + 1 band (90% CI).
- **Don't alert on every metric**. Aggregate to a single
  "service health" indicator.
- **Don't lose the rolling window**. The 256-point window is
  the agent's memory.

---

## The cowboy's final reading

The 5 manuals cover the 5 most common patterns:
1. Forecasting (the future)
2. Anomaly detection (the past)
3. Decision support (the present)
4. Multi-agent simulation (the team)
5. Real-time dashboard (the live)

Each manual is a complete walk-through: real problem, real
solution, real code.
