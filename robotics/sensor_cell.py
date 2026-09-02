"""SensorCell — a cell whose state is a multivariate sensor stream.

The shape is the same as TimeCell (context [T, V], forecast [H, V],
quantiles [9, H, V]) but the semantics are different: V is the
number of sensor channels, not the number of variates in a time
series. The 5 operations are the same.

The "future" being predicted is the next state of the robot: joint
angles in 0.1s, 0.2s, ..., 0.5s. The agent can use this prediction
to plan an action before the actual sensor data arrives.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SensorReading:
    """A single multivariate sensor reading at one timestep.

    channels is a list of (name, value) pairs. The order is fixed
    for the lifetime of the cell.
    """
    timestamp_ms: int
    channels: List[tuple]


class SensorCell:
    """A cell whose context is a rolling window of sensor readings.

    Parameters
    ----------
    channel_names : list of str
        Names of the sensor channels. The order is fixed.
    history_len : int
        How many past readings to keep as context. Default 64.
    horizon : int
        How many future steps to forecast. Default 5.
    """

    def __init__(
        self,
        channel_names: List[str],
        history_len: int = 64,
        horizon: int = 5,
    ):
        if not channel_names:
            raise ValueError("channel_names must be non-empty")
        self.channel_names = list(channel_names)
        self.n_channels = len(self.channel_names)
        self.history_len = history_len
        self.horizon = horizon
        # Rolling buffer: shape [history_len, n_channels]
        self._buffer: List[np.ndarray] = []
        self._next_id: int = 0
        self._forecast: Optional[np.ndarray] = None
        self._quantiles: Optional[np.ndarray] = None

    @property
    def context(self) -> Optional[np.ndarray]:
        if not self._buffer:
            return None
        return np.array(self._buffer[-self.history_len:])

    @property
    def context_len(self) -> int:
        return len(self._buffer)

    def bind_context(self, context: np.ndarray) -> int:
        """Set the entire context at once (BIND_CONTEXT)."""
        if context.ndim != 2 or context.shape[1] != self.n_channels:
            raise ValueError(
                f"context must be [T, {self.n_channels}], got {context.shape}"
            )
        self._buffer = [row for row in context]
        return 0

    def set_horizon(self, horizon: int) -> int:
        """Set the forecast horizon (BIND_COVARIATE)."""
        if horizon <= 0:
            return -1
        self.horizon = horizon
        return 0

    def append(self, reading: np.ndarray) -> int:
        """Append a single sensor reading (TICK)."""
        if reading.shape != (self.n_channels,):
            raise ValueError(
                f"reading must be shape ({self.n_channels},), got {reading.shape}"
            )
        self._buffer.append(reading.astype(np.float64))
        # Cap the buffer
        if len(self._buffer) > self.history_len * 2:
            self._buffer = self._buffer[-self.history_len:]
        return 0

    def forecast_(self) -> int:
        """Forecast the next `horizon` states (FORECAST).

        Uses a simple linear extrapolation of the last 8 readings
        per channel, plus FNV-1a-seeded noise for the quantiles.

        This is the robotics equivalent of the time.cell's
        trend-aware synthetic. A real implementation would call
        a JEPA-style latent dynamics model.
        """
        if self.context_len < 2 or self.horizon == 0:
            return -1
        ctx = self.context
        H = self.horizon
        V = self.n_channels
        # Estimate per-channel drift from the last 8 readings
        N = min(8, self.context_len)
        recent = ctx[-N:]
        x = np.arange(N, dtype=np.float64)
        x_mean = (N - 1) / 2.0
        y_mean = recent.mean(axis=0)
        num = (x[:, None] * (recent - y_mean[None, :])).sum(axis=0)
        den = ((x - x_mean) ** 2).sum()
        if den == 0:
            drift = np.zeros(V)
        else:
            drift = num / den
        last = recent[-1]
        # Per-channel step std
        step_std = (recent[1:] - recent[:-1]).std(axis=0) + 1e-6
        # FNV-1a-seeded noise per (channel, t)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            h0 = int(ctx.sum() * 1e6) & 0xFFFFFFFFFFFFFFFF
            h = h0
            noise = np.zeros((H, V))
            for v in range(V):
                for t in range(H):
                    h = (h * 0x100000001b3) ^ (v * 0x9e3779b97f4a7c15)
                    h = (h * 0x100000001b3) ^ (t * 0x9e3779b97f4a7c15)
                    h = h & 0xFFFFFFFF
                    if h >= (1 << 31):
                        h -= (1 << 32)
                    noise[t, v] = h / float(1 << 30)
        # Build forecast [H, V] = last + drift*t + step_std*noise
        t_h = np.arange(H, dtype=np.float64)[:, None]
        self._forecast = last[None, :] + drift[None, :] * t_h + step_std[None, :] * noise
        # 9 quantiles: offset by ±0.5*step_std per quantile
        q_offsets = (np.arange(9) - 4) * 0.5
        self._quantiles = self._forecast[None, :, :] + (step_std[None, None, :] * q_offsets[:, None, None])
        return 0

    def read_point(self, channel: int = 0) -> np.ndarray:
        """Read the point forecast for a channel (READ_POINT)."""
        if self._forecast is None or channel >= self.n_channels:
            return np.zeros(0)
        return self._forecast[:, channel].copy()

    def read_full_forecast(self) -> np.ndarray:
        """Read the full forecast tensor [H, V] for all channels.

        Unlike read_point(channel), this returns the entire
        forecast, not a single channel. Useful for controllers
        that need all the state (e.g. q and q_dot together).
        Returns an empty array if no forecast has been made.
        """
        if self._forecast is None:
            return np.zeros((0, self.n_channels))
        return self._forecast.copy()

    def read_quantile(self, q: float, channel: int = 0) -> np.ndarray:
        """Read a quantile forecast (READ_QUANTILE)."""
        if self._quantiles is None or channel >= self.n_channels:
            return np.zeros(0)
        qi = int(q * 10.0 - 0.5)
        qi = max(0, min(8, qi))
        return self._quantiles[qi, :, channel].copy()

    def snapshot(self) -> dict:
        """A JSON-serializable snapshot of the cell state."""
        return {
            "channel_names": self.channel_names,
            "context_len": self.context_len,
            "horizon": self.horizon,
            "context": self.context.tolist() if self.context is not None else None,
            "forecast": self._forecast.tolist() if self._forecast is not None else None,
        }
