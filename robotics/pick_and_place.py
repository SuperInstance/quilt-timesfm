"""A pick-and-place demo: a 2-DOF arm simulated as a 2-channel sensor stream.

The arm has two joints. The "sensor" is the (q1, q2) reading at
each timestep. The "actuator" is the (q1, q2) command to send.
The "target" is a (x, y) end-effector position, which we map back
to (q1, q2) via a simple inverse-kinematics approximation.

The simulation:
  - At each step, the arm reads its current (q1, q2)
  - It forecasts where it will be in H steps (linear extrapolation)
  - It checks the forecast against the desired end-effector position
  - If off, it plans a corrective motion
  - It records the actual next reading as the "outcome"

The point of the demo is to show that the same cell machinery
works for robotics. The actual physics is faked — there's no
torque, no inertia, no collision. The forecast is just linear
extrapolation; the "correction" is also linear.
"""
from __future__ import annotations
import numpy as np
from typing import Iterator, Tuple, List
from .sensor_cell import SensorCell
from .action_cell import ActionCell
from .control_loop import ControlLoop, RobotState, RobotAction


class TwoDOFArm:
    """A 2-DOF arm: link 1 of length 1.0, link 2 of length 1.0.

    Joint angles q1, q2 are in radians. End-effector position is:
        x = cos(q1) + cos(q1 + q2)
        y = sin(q1) + sin(q1 + q2)

    Inverse kinematics (analytical) returns the two elbow-up/down
    solutions; we just pick the first.
    """

    LINK1 = 1.0
    LINK2 = 1.0

    def __init__(self, q1: float = 0.5, q2: float = 1.0):
        self.q1 = q1
        self.q2 = q2

    def forward_kinematics(self) -> np.ndarray:
        x = self.LINK1 * np.cos(self.q1) + self.LINK2 * np.cos(self.q1 + self.q2)
        y = self.LINK1 * np.sin(self.q1) + self.LINK2 * np.sin(self.q1 + self.q2)
        return np.array([x, y])

    def inverse_kinematics(self, target_xy: np.ndarray) -> np.ndarray:
        """Analytical IK for the 2-DOF arm. Returns (q1, q2)."""
        x, y = target_xy
        # Reachability check
        d2 = x * x + y * y
        d = np.sqrt(d2)
        d_max = self.LINK1 + self.LINK2
        d_min = abs(self.LINK1 - self.LINK2)
        if d > d_max or d < d_min:
            return None  # unreachable
        # cos(q2) = (d^2 - L1^2 - L2^2) / (2 L1 L2)
        cos_q2 = (d2 - self.LINK1 ** 2 - self.LINK2 ** 2) / (2 * self.LINK1 * self.LINK2)
        cos_q2 = np.clip(cos_q2, -1.0, 1.0)
        q2_a = np.arccos(cos_q2)
        q2_b = -q2_a
        # q1 = atan2(y, x) - atan2(L2 sin(q2), L1 + L2 cos(q2))
        def solve(q2):
            return np.arctan2(y, x) - np.arctan2(
                self.LINK2 * np.sin(q2), self.LINK1 + self.LINK2 * np.cos(q2)
            )
        return np.array([solve(q2_a), q2_a])

    def step(self, command: np.ndarray, noise_std: float = 0.01) -> np.ndarray:
        """Apply a (q1, q2) command. Returns the new sensor reading.

        The arm tracks the command with a first-order lag and
        Gaussian noise. This is a stand-in for real dynamics.
        """
        if command is None:
            return np.array([self.q1, self.q2])
        alpha = 0.3  # first-order lag coefficient
        self.q1 = self.q1 + alpha * (command[0] - self.q1) + np.random.normal(0, noise_std)
        self.q2 = self.q2 + alpha * (command[1] - self.q2) + np.random.normal(0, noise_std)
        return np.array([self.q1, self.q2])


