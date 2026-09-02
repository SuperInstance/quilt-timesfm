"""A 2-link planar arm with proper Lagrangian dynamics.

This is a real robot dynamics model — Newton-Euler / Lagrangian
equations of motion, not a kinematic fudge. The arm has:

  - Two revolute joints, q1 (shoulder) and q2 (elbow)
  - Link 1: length L1, mass m1, center of mass at L1/2
  - Link 2: length L2, mass m2, center of mass at L2/2
  - No gravity (planar — the arm is in the horizontal plane)
  - Viscous friction at each joint
  - External torque commands at each joint

The dynamics are governed by:
  M(q) * q_ddot + C(q, q_dot) * q_dot + F * q_dot = tau

where M is the 2x2 mass matrix, C is the Coriolis/centripetal
matrix, F is the friction matrix, and tau is the torque vector.

Given a torque command, the simulator integrates the dynamics
forward in time using RK4 (Runge-Kutta 4th order) at 1ms
sub-steps. This is a real robot arm.

The cell model wraps this:
  - SensorCell reads (q1, q2, q1_dot, q2_dot) at each timestep
  - ActionCell plans the next torque command
  - ControlLoop ties them together
  - The "forecast" is the predicted next state, used for MPC-style
    look-ahead

Why a 2-link arm:
  - Closed-form forward kinematics and dynamics
  - Famous textbook example (Spong, Hutchinson, Vidyasagar)
  - Enough complexity to be interesting (coupled dynamics) but
    not so much that it needs a real robot to validate

This is the real robotics interface. A 7-DOF arm or a mobile
manipulator would just extend the same pattern with more joints.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class ArmParams:
    """Physical parameters of the 2-link arm.

    All units are SI (meters, kilograms, seconds, radians, Nm).
    Defaults are a desktop-scale arm.
    """
    L1: float = 0.5            # length of link 1 (m)
    L2: float = 0.4            # length of link 2 (m)
    m1: float = 1.5            # mass of link 1 (kg)
    m2: float = 1.0            # mass of link 2 (kg)
    I1: float = 0.05           # moment of inertia of link 1 about COM (kg m^2)
    I2: float = 0.03           # moment of inertia of link 2 about COM (kg m^2)
    c1: float = 0.25           # COM distance from joint 1 (m)
    c2: float = 0.20           # COM distance from joint 2 (m)
    b1: float = 0.1            # viscous friction at joint 1 (N m s/rad)
    b2: float = 0.05           # viscous friction at joint 2 (N m s/rad)
    tau_max: float = 20.0      # max torque at each joint (N m)


class LagrangianArm:
    """A 2-link planar arm with real Lagrangian dynamics.

    State: (q1, q2, q1_dot, q2_dot) — 4-dimensional
    Control: (tau1, tau2) — 2-dimensional torques

    Integration: RK4 with sub-steps (default 1ms each).
    The simulation step is the outer "tick" (default 10ms);
    RK4 sub-steps integrate within the tick for accuracy.
    """

    def __init__(self, params: Optional[ArmParams] = None,
                 q1: float = 0.5, q2: float = 1.0,
                 q1_dot: float = 0.0, q2_dot: float = 0.0):
        self.p = params or ArmParams()
        self.q = np.array([q1, q2], dtype=np.float64)
        self.q_dot = np.array([q1_dot, q2_dot], dtype=np.float64)
        self.t = 0.0  # simulation time

    @property
    def state(self) -> np.ndarray:
        return np.concatenate([self.q, self.q_dot])

    def mass_matrix(self, q: np.ndarray) -> np.ndarray:
        """Compute the 2x2 mass matrix M(q)."""
        p = self.p
        q1, q2 = q
        c2 = np.cos(q2)
        m11 = (p.I1 + p.I2
               + p.m1 * p.c1 ** 2
               + p.m2 * (p.L1 ** 2 + p.c2 ** 2 + 2 * p.L1 * p.c2 * c2))
        m12 = p.I2 + p.m2 * (p.c2 ** 2 + p.L1 * p.c2 * c2)
        m22 = p.I2 + p.m2 * p.c2 ** 2
        return np.array([[m11, m12], [m12, m22]])

    def coriolis(self, q: np.ndarray, q_dot: np.ndarray) -> np.ndarray:
        """Compute the Coriolis/centripetal vector C(q, q_dot) q_dot."""
        p = self.p
        q1, q2 = q
        q1d, q2d = q_dot
        s2 = np.sin(q2)
        h = -p.m2 * p.L1 * p.c2 * s2
        c11 = h * q2d
        c12 = h * (q1d + q2d)
        c21 = -h * q1d
        c22 = 0.0
        return np.array([
            c11 * q1d + c12 * q2d,
            c21 * q1d + c22 * q2d,
        ])

    def friction(self, q_dot: np.ndarray) -> np.ndarray:
        """Viscous friction: F q_dot."""
        return np.array([self.p.b1 * q_dot[0], self.p.b2 * q_dot[1]])

    def acceleration(self, q: np.ndarray, q_dot: np.ndarray, tau: np.ndarray) -> np.ndarray:
        """Compute q_ddot given (q, q_dot, tau) via the equation of motion.

        M(q) q_ddot + C(q, q_dot) q_dot + F q_dot = tau
        =>  q_ddot = M^{-1} (tau - C q_dot - F q_dot)
        """
        M = self.mass_matrix(q)
        Cq_dot = self.coriolis(q, q_dot)
        Fq_dot = self.friction(q_dot)
        rhs = tau - Cq_dot - Fq_dot
        return np.linalg.solve(M, rhs)

    def dynamics(self, state: np.ndarray, tau: np.ndarray) -> np.ndarray:
        """The state derivative: [q_dot; q_ddot]."""
        q, q_dot = state[:2], state[2:]
        q_ddot = self.acceleration(q, q_dot, tau)
        return np.concatenate([q_dot, q_ddot])

    def rk4_step(self, tau: np.ndarray, dt: float) -> None:
        """One RK4 integration step."""
        state = self.state
        k1 = self.dynamics(state, tau)
        k2 = self.dynamics(state + 0.5 * dt * k1, tau)
        k3 = self.dynamics(state + 0.5 * dt * k2, tau)
        k4 = self.dynamics(state + dt * k3, tau)
        new_state = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        self.q = new_state[:2]
        self.q_dot = new_state[2:]
        self.t += dt

    def send_torque(self, tau: np.ndarray, duration: float = 0.01,
                    sub_steps: int = 10) -> np.ndarray:
        """Apply a torque for `duration` seconds and return the new state.

        The torque is clamped to ±tau_max at each joint. The
        integration is sub-stepped `sub_steps` times for accuracy.

        Parameters
        ----------
        tau : np.ndarray, shape (2,)
            Joint torques (N m). Clamped to ±p.tau_max.
        duration : float
            Wall-clock duration to apply the torque. Default 10ms.
        sub_steps : int
            Number of RK4 sub-steps within the duration. Default 10.

        Returns
        -------
        np.ndarray
            The new state (q1, q2, q1_dot, q2_dot).
        """
        tau = np.clip(np.asarray(tau, dtype=np.float64),
                      -self.p.tau_max, self.p.tau_max)
        dt = duration / sub_steps
        for _ in range(sub_steps):
            self.rk4_step(tau, dt)
        return self.state.copy()

    def forward_kinematics(self) -> np.ndarray:
        """End-effector position (x, y)."""
        q1, q2 = self.q
        x = self.p.L1 * np.cos(q1) + self.p.L2 * np.cos(q1 + q2)
        y = self.p.L1 * np.sin(q1) + self.p.L2 * np.sin(q1 + q2)
        return np.array([x, y])

    def jacobian(self) -> np.ndarray:
        """The 2x2 geometric Jacobian at the end-effector."""
        q1, q2 = self.q
        j11 = -self.p.L1 * np.sin(q1) - self.p.L2 * np.sin(q1 + q2)
        j12 = -self.p.L2 * np.sin(q1 + q2)
        j21 = self.p.L1 * np.cos(q1) + self.p.L2 * np.cos(q1 + q2)
        j22 = self.p.L2 * np.cos(q1 + q2)
        return np.array([[j11, j12], [j21, j22]])

    def reset(self, q: Optional[np.ndarray] = None,
              q_dot: Optional[np.ndarray] = None) -> None:
        """Reset the arm to the given state (or to defaults)."""
        if q is not None:
            self.q = np.asarray(q, dtype=np.float64)
        if q_dot is not None:
            self.q_dot = np.asarray(q_dot, dtype=np.float64)
        self.t = 0.0


# ─── High-level controllers ───────────────────────────────────────

def gravity_compensation_torque(arm: LagrangianArm) -> np.ndarray:
    """Compute the torque needed to hold the arm against gravity.

    For a planar (horizontal) arm, gravity is zero, so this
    returns zero. For a vertical arm, this would compute
    M * g * cos(q) terms. Useful as a baseline.
    """
    return np.zeros(2)


def impedance_torque(arm: LagrangianArm, q_desired: np.ndarray,
                     kp: float = 50.0, kd: float = 5.0) -> np.ndarray:
    """Impedance control: tau = kp (q_desired - q) - kd q_dot.

    This is a simple spring-damper around the desired position.
    It assumes the arm's gravity is already compensated.
    """
    err = q_desired - arm.q
    return kp * err - kd * arm.q_dot


def computed_torque_torque(arm: LagrangianArm, q_desired: np.ndarray,
                           q_dot_desired: np.ndarray,
                           kp: float = 100.0, kd: float = 20.0) -> np.ndarray:
    """Computed-torque controller with full dynamics cancellation.

    tau = M(q) (q_ddot_desired + kd (q_dot_desired - q_dot)
                + kp (q_desired - q))
        + C(q, q_dot) q_dot + F q_dot

    With q_dot_desired = 0 and q_ddot_desired = 0, this becomes
    a PD controller with full nonlinear compensation. Standard
    in modern robotics (Spong et al., chapter 6).
    """
    M = arm.mass_matrix(arm.q)
    Cq_dot = arm.coriolis(arm.q, arm.q_dot)
    Fq_dot = arm.friction(arm.q_dot)
    err = q_desired - arm.q
    err_dot = q_dot_desired - arm.q_dot
    q_ddot_desired = kp * err + kd * err_dot
    return M @ q_ddot_desired + Cq_dot + Fq_dot


def ik_2link(target_xy: np.ndarray,
             L1: float, L2: float,
             elbow: str = "up") -> Optional[np.ndarray]:
    """Closed-form inverse kinematics for the 2-link arm.

    Returns (q1, q2) or None if the target is unreachable.

    Parameters
    ----------
    target_xy : (x, y) in workspace
    L1, L2 : link lengths
    elbow : "up" or "down" — which IK solution to pick
    """
    x, y = target_xy
    d2 = x * x + y * y
    d = np.sqrt(d2)
    if d > L1 + L2 or d < abs(L1 - L2):
        return None
    cos_q2 = (d2 - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
    cos_q2 = np.clip(cos_q2, -1.0, 1.0)
    q2 = np.arccos(cos_q2) if elbow == "down" else -np.arccos(cos_q2)
    q1 = np.arctan2(y, x) - np.arctan2(L2 * np.sin(q2), L1 + L2 * np.cos(q2))
    return np.array([q1, q2])


def min_jerk_trajectory(q_start: np.ndarray, q_end: np.ndarray,
                        duration: float, n_points: int = 50
                        ) -> List["TrajectoryPoint"]:
    """A minimum-jerk trajectory from q_start to q_end.

    The minimum-jerk profile is the standard for smooth robot
    motion (Flash & Hogan, 1985). It minimizes the integral of
    the squared jerk (third derivative of position), which
    gives a smooth, human-like motion.
    """
    traj = []
    for i in range(n_points):
        s = i / max(1, n_points - 1)  # 0 to 1
        # 5th-order polynomial: s^3 * (10 - 15s + 6s^2)
        s3 = s * s * s
        s2 = s * s
        smooth = s3 * (10 - 15 * s + 6 * s2)
        q = q_start + (q_end - q_start) * smooth
        traj.append(TrajectoryPoint(q=q, t=s * duration))
    return traj


@dataclass
class TrajectoryPoint:
    """A point on a desired trajectory."""
    q: np.ndarray        # joint angles
    t: float             # time (s) since the start of this segment
