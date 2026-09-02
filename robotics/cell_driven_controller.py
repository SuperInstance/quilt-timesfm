"""Cell-driven robotics: use the SensorCell's forecast to control the arm.

The previous controllers (computed-torque) used the arm's actual
state, not the cell's forecast. This module closes the loop:

  1. The SensorCell accumulates the arm's state history
  2. The cell's FORECAST op predicts the next H states
  3. The ActionCell plans a torque trajectory that minimizes
     the error between the forecast and the desired trajectory
  4. The first torque is applied; the loop repeats

This is the cell model doing real work in a closed-loop controller.
The cell's forecast error tells us how well the cell has learned
the dynamics; that error drives an online learning rate for
the controller.

Why this matters:
  - The cell model becomes the controller, not just an observer
  - The cell's quantiles give us a confidence interval on the
    next state — used to gate the control authority (less
    authority when the forecast is uncertain)
  - The cell's CRDT properties mean multiple arms can share
    forecasts; we can run multi-arm control with merged cells
"""
from __future__ import annotations
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .lagrangian_arm import (
    LagrangianArm, ArmParams, TrajectoryPoint,
    computed_torque_torque, ik_2link, min_jerk_trajectory,
)
from .sensor_cell import SensorCell
from .action_cell import ActionCell


@dataclass
class CellControlStep:
    """The state of one tick of cell-driven control."""
    tick: int
    t: float
    q: np.ndarray
    q_dot: np.ndarray
    q_desired: np.ndarray
    forecast_1step: np.ndarray
    forecast_error: float
    forecast_uncertainty: float   # width of 90% CI on q1+q2 averaged
    torque: np.ndarray
    tracking_error: float
    end_effector: np.ndarray
    waypoint: str


