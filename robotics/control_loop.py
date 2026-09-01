"""The control loop — the robotics equivalent of PaperTrader.run().

The loop:
  1. Read the next sensor reading
  2. Append to SensorCell
  3. Forecast the next state (FORECAST)
  4. Compare the forecast to the target trajectory
  5. If we're on track, hold the action; if we're off track, plan
     a corrective action
  6. Send the command to the actuator
  7. Record the actual next reading
  8. Update calibration

The cell shape is the same as paper trading; the only difference
is the data type (joint angles vs prices).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple
import numpy as np

from .sensor_cell import SensorCell
from .action_cell import ActionCell


class RobotAction(str, Enum):
    """What the controller decided to do this tick."""
    HOLD = "hold"                  # on track
    CORRECT = "correct"            # adjust toward target
    STOP = "stop"                  # abort (large error, near singularity)
    GATHER_DATA = "gather_data"    # calibration poor, don't move


@dataclass
class RobotState:
    """A snapshot of the controller state at one tick."""
    step: int
    timestamp_ms: int
    sensor_reading: np.ndarray
    forecast_mean: Optional[np.ndarray]
    target: np.ndarray
    action: RobotAction
    command: Optional[np.ndarray]
    actual_next: Optional[np.ndarray] = None
    error: Optional[float] = None
    rationale: str = ""


class ControlLoop:
    """Tie a SensorCell and an ActionCell together into a control loop.

    Parameters
    ----------
    sensor_cell : SensorCell
    action_cell : ActionCell
    n_channels : int
        How many sensor channels the controller reads. Must match
        sensor_cell.n_channels.
    n_actuators : int
        How many actuators. Must match action_cell.n_actuators.
    target : np.ndarray
        The goal state (e.g. end-effector target position). Used to
        generate a target trajectory.
    error_threshold : float
        If the absolute error between forecast and target exceeds
        this, the controller issues a CORRECT.
    stop_threshold : float
        If the error exceeds this, the controller STOPS (avoid
        singularity / collision).
    """

    def __init__(
        self,
        sensor_cell: SensorCell,
        action_cell: ActionCell,
        n_channels: int,
        n_actuators: int,
        target: np.ndarray,
        error_threshold: float = 0.05,
        stop_threshold: float = 0.20,
    ):
        if sensor_cell.n_channels != n_channels:
            raise ValueError("sensor_cell channel count mismatch")
        if action_cell.n_actuators != n_actuators:
            raise ValueError("action_cell actuator count mismatch")
        self.sensor = sensor_cell
        self.action = action_cell
        self.target = np.asarray(target, dtype=np.float64)
        self.error_threshold = error_threshold
        self.stop_threshold = stop_threshold
        self._history: List[RobotState] = []
        self._calibration = 1.0

    def step(self, reading: np.ndarray) -> RobotState:
        """Process one sensor reading and decide the next command."""
        ts = int(np.datetime64('now').view('i8') // 1_000_000) if hasattr(np, 'datetime64') else 0
        # 1. Append to sensor cell
        self.sensor.append(reading)
        # 2. Forecast
        self.sensor.forecast_()
        forecast_mean = self.sensor.read_point(0) if self.sensor.context_len >= 2 else None
        # 3. Compute the *actual* distance to the target. The forecast
        # is a forward-looking estimate, but for control we need to
        # react to where the arm *is* now, not where it will be.
        current_err = float(np.linalg.norm(reading - self.target))
        # The forecast error: how far the forecast thinks we'll be
        # from where we actually are.
        if forecast_mean is not None and len(forecast_mean) > 0:
            forecast_err = float(np.linalg.norm(forecast_mean[0] - reading))
        else:
            forecast_err = 0.0
        # The control decision is based on the *current* error, not
        # the forecast error. The forecast is used to plan the
        # corrective action, not to decide whether to act.
        err = current_err
        # 4. Decide
        if err > self.stop_threshold:
            # Trully catastrophic (e.g. IK failure, unreachable target).
            # Hold position and skip the next action.
            action = RobotAction.STOP
            command = reading  # hold position
            rationale = f"error {err:.3f} > stop threshold {self.stop_threshold}; holding position"
        elif err > self.error_threshold:
            action = RobotAction.CORRECT
            # Generate a target trajectory toward the goal
            current = reading if self.sensor.context_len == 1 else self.sensor.context[-1]
            # Smoothly approach the target in H steps
            traj = np.linspace(current, self.target, self.action.horizon + 1)[1:]
            self.action.bind_context(traj)
            self.action.forecast_()
            command = self.action.next_command()
            rationale = f"error {err:.3f} > threshold; planning correction"
        else:
            action = RobotAction.HOLD
            command = reading  # hold current position
            rationale = f"error {err:.3f} within tolerance; holding"
        # Build the state record
        state = RobotState(
            step=self.sensor.context_len - 1,
            timestamp_ms=ts,
            sensor_reading=reading.copy(),
            forecast_mean=forecast_mean.copy() if forecast_mean is not None else None,
            target=self.target.copy(),
            action=action,
            command=command.copy() if command is not None else None,
            rationale=rationale,
        )
        self._history.append(state)
        return state

    def run(self, readings) -> List[RobotState]:
        """Run the loop over an iterator of sensor readings."""
        for r in readings:
            self.step(r)
        return self._history

    @property
    def history(self) -> List[RobotState]:
        return self._history