class PickAndPlaceDemo:
    """Run a 2-DOF arm through a pick-and-place task using the cell model.

    The task: start at a "home" position, reach a "pick" position,
    hold for a few steps, then reach a "place" position. The
    controller uses the SensorCell to forecast the next state and
    the ActionCell to plan corrective motions.
    """

    def __init__(
        self,
        home_xy: np.ndarray = None,
        pick_xy: np.ndarray = None,
        place_xy: np.ndarray = None,
    ):
        home_xy = np.asarray(home_xy if home_xy is not None else [1.2, 0.0])
        pick_xy = np.asarray(pick_xy if pick_xy is not None else [0.5, 1.0])
        place_xy = np.asarray(place_xy if place_xy is not None else [-0.5, 1.0])
        # Build the arm at the home position
        arm = TwoDOFArm()
        home_q = arm.inverse_kinematics(home_xy)
        if home_q is None:
            raise ValueError(f"home position {home_xy} unreachable")
        arm.q1, arm.q2 = home_q
        self.arm = arm
        # Build the cells
        self.sensor = SensorCell(channel_names=["q1", "q2"], history_len=32, horizon=5)
        self.action = ActionCell(actuator_names=["q1", "q2"], history_len=32, horizon=5)
        # The control loop's target is the desired end-effector position
        # in joint space. The controller reads the joint angles
        # (SensorCell) and decides the next joint angles (ActionCell).
        # The "target" is the joint angles corresponding to the
        # currently-desired end-effector position. We start at home.
        self.target_q = home_q.copy()
        self.controller = ControlLoop(
            sensor_cell=self.sensor,
            action_cell=self.action,
            n_channels=2,
            n_actuators=2,
            target=self.target_q,
            error_threshold=0.05,
            stop_threshold=3.0,  # Joint-space distance, not end-effector
        )
        # The waypoints: home -> pick -> place
        self.waypoints = [
            ("home", home_q, 10),    # hold for 10 steps
            ("pick", arm.inverse_kinematics(pick_xy), 30),  # move to pick, hold 30
            ("place", arm.inverse_kinematics(place_xy), 30),
        ]
        self._waypoint_idx = 0
        self._waypoint_step = 0

    def _current_waypoint(self):
        return self.waypoints[self._waypoint_idx]

    def step(self) -> RobotState:
        """One tick of the demo."""
        # Read the current joint angles
        reading = np.array([self.arm.q1, self.arm.q2])
        # Update the target from the current waypoint
        name, target_q, hold_steps = self._current_waypoint()
        # If we're close to the current waypoint target, advance
        if np.linalg.norm(reading - self.target_q) < 0.05:
            self._waypoint_step += 1
            if self._waypoint_step >= hold_steps:
                self._waypoint_idx = (self._waypoint_idx + 1) % len(self.waypoints)
                self._waypoint_step = 0
        # Always update target to current waypoint
        self.controller.target = target_q.copy()
        # Tick the controller
        state = self.controller.step(reading)
        # Apply the command
        if state.command is not None:
            self.arm.step(state.command)
        return state

    def run(self, n_steps: int = 200, verbose: bool = False) -> dict:
        """Run the demo for `n_steps` ticks."""
        states: List[RobotState] = []
        for i in range(n_steps):
            s = self.step()
            states.append(s)
            if verbose and i % 20 == 0:
                name, _, _ = self._current_waypoint()
                print(
                    f"t={i:4d} q=({s.sensor_reading[0]:+.2f}, {s.sensor_reading[1]:+.2f}) "
                    f"action={s.action.value:11s} target=({name})  "
                    f"rationale={s.rationale[:50]}"
                )
        return {
            "n_steps": n_steps,
            "states": states,
            "n_stops": sum(1 for s in states if s.action == RobotAction.STOP),
            "n_corrects": sum(1 for s in states if s.action == RobotAction.CORRECT),
            "n_holds": sum(1 for s in states if s.action == RobotAction.HOLD),
        }
