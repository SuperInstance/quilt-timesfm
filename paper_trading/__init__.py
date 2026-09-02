"""Paper trading — forecast-driven trading on synthetic price data.

The paper trader is a small, end-to-end agent that:
  1. Streams a price series (synthetic by default; pluggable for real)
  2. Uses time.cell to forecast the next N steps
  3. Uses TemporalReasoner to recommend buy / sell / hold
  4. Executes the action on a paper portfolio
  5. Records the actual outcome
  6. Updates calibration as more history arrives

It exercises every capability of the temporal stack:
  - ForecastObject (the forecast as durable state)
  - quf:// URI (every forecast is addressable)
  - Scenarios (3 futures: optimistic / baseline / pessimistic)
  - Counterfactuals ("what if I had bought?")
  - Explainability (what the model thinks is driving the move)
  - Lifecycle (record_outcome + calibration_score)
  - Agent memory (durable store across sessions)
  - Decision support (buy / sell / hold with expected benefit)
  - Metrics (MAE, RMSE, agent utility)
  - CRDT (merge forecasts from multiple cells)
"""

from .trader import PaperTrader, Trade, Portfolio, Position
from .data import synthetic_price_stream, GeometricBrownianMotion, EXAMPLE_SHOCKS
from .feeds import CSVPriceFeed, YahooFinanceFeed, RandomWalkFeed
from .strategy import TradingDecisionSupport, TradingAction

__all__ = [
    "PaperTrader",
    "Trade",
    "Portfolio",
    "Position",
    "synthetic_price_stream",
    "GeometricBrownianMotion",
    "EXAMPLE_SHOCKS",
    "CSVPriceFeed",
    "YahooFinanceFeed",
    "RandomWalkFeed",
    "TradingDecisionSupport",
    "TradingAction",
]
