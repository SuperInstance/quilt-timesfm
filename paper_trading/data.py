"""Synthetic and real price data sources for the paper trader.

The default is a Geometric Brownian Motion with configurable drift
and volatility. Real price data can be plugged in by passing an
iterator of (timestamp, price) tuples to PaperTrader.run().

Why GBM:
- It's the canonical model for an asset price in continuous time
- The log-returns are normally distributed, which matches what
  the time.cell's quantile heads are trained on
- A "spike + drift" overlay lets the agent see both predictable
  trends and unpredictable shocks
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple


@dataclass
class GeometricBrownianMotion:
    """dS/S = mu*dt + sigma*dW — a Brownian asset price.

    Parameters
    ----------
    S0 : float
        Initial price. Default 100.
    mu : float
        Annualized drift. Default 0.08 (8% per year).
    sigma : float
        Annualized volatility. Default 0.20 (20% per year).
    dt : float
        Time step in years. Default 1/252 (one trading day).
    seed : int
        RNG seed. Default 42.
    """

    S0: float = 100.0
    mu: float = 0.08
    sigma: float = 0.20
    dt: float = 1.0 / 252.0
    seed: int = 42

    def stream(
        self,
        n_steps: int = 1000,
        shocks: Optional[list] = None,
    ) -> Iterator[Tuple[int, float]]:
        """Yield (step_index, price) for `n_steps` steps.

        Parameters
        ----------
        n_steps : int
            Number of price points to generate.
        shocks : list of (step_index, magnitude) or None
            Optional list of exogenous shocks. Each shock adds a
            multiplicative jump to the price at the given step.
            Useful for testing the agent's response to events.
        """
        rng = np.random.default_rng(self.seed)
        shock_map = dict(shocks or [])
        price = self.S0
        for t in range(n_steps):
            if t in shock_map:
                price *= (1.0 + shock_map[t])
            # Standard GBM step: S_{t+1} = S_t * exp((mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
            z = rng.standard_normal()
            log_return = (self.mu - 0.5 * self.sigma ** 2) * self.dt + self.sigma * np.sqrt(self.dt) * z
            price *= float(np.exp(log_return))
            yield (t, price)


def synthetic_price_stream(
    n_steps: int = 1000,
    seed: int = 42,
    drift: float = 0.08,
    vol: float = 0.20,
    shocks: Optional[list] = None,
) -> Iterator[Tuple[int, float]]:
    """A convenience wrapper for GeometricBrownianMotion.stream().

    Example
    -------
    >>> stream = synthetic_price_stream(n_steps=200, seed=0)
    >>> for t, price in stream:
    ...     print(t, price)
    """
    gbm = GeometricBrownianMotion(seed=seed, mu=drift, sigma=vol)
    return gbm.stream(n_steps=n_steps, shocks=shocks)


# A few real-feel shock patterns for testing.
# These simulate news events, earnings surprises, etc.
EXAMPLE_SHOCKS = {
    "earnings_beat": [(50, +0.10), (51, -0.02)],     # +10% on day 50, partial give-back
    "fed_hike": [(100, -0.05), (101, -0.03)],         # -5% on day 100
    "product_launch": [(75, +0.15)],                 # +15% on day 75
    "volatility_spike": [(t, 0.0) for t in range(20)],  # No jump, just higher vol
}
