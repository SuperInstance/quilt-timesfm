"""Real pick-and-place: 2-link arm with Lagrangian dynamics + computed-torque control.

This is the real robotics demo. The dynamics are Lagrangian (proper
mass matrix, Coriolis, friction), the controller is computed-torque
with full nonlinear compensation, and the cell model wraps the
sensor stream + trajectory planning.

The task is the same as the kinematic PickAndPlaceDemo (home ->
pick -> place) but with real physics:
  - The arm has inertia, so commands don't move it instantly
  - Coriolis forces couple the joints
  - Friction slows small motions
  - The cell's forecast is used for look-ahead (1-step ahead),
    the computed-torque controller uses the full dynamics for
    feedback
"""
from __future__ import annotations
import numpy as np
from typing import Iterator, Tuple, List, Optional

from .lagrangian_arm import (
    LagrangianArm, ArmParams, TrajectoryPoint,
    gravity_compensation_torque,
    impedance_torque,
    computed_torque_torque,
    ik_2link,
    min_jerk_trajectory,
)
from .sensor_cell import SensorCell
from .action_cell import ActionCell


# TrajectoryPoint and min_jerk_trajectory are imported from lagrangian_arm.


class RealPickAndPlace:
    """Pick-and-place with real Lagrangian dynamics.

    Parameters
    ----------
    home_xy : (x, y) of the home position
    pick_xy : (x, y) of the pick position
    place_xy : (x, y) of the place position
    arm_params : ArmParams (default: desktop-scale arm)
    duration_per_segment : float
        Wall-clock time for each waypoint transition (seconds).
    control_rate : float
        Control loop rate in Hz (default 100Hz = 10ms per tick).
    """

    def __init__(
        self,
        home_xy: Tuple[float, float] = (0.6, 0.0),
        pick_xy: Tuple[float, float] = (0.3, 0.4),
        place_xy: Tuple[float, float] = (-0.3, 0.4),
        arm_params: Optional[ArmParams] = None,
        duration_per_segment: float = 1.0,
        control_rate: float = 100.0,
    ):
        # Build the arm with default parameters
        self.arm = LagrangianArm(params=arm_params or ArmParams())
        # Plan IK for each waypoint
        self.waypoints = []
        for name, xy in [("home", home_xy), ("pick", pick_xy), ("place", place_xy)]:
            q = ik_2link(np.array(xy), self.arm.p.L1, self.arm.p.L2)
            if q is None:
                raise ValueError(
                    f"waypoint {name} at {xy} is unreachable with this arm"
                )
            self.waypoints.append((name, q))
        # Move the arm to the home position
        self.arm.reset(q=self.waypoints[0][1])
        # Build the cells
        self.sensor = SensorCell(
            channel_names=["q1", "q2", "q1_dot", "q2_dot"],
            history_len=32, horizon=5,
        )
        self.action = ActionCell(
            actuator_names=["tau1", "tau2"],
            history_len=32, horizon=5,
        )
        # The trajectory we're following
        self.trajectory: List[TrajectoryPoint] = []
        self.trajectory_start: float = 0.0
        self.waypoint_idx: int = 0
        self.duration_per_segment = duration_per_segment
        self.dt = 1.0 / control_rate
        # Bookkeeping
        self.tick_count = 0
        self._plan_next_trajectory()

    def _plan_next_trajectory(self) -> None:
        """Plan a min-jerk trajectory from the current pose to the next waypoint."""
        next_idx = (self.waypoint_idx + 1) % len(self.waypoints)
        _, q_target = self.waypoints[next_idx]
        self.trajectory = min_jerk_trajectory(
            q_start=self.arm.q.copy(),
            q_end=q_target,
            duration=self.duration_per_segment,
            n_points=50,
        )
        self.trajectory_start = self.arm.t
        self.waypoint_idx = next_idx

    def _desired_state(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (q_desired, q_dot_desired) at the current time.

        We look up the current trajectory point and the next one
        to compute a finite-difference velocity estimate.
        """
        t_local = self.arm.t - self.trajectory_start
        if t_local >= self.trajectory[-1].t:
            # Reached the end of the current segment
            q_des = self.trajectory[-1].q
            q_dot_des = np.zeros(2)
            return q_des, q_dot_des
        # Find the surrounding trajectory points
        for i in range(len(self.trajectory) - 1):
            if self.trajectory[i].t <= t_local < self.trajectory[i + 1].t:
                p0 = self.trajectory[i]
                p1 = self.trajectory[i + 1]
                alpha = (t_local - p0.t) / max(1e-9, p1.t - p0.t)
                q_des = p0.q * (1 - alpha) + p1.q * alpha
                q_dot_des = (p1.q - p0.q) / max(1e-9, p1.t - p0.t)
                return q_des, q_dot_des
        return self.trajectory[-1].q, np.zeros(2)

    def step(self) -> dict:
        """One control tick. Returns a status dict."""
        # 1. Read the sensor (state)
        reading = self.arm.state.copy()
        self.sensor.append(reading)
        # 2. Forecast the next state (FORECAST)
        self.sensor.forecast_()
        forecast = self.sensor.read_point(0)  # [H=5, V=4]
        # 3. Compute the desired state from the trajectory
        q_des, q_dot_des = self._desired_state()
        # 4. Computed-torque control with full dynamics
        tau = computed_torque_torque(self.arm, q_des, q_dot_des,
                                     kp=200.0, kd=20.0)
        # 5. Apply the torque
        self.arm.send_torque(tau, duration=self.dt, sub_steps=5)
        # 6. Record the action
        self.action.set_target(tau)
        # 7. Check if we should replan
        waypoint_name, waypoint_q = self.waypoints[self.waypoint_idx]
        if (np.linalg.norm(self.arm.q - waypoint_q) < 0.01
                and self.arm.t - self.trajectory_start > self.duration_per_segment - 0.1):
            self._plan_next_trajectory()
        # 8. Build the status
        self.tick_count += 1
        status = {
            "tick": self.tick_count,
            "t": self.arm.t,
            "q": self.arm.q.copy(),
            "q_dot": self.arm.q_dot.copy(),
            "q_desired": q_des.copy(),
            "q_dot_desired": q_dot_des.copy(),
            "tau": tau.copy(),
            "tracking_error": float(np.linalg.norm(self.arm.q - q_des)),
            "forecast_1step": forecast[0].tolist() if len(forecast) > 0 else None,
            "end_effector": self.arm.forward_kinematics().tolist(),
            "waypoint": waypoint_name,
        }
        return status

    def run(self, n_ticks: int = 1000, verbose: bool = False) -> dict:
        """Run the controller for `n_ticks` ticks. Returns a summary."""
        statuses: List[dict] = []
        for i in range(n_ticks):
            s = self.step()
            statuses.append(s)
            if verbose and i % 100 == 0:
                print(
                    f"t={s['t']:6.2f}s q=({s['q'][0]:+.2f}, {s['q'][1]:+.2f}) "
                    f"tau=({s['tau'][0]:+6.2f}, {s['tau'][1]:+6.2f}) "
                    f"err={s['tracking_error']:.4f} "
                    f"ee=({s['end_effector'][0]:+.2f}, {s['end_effector'][1]:+.2f}) "
                    f"-> {s['waypoint']}"
                )
        # Summarize
        tracking_errors = [s["tracking_error"] for s in statuses]
        return {
            "n_ticks": n_ticks,
            "duration": statuses[-1]["t"] if statuses else 0.0,
            "mean_tracking_error": float(np.mean(tracking_errors)),
            "max_tracking_error": float(np.max(tracking_errors)),
            "final_waypoint": statuses[-1]["waypoint"] if statuses else None,
            "statuses": statuses,
        }
