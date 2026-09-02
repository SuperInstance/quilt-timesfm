"""Robotics — cells + real Lagrangian dynamics + computed-torque control.

The cell model (SensorCell, ActionCell) wraps a real robot arm:

  - LagrangianArm: a 2-link planar arm with proper mass matrix,
    Coriolis, and friction. State is (q, q_dot). The dynamics
    are integrated with RK4 at 1ms sub-steps.
  - RealPickAndPlace: a pick-and-place task that uses computed-torque
    control (full nonlinear dynamics cancellation) and min-jerk
    trajectories between waypoints. Tracks position to <0.01 rad.
  - SensorCell: a 4-channel cell (q1, q2, q1_dot, q2_dot) whose
    forecast is the predicted next state. Used for look-ahead.
  - ActionCell: a 2-channel cell (tau1, tau2) whose forecast is
    the planned torque trajectory.
  - ControlLoop: a tick loop that ties sensor -> forecast -> action
    -> command -> record outcome.
  - PickAndPlaceDemo (legacy): a kinematic version kept for
    comparison with the real arm.

The cell shape is the same as `time.cell`:

  - context: 2D float array of shape [T, V]
  - horizon: number of future steps
  - forecast: 2D array of shape [H, V]
  - quantiles: 3D array of shape [9, H, V]
  - 5 ops: BIND_CONTEXT, BIND_COVARIATE, FORECAST, READ_POINT, READ_QUANTILE
  - 5+1 laws: BIND idempotence, LINK transitivity, EFFECT
    associativity, VIEW purity, TICK monotonicity, FORGET completeness

Why the cell model fits robotics: in trading, the world is a
price series. In robotics, the world is a sensor stream. The
cell machinery — context, forecast, quantiles, read — applies
to both. The substrate binding (TimesFM for prices, Lagrangian
dynamics for the arm) is the only thing that varies.
"""

from .sensor_cell import SensorCell
from .action_cell import ActionCell
from .control_loop import ControlLoop, RobotState, RobotAction
from .pick_and_place import PickAndPlaceDemo, TwoDOFArm
from .lagrangian_arm import (
    LagrangianArm, ArmParams,
    gravity_compensation_torque,
    impedance_torque,
    computed_torque_torque,
    ik_2link,
    min_jerk_trajectory,
)
from .real_pick_and_place import RealPickAndPlace, TrajectoryPoint
from .cell_driven_controller import (
    CellDrivenController, CellControlStep, compare_controllers,
)

__all__ = [
    "SensorCell",
    "ActionCell",
    "ControlLoop",
    "RobotState",
    "RobotAction",
    "PickAndPlaceDemo",
    "TwoDOFArm",
    "LagrangianArm",
    "ArmParams",
    "gravity_compensation_torque",
    "impedance_torque",
    "computed_torque_torque",
    "ik_2link",
    "min_jerk_trajectory",
    "RealPickAndPlace",
    "TrajectoryPoint",
    "CellDrivenController",
    "CellControlStep",
    "compare_controllers",
]
