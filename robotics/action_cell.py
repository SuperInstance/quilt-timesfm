"""ActionCell — a cell whose state is a target trajectory (joint positions, etc.).

The cell shape is the same as SensorCell, but the semantics are
inverted: a SensorCell forecasts a future state; an ActionCell
stores a desired future trajectory and the sensor readings verify
whether the trajectory is being followed.

The 5 operations are: BIND_CONTEXT (set the target trajectory),
SET_HORIZON, FORECAST (plan the next action by extrapolating the
trajectory), READ_POINT (read the planned next action),
READ_QUANTILE (read the action distribution under uncertainty).
"""
from __future__ import annotations
import numpy as np
from typing import Optional, List


class ActionCell:
    """A cell whose context is a target trajectory of length T for V actuators.

    The forecast is the "extended" trajectory — what we plan to do
    for the next H timesteps, based on the target. The agent uses
    this to decide what command to send to the actuators right now.

    Parameters
    ----------
    actuator_names : list of str
        Names of the actuators (e.g. ["shoulder", "elbow", "gripper"]).
    history_len : int
        How many past target points to keep. Default 32.
    horizon : int
        How many future action steps to plan. Default 5.
    """

    def __init__(
        self,
        actuator_names: List[str],
        history_len: int = 32,
        horizon: int = 5,
    ):
        if not actuator_names:
            raise ValueError("actuator_names must be non-empty")
        self.actuator_names = list(actuator_names)
        self.n_actuators = len(self.actuator_names)
        self.history_len = history_len
        self.horizon = horizon
        self._target: List[np.ndarray] = []
        self._plan: Optional[np.ndarray] = None

    @property
    def context(self) -> Optional[np.ndarray]:
        if not self._target:
            return None
        return np.array(self._target[-self.history_len:])

    @property
    def context_len(self) -> int:
        return len(self._target)

    def set_target(self, target: np.ndarray) -> int:
        """Set a single target point for all actuators (TICK)."""
        if target.shape != (self.n_actuators,):
            raise ValueError(
                f"target must be shape ({self.n_actuators},), got {target.shape}"
            )
        self._target.append(target.astype(np.float64))
        return 0

    def bind_context(self, context: np.ndarray) -> int:
        """Set the entire target trajectory at once (BIND_CONTEXT)."""
        if context.ndim != 2 or context.shape[1] != self.n_actuators:
            raise ValueError(
                f"context must be [T, {self.n_actuators}], got {context.shape}"
            )
        self._target = [row for row in context]
        return 0

    def set_horizon(self, horizon: int) -> int:
        if horizon <= 0:
            return -1
        self.horizon = horizon
        return 0

    def forecast_(self) -> int:
        """Plan the next H actions (FORECAST).

        For an ActionCell, the "forecast" is the planned future
        trajectory. The simplest plan is to extrapolate the target
        trajectory linearly. A real implementation would use an
        MPC (model-predictive control) solver or a learned policy.
        """
        if self.context_len < 2 or self.horizon == 0:
            return -1
        ctx = self.context
        H = self.horizon
        V = self.n_actuators
        # Linear extrapolation
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
        t_h = np.arange(H, dtype=np.float64)[:, None]
        self._plan = last[None, :] + drift[None, :] * t_h
        return 0

    def read_point(self, actuator: int = 0) -> np.ndarray:
        """Read the planned trajectory for one actuator (READ_POINT)."""
        if self._plan is None or actuator >= self.n_actuators:
            return np.zeros(0)
        return self._plan[:, actuator].copy()

    def next_command(self) -> Optional[np.ndarray]:
        """Read the next action to send to the actuators.

        This is a sugar method: returns the first step of the plan
        as a 1-D array, or None if no plan has been made.
        """
        if self._plan is None or len(self._plan) == 0:
            return None
        return self._plan[0].copy()
