"""Trading decision support — maps forecasts to buy / sell / hold.

The base DecisionSupport in temporal.py is generic; it recommends
"increase capacity" or "reduce cost". For paper trading we need
a domain-specific recommender that:

  - Translates "spike in price" into BUY
  - Translates "dip in price" into SELL
  - Translates "wide uncertainty" into HOLD (or HALF_SIZE)
  - Translates "poor calibration" into GATHER_DATA (skip trade)

The logic is the same shape as DecisionSupport — we keep the
heuristics but rewrite the action vocabulary and the rationale.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from temporal import ForecastObject, AgentMemory


class TradingAction(str, Enum):
    """The 5 actions a paper trader can take.

    String-valued so they serialize cleanly to JSON / quf:// metadata.
    """
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    HALF_SIZE = "half_size"      # uncertain, halve the position
    GATHER_DATA = "gather_data"  # calibration is poor, skip this trade


@dataclass
class TradingDecision:
    """The output of a single trading decision."""
    action: TradingAction
    confidence: float
    expected_benefit: float          # expected P&L per share, in price units
    rationale: str
    horizon: int                     # how many steps the decision is for
    forecast_uri: str                # the quf:// URI of the forecast that drove this


class TradingDecisionSupport:
    """A trading-specific recommender.

    Given a forecast of the next N prices, decide whether to buy,
    sell, hold, or halve position. The decision is made on the
    expected return over the horizon, the uncertainty of that
    return, and the historical calibration on this source.
    """

    def __init__(
        self,
        memory: "AgentMemory",
        threshold_return: float = 0.005,   # +0.5% expected return to BUY
        threshold_uncertainty: float = 0.4,  # 40% relative CI to HALF_SIZE
    ):
        self.memory = memory
        self.threshold_return = threshold_return
        self.threshold_uncertainty = threshold_uncertainty

    def decide(self, forecast: "ForecastObject", current_price: float) -> TradingDecision:
        """Make a trading decision based on the forecast.

        Parameters
        ----------
        forecast : ForecastObject
            The forecast of the next N steps. The first element of
            forecast.forecast is the immediate next-step prediction;
            the rest is the multi-step horizon.
        current_price : float
            The price at decision time. Used to compute expected
            return as a fraction.

        Returns
        -------
        TradingDecision
        """
        point = np.array(forecast.forecast)
        last_pred = float(point[-1])
        # Expected return: (last_pred - current_price) / current_price
        expected_return = (last_pred - current_price) / current_price

        # Uncertainty: width of the 90% CI relative to the mean
        if forecast.uncertainty:
            q90 = np.array(forecast.uncertainty[8])
            q10 = np.array(forecast.uncertainty[0])
            ci_width = float(np.mean(q90 - q10))
            relative_uncertainty = ci_width / max(abs(current_price), 1e-6)
        else:
            relative_uncertainty = 0.0

        # Calibration check
        learn = self.memory.learn_from_history(forecast.source)
        calibration = learn.get("mean_calibration")
        recent_error = learn.get("mean_error")
        # Convert error to relative terms (MAE / current price).
        # An MAE of 2 on a $100 asset is 2% — fine. An MAE of 2 on a
        # $5 asset is 40% — terrible. The threshold is on relative error.
        if recent_error is not None:
            relative_error = recent_error / max(abs(current_price), 1e-6)
        else:
            relative_error = None

        # 1. Poor calibration → GATHER_DATA
        if calibration is not None and relative_error is not None:
            if relative_error > 0.03 or calibration < 0.5:
                return TradingDecision(
                    action=TradingAction.GATHER_DATA,
                    confidence=0.6,
                    expected_benefit=0.0,
                    horizon=forecast.horizon,
                    forecast_uri=forecast.uri,
                    rationale=(
                        f"calibration {calibration:.2f} and relative error "
                        f"{relative_error:.2%} suggest the model is unreliable; "
                        f"skip the trade and gather more data"
                    ),
                )

        # 2. High uncertainty → HALF_SIZE
        if relative_uncertainty > self.threshold_uncertainty:
            return TradingDecision(
                action=TradingAction.HALF_SIZE,
                confidence=0.4 * forecast.confidence,
                expected_benefit=expected_return * current_price / 2,
                horizon=forecast.horizon,
                forecast_uri=forecast.uri,
                rationale=(
                    f"90% CI width = {relative_uncertainty:.1%} of price; "
                    f"halving the position to limit downside"
                ),
            )

        # 3. Strong positive signal → BUY
        if expected_return > self.threshold_return:
            return TradingDecision(
                action=TradingAction.BUY,
                confidence=min(1.0, forecast.confidence * (1 + expected_return * 5)),
                expected_benefit=expected_return * current_price,
                horizon=forecast.horizon,
                forecast_uri=forecast.uri,
                rationale=(
                    f"forecast says price will rise to {last_pred:.2f} "
                    f"({expected_return:+.2%}); confidence {forecast.confidence:.2f}"
                ),
            )

        # 4. Strong negative signal → SELL
        if expected_return < -self.threshold_return:
            return TradingDecision(
                action=TradingAction.SELL,
                confidence=min(1.0, forecast.confidence * (1 + abs(expected_return) * 5)),
                expected_benefit=abs(expected_return) * current_price,
                horizon=forecast.horizon,
                forecast_uri=forecast.uri,
                rationale=(
                    f"forecast says price will fall to {last_pred:.2f} "
                    f"({expected_return:+.2%}); confidence {forecast.confidence:.2f}"
                ),
            )

        # 5. No signal → HOLD
        return TradingDecision(
            action=TradingAction.HOLD,
            confidence=0.5,
            expected_benefit=0.0,
            horizon=forecast.horizon,
            forecast_uri=forecast.uri,
            rationale=(
                f"expected return {expected_return:+.2%} within ±{self.threshold_return:.1%}; "
                f"no strong signal; hold the position"
            ),
        )
