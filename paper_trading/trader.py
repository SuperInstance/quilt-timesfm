"""The PaperTrader — the agent that ties the cell, the strategy, and the portfolio together.

The PaperTrader runs a tick loop:
  1. Read the next price from the stream
  2. Append it to the rolling history
  3. Once we have enough history, bind the cell, forecast the next N steps
  4. Run the strategy on the forecast, get a TradingDecision
  5. Execute the decision on the portfolio
  6. After the horizon elapses, record the actual outcome against the forecast
  7. Update the calibration

Everything is logged. The full trade log is the audit trail.
The forecast + decision + outcome form a single record with a quf:// URI.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Iterator, Optional, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from quilt_cell import TimeCell
    from temporal import TemporalReasoner
    from .strategy import TradingDecision


@dataclass
class Trade:
    """A single recorded trade — the input, the forecast, the decision, and the outcome.

    The record is a CRDT-friendly dict (no nested mutable state),
    suitable for replaying or merging across agents.
    """
    step: int                       # the step index when the trade was made
    timestamp_ms: int               # wall-clock time, ms since epoch
    current_price: float            # the price at decision time
    forecast_uri: str               # the quf:// URI of the forecast
    forecast_mean: float            # the mean of the point forecast
    forecast_horizon: int           # how many steps the forecast covered
    forecast_confidence: float      # the model's self-reported confidence
    forecast_quantile_width: float  # the width of the 90% CI (uncertainty)
    action: str                     # buy / sell / hold / half_size / gather_data
    decision_confidence: float      # the strategy's confidence in the decision
    expected_benefit: float         # the strategy's predicted P&L per share
    rationale: str                  # human-readable explanation
    cost_basis: float = 0.0         # the cost basis at the time of the trade
    # Outcome (filled in when the horizon elapses)
    actual_price: Optional[float] = None
    actual_return: Optional[float] = None
    prediction_error: Optional[float] = None
    realized_pnl: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Position:
    """A single position in a single asset."""
    asset: str
    shares: float = 0.0
    cost_basis: float = 0.0         # average price paid per share

    def market_value(self, current_price: float) -> float:
        return self.shares * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.cost_basis) * self.shares


@dataclass
class Portfolio:
    """Cash + positions. P&L is computed against the initial cash balance."""
    initial_cash: float = 100_000.0
    cash: float = 100_000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    trade_log: List[Trade] = field(default_factory=list)

    def total_value(self, prices: Dict[str, float]) -> float:
        v = self.cash
        for asset, pos in self.positions.items():
            v += pos.market_value(prices.get(asset, 0.0))
        return v

    def total_pnl(self, prices: Dict[str, float]) -> float:
        return self.total_value(prices) - self.initial_cash

    def execute(
        self,
        asset: str,
        action: str,
        price: float,
        max_trade_pct: float = 0.1,
        transaction_cost_bps: float = 5.0,  # 5 bps = 0.05% per trade (typical retail)
    ) -> Tuple[float, float]:
        """Execute an action on `asset` at `price`. Returns (shares_traded, cash_delta).

        `max_trade_pct` caps the size of a single trade as a fraction
        of the portfolio. This is the "don't bet the farm" rule.

        `transaction_cost_bps` is the per-side transaction cost in
        basis points. 5 bps is typical for retail; institutional
        is 1-2 bps. Applied to both buys and sells.
        """
        pos = self.positions.setdefault(asset, Position(asset=asset))
        portfolio_value = self.total_value({asset: price})
        max_trade_value = portfolio_value * max_trade_pct
        cost_frac = transaction_cost_bps / 10000.0
        if action == "buy":
            # Use up to half of cash for the buy
            trade_value = min(self.cash * 0.5, max_trade_value)
            if trade_value <= 0:
                return 0.0, 0.0
            cost = trade_value * cost_frac
            net_cash = trade_value + cost
            if net_cash > self.cash:
                trade_value = self.cash / (1 + cost_frac)
                cost = trade_value * cost_frac
                net_cash = trade_value + cost
            shares = trade_value / price
            self.cash -= net_cash
            # Update cost basis
            new_cost = pos.cost_basis * pos.shares + price * shares
            new_shares = pos.shares + shares
            pos.cost_basis = new_cost / new_shares if new_shares > 0 else 0.0
            pos.shares = new_shares
            return shares, -net_cash
        if action == "sell":
            # Sell up to half of the position
            shares_to_sell = min(pos.shares * 0.5, max_trade_value / price)
            if shares_to_sell <= 0:
                return 0.0, 0.0
            proceeds = shares_to_sell * price
            cost = proceeds * cost_frac
            net_proceeds = proceeds - cost
            self.cash += net_proceeds
            pos.shares -= shares_to_sell
            return shares_to_sell, net_proceeds
        if action == "half_size":
            # Treat as a half-sized buy
            return self.execute(asset, "buy", price, max_trade_pct=max_trade_pct / 2)
        if action in ("hold", "gather_data"):
            return 0.0, 0.0
        raise ValueError(f"unknown action: {action!r}")


class PaperTrader:
    """The end-to-end paper-trading agent.

    Parameters
    ----------
    cell : TimeCell
        The forecast cell.
    reasoner : TemporalReasoner
        The temporal-reasoning wrapper (forecast + scenarios + lifecycle).
    strategy : TradingDecisionSupport
        The trading-specific recommender.
    asset : str
        Which asset the trader trades (e.g. "AAPL"). Default "ASSET".
    history_len : int
        How many past prices to bind as context. Default 128.
    horizon : int
        How many steps the forecast should cover. Default 5.
    min_history : int
        How many history points are required before the first trade.
    max_position_pct : float
        Cap on the size of any single trade, as a fraction of
        the portfolio. Default 0.1 (10%).
    """

    def __init__(
        self,
        cell: "TimeCell",
        reasoner: "TemporalReasoner",
        strategy: "TradingDecisionSupport",
        asset: str = "ASSET",
        history_len: int = 128,
        horizon: int = 5,
        min_history: int = 64,
        max_position_pct: float = 0.1,
        use_trend_synthetic: bool = True,
    ):
        self.cell = cell
        self.reasoner = reasoner
        self.strategy = strategy
        self.asset = asset
        self.history_len = history_len
        self.horizon = horizon
        self.min_history = min_history
        self.max_position_pct = max_position_pct
        # If True, use forecast_trend() instead of forecast_() in synthetic
        # mode. The trend forecast is a continuation of the input series,
        # which is what a real TimesFM 3.0 would do. Required for
        # paper-trading to have any useful signal.
        self.use_trend_synthetic = use_trend_synthetic
        self.portfolio = Portfolio()
        self.history: List[float] = []
        self._pending_forecast: Optional[Any] = None
        self._pending_horizon_left: int = 0

    @property
    def total_pnl(self) -> float:
        return self.portfolio.total_pnl({self.asset: self.history[-1] if self.history else 0.0})

    @property
    def cash(self) -> float:
        return self.portfolio.cash

    @property
    def shares(self) -> float:
        return self.portfolio.positions.get(self.asset, Position(self.asset)).shares

    def _make_forecast(self) -> Any:
        """Build a ForecastObject from the current history."""
        if len(self.history) < self.min_history:
            return None
        ctx = np.array(self.history[-self.history_len:]).reshape(-1, 1)
        self.cell.bind_context(ctx)
        # set_horizon must be called BEFORE forecast_object, so the
        # reasoner can read the horizon. forecast_object also calls
        # set_horizon internally, but doing it here makes the cell
        # state consistent if a caller inspects the cell.
        self.cell.set_horizon(self.horizon)
        # Use trend-aware synthetic if enabled, otherwise the cell
        # uses the real model (or _forecast_synthetic if forced).
        method = "trend" if self.use_trend_synthetic else "default"
        fo = self.reasoner.forecast_object(self.asset, horizon=self.horizon, method=method)
        return fo

    def step(self, price: float) -> Dict[str, Any]:
        """Process one price tick. Returns a step report.

        The report is a dict with:
          - 'step': the step index
          - 'forecast': the forecast (or None)
          - 'decision': the TradingDecision (or None)
          - 'trade': the executed Trade (or None)
          - 'price': the price

        Defensive: if price is not finite or non-positive, it is
        replaced with the last seen valid price (or 1.0 if none).
        The cell still gets a value; the strategy sees a flat
        line and produces a "hold" decision.
        """
        import math
        if not math.isfinite(price) or price <= 0:
            price = self.history[-1] if self.history else 1.0
        self.history.append(price)
        report = {"step": len(self.history) - 1, "price": price, "forecast": None,
                  "decision": None, "trade": None}
        # Settle any pending forecast whose horizon just elapsed
        if self._pending_forecast is not None and self._pending_horizon_left <= 1:
            trade = self.portfolio.trade_log[-1]  # the trade that opened this forecast
            trade.actual_price = price
            trade.actual_return = (price - trade.current_price) / trade.current_price
            trade.prediction_error = abs(
                trade.forecast_mean - price
            ) / max(abs(trade.current_price), 1e-6)
            # Realized P&L = (sell_price - cost_basis) * shares, or 0 if we held
            pos = self.portfolio.positions.get(self.asset)
            if pos and pos.shares > 0:
                trade.realized_pnl = (price - trade.cost_basis) * pos.shares
            else:
                trade.realized_pnl = 0.0
            # Update the forecast object's lifecycle
            self.reasoner.record_outcome(
                self._pending_forecast, [price] * self.horizon
            )
            self._pending_forecast = None
            self._pending_horizon_left = 0
            report["settled_trade"] = trade
        elif self._pending_forecast is not None:
            self._pending_horizon_left -= 1
        # Make a new forecast + decision if we have enough history
        if len(self.history) >= self.min_history and self._pending_forecast is None:
            fo = self._make_forecast()
            if fo is not None:
                # We need to set the cell's horizon for the reasoner too
                self.cell.set_horizon(self.horizon)
                decision = self.strategy.decide(fo, current_price=price)
                # Execute
                shares_traded, cash_delta = self.portfolio.execute(
                    self.asset, decision.action, price, self.max_position_pct
                )
                # Get the post-trade position to capture the new cost basis
                post_pos = self.portfolio.positions.get(self.asset)
                trade = Trade(
                    step=len(self.history) - 1,
                    timestamp_ms=int(time.time() * 1000),
                    current_price=price,
                    forecast_uri=fo.uri,
                    forecast_mean=float(np.mean(fo.forecast)),
                    forecast_horizon=fo.horizon,
                    forecast_confidence=fo.confidence,
                    forecast_quantile_width=float(
                        np.mean(np.array(fo.uncertainty[8]) - np.array(fo.uncertainty[0]))
                    ) if fo.uncertainty else 0.0,
                    action=decision.action.value if hasattr(decision.action, "value") else str(decision.action),
                    decision_confidence=decision.confidence,
                    expected_benefit=decision.expected_benefit,
                    rationale=decision.rationale,
                    cost_basis=post_pos.cost_basis if post_pos else 0.0,
                )
                self.portfolio.trade_log.append(trade)
                self._pending_forecast = fo
                self._pending_horizon_left = self.horizon
                report["forecast"] = fo
                report["decision"] = decision
                report["trade"] = trade
        return report

    def run(
        self,
        price_stream: Iterator[Tuple[int, float]],
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Run the trader over a price stream. Returns a summary."""
        n_trades = 0
        n_actions = {"buy": 0, "sell": 0, "hold": 0, "half_size": 0, "gather_data": 0}
        initial_value = self.portfolio.total_value({self.asset: 0.0})
        # Count only trades that change the position (buy, sell, half_size).
        # hold and gather_data are decisions, not trades.
        TRADING_ACTIONS = {"buy", "sell", "half_size"}
        for t, price in price_stream:
            report = self.step(price)
            if report["trade"] is not None:
                action = report["trade"].action
                n_actions[action] = n_actions.get(action, 0) + 1
                if action in TRADING_ACTIONS:
                    n_trades += 1
                if verbose:
                    print(
                        f"t={t:4d} p={price:7.2f} "
                        f"action={action:11s} "
                        f"confidence={report['trade'].decision_confidence:.2f} "
                        f"rationale={report['trade'].rationale}"
                    )
        final_value = self.portfolio.total_value({self.asset: self.history[-1]})
        return {
            "n_trades": n_trades,
            "n_actions": n_actions,
            "initial_value": initial_value,
            "final_value": final_value,
            "total_pnl": final_value - initial_value,
            "pnl_pct": (final_value - initial_value) / initial_value if initial_value else 0.0,
            "trade_log": [t.to_dict() for t in self.portfolio.trade_log],
        }