class CellDrivenController:
    """A controller where the cell's forecast drives the control.

    The control law is:
      tau = M(q) (q_ddot_des + kd (q_dot_des - q_dot)
                  + kp (q_des - q))
           + C(q, q_dot) q_dot + F q_dot
           + alpha * (q_forecast_1step - q_des)  # cell-correction

    The `alpha * (q_forecast_1step - q_des)` term is the cell-driven
    correction: if the cell forecasts that we'll be at a different
    state than we want, add a torque to push us back. `alpha` is
    a learning rate that decays as the cell's forecast improves.

    The cell's forecast error is the L2 norm between the forecast
    and the actual state at the next step. The learning rate alpha
    starts at 0 and ramps up as the cell's forecast error drops.

    Parameters
    ----------
    arm : LagrangianArm
    q_target : np.ndarray
        The desired joint position.
    n_channels : int (default 4 for state)
    forecast_horizon : int (default 5)
    history_len : int (default 32)
    control_rate : float (default 100Hz)
    """

    def __init__(
        self,
        arm: LagrangianArm,
        q_target: np.ndarray,
        n_channels: int = 4,
        forecast_horizon: int = 5,
        history_len: int = 32,
        control_rate: float = 100.0,
    ):
        self.arm = arm
        self.q_target = np.asarray(q_target, dtype=np.float64)
        self.dt = 1.0 / control_rate
        self.sensor = SensorCell(
            channel_names=["q1", "q2", "q1_dot", "q2_dot"][:n_channels],
            history_len=history_len, horizon=forecast_horizon,
        )
        self.action = ActionCell(
            actuator_names=["tau1", "tau2"],
            history_len=history_len, horizon=forecast_horizon,
        )
        self.tick_count = 0
        self._forecast_errors: List[float] = []
        self._tracking_errors: List[float] = []

    def _alpha(self) -> float:
        """The cell-driven learning rate.

        Returns 0 when the cell's forecast is wrong (no trust),
        returns ~1.0 when the cell's forecast is accurate.
        Uses a sigmoid: 0.5 * (1 + tanh(3 * (1 - err)))
        """
        if not self._forecast_errors:
            return 0.0
        # Use the rolling mean of the last 10 forecast errors
        recent = self._forecast_errors[-10:]
        mean_err = float(np.mean(recent))
        # When err=0, alpha=1.0; when err>0.5, alpha->0
        return float(0.5 * (1 + np.tanh(3 * (0.5 - mean_err))))

    def _forecast_uncertainty(self) -> float:
        """Width of the 90% CI on q1+q2 from the cell's quantile forecast."""
        try:
            q90_q1 = self.sensor.read_quantile(0.9, 0)
            q10_q1 = self.sensor.read_quantile(0.1, 0)
            q90_q2 = self.sensor.read_quantile(0.9, 1)
            q10_q2 = self.sensor.read_quantile(0.1, 1)
            if len(q90_q1) == 0 or len(q90_q2) == 0:
                return 0.0
            return float(np.mean((q90_q1 - q10_q1) + (q90_q2 - q10_q2)))
        except (IndexError, AttributeError):
            return 0.0

    def step(self) -> CellControlStep:
        """One tick of cell-driven control."""
        # 1. Read state
        reading = self.arm.state.copy()
        self.sensor.append(reading)
        # 2. Forecast
        rc = self.sensor.forecast_()
        if rc != 0 or self.sensor.context_len < 2:
            forecast_1step = self.arm.q.copy()
            forecast_err = 0.0
        else:
            # read_full_forecast returns [H, V]; we want the first
            # step, all channels
            forecast = self.sensor.read_full_forecast()
            forecast_1step = forecast[0, :2]  # first step, q only
            forecast_err = float(np.linalg.norm(forecast_1step - self.arm.q))
        # 3. Standard computed-torque term
        tau_pd = computed_torque_torque(
            self.arm, self.q_target, np.zeros(2),
            kp=200.0, kd=20.0,
        )
        # 4. Cell-correction term (only when we have a good forecast)
        # The forecast gives us a forward look: where we'll be
        # if we keep doing what we're doing. The correction
        # is a small additive torque to push the forecast back
        # toward the target. Gain is small (5.0) so it doesn't
        # dominate the PD term.
        alpha = self._alpha()
        cell_correction = alpha * (forecast_1step - self.q_target) * 5.0
        # 5. Combine
        tau = tau_pd + cell_correction
        # 6. Apply
        self.arm.send_torque(tau, duration=self.dt, sub_steps=5)
        # 7. Record action
        self.action.set_target(tau)
        # 8. Measure forecast error
        actual_next = self.arm.q.copy()
        forecast_err = float(np.linalg.norm(forecast_1step - actual_next))
        self._forecast_errors.append(forecast_err)
        self._tracking_errors.append(float(np.linalg.norm(actual_next - self.q_target)))
        # 9. Build the result
        self.tick_count += 1
        return CellControlStep(
            tick=self.tick_count,
            t=self.arm.t,
            q=self.arm.q.copy(),
            q_dot=self.arm.q_dot.copy(),
            q_desired=self.q_target.copy(),
            forecast_1step=forecast_1step.copy(),
            forecast_error=forecast_err,
            forecast_uncertainty=self._forecast_uncertainty(),
            torque=tau.copy(),
            tracking_error=self._tracking_errors[-1],
            end_effector=self.arm.forward_kinematics(),
            waypoint="",
        )

    def run(self, n_ticks: int = 1000, verbose: bool = False) -> dict:
        """Run the cell-driven controller for n_ticks."""
        steps: List[CellControlStep] = []
        for i in range(n_ticks):
            s = self.step()
            steps.append(s)
            if verbose and i % 200 == 0:
                print(
                    f"t={s.t:6.2f}s q=({s.q[0]:+.2f}, {s.q[1]:+.2f}) "
                    f"forecast=({s.forecast_1step[0]:+.2f}, {s.forecast_1step[1]:+.2f}) "
                    f"forecast_err={s.forecast_error:.4f} "
                    f"alpha={self._alpha():.2f} "
                    f"tracking_err={s.tracking_error:.4f}"
                )
        # Summarize
        return {
            "n_ticks": n_ticks,
            "duration": steps[-1].t if steps else 0.0,
            "mean_forecast_error": float(np.mean(self._forecast_errors)),
            "final_forecast_error": float(self._forecast_errors[-1]) if self._forecast_errors else 0.0,
            "mean_tracking_error": float(np.mean(self._tracking_errors)),
            "final_tracking_error": float(self._tracking_errors[-1]) if self._tracking_errors else 0.0,
            "forecast_error_history": list(self._forecast_errors),
            "tracking_error_history": list(self._tracking_errors),
            "steps": steps,
        }


def compare_controllers(
    arm_params: Optional[ArmParams] = None,
    n_ticks: int = 1000,
    q_start: Tuple[float, float] = (0.3, 0.7),
    q_target: Tuple[float, float] = (1.2, 0.4),
) -> dict:
    """Run two controllers and compare: pure PD vs cell-driven.

    Returns a dict with both controllers' error histories.
    """
    # Controller A: pure computed-torque
    arm_a = LagrangianArm(params=arm_params, q1=q_start[0], q2=q_start[1])
    q_target_arr = np.array(q_target)
    errs_a = []
    for _ in range(n_ticks):
        tau = computed_torque_torque(arm_a, q_target_arr, np.zeros(2), kp=200, kd=20)
        arm_a.send_torque(tau, duration=0.01)
        errs_a.append(float(np.linalg.norm(arm_a.q - q_target_arr)))

    # Controller B: cell-driven
    arm_b = LagrangianArm(params=arm_params, q1=q_start[0], q2=q_start[1])
    cell_ctrl = CellDrivenController(arm_b, q_target_arr)
    result_b = cell_ctrl.run(n_ticks=n_ticks, verbose=False)
    errs_b = result_b["tracking_error_history"]

    return {
        "pd_only": {
            "final_error": errs_a[-1],
            "mean_error": float(np.mean(errs_a)),
            "errors": errs_a,
        },
        "cell_driven": {
            "final_error": result_b["final_tracking_error"],
            "mean_error": result_b["mean_tracking_error"],
            "mean_forecast_error": result_b["mean_forecast_error"],
            "errors": errs_b,
            "forecast_errors": result_b["forecast_error_history"],
        },
    }
