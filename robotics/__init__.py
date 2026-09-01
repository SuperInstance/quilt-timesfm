"""Robotics-shaped cells — the interface between the cell model and a robot.

This module is the bridge. It doesn't run a real robot (no ROS, no
MuJoCo, no Isaac), but it defines the cell shape and the data flow
that would let a `time.cell` forecast be used as the input to a
robot controller.

The motivation: the README says "agents that act on the world need
to forecast". For a trading agent, the world is a price series. For
a robotic agent, the world is a stream of sensor readings. The
cell model — context, forecast, quantiles, read — applies to both.

This module provides:

  - SensorCell: a cell whose state is a multivariate sensor stream
    (joint angles, IMU, force, vision features) and whose forecast
    is a predicted future state.
  - ActionCell: a cell whose state is a target trajectory (joint
    positions, gripper commands) and whose value is a feasible
    motion plan.
  - ControlLoop: a tick loop that ties sensor -> forecast -> action
    -> command -> record outcome -> update calibration. The shape is
    exactly the same as PaperTrader, but the cells are different.
  - A pick-and-place demo: a 2-DOF arm simulated as a 2-channel
    sensor stream. Forecast the next position, decide whether to
    move, record the result.

The cell shape is the same as `time.cell`:

  - context: 2D float array of shape [T, V]
  - horizon: number of future steps
  - forecast: 2D array of shape [H, V]
  - quantiles: 3D array of shape [9, H, V]
  - 5 ops: BIND_CONTEXT, BIND_COVARIATE, FORECAST, READ_POINT, READ_QUANTILE
  - 5+1 laws: BIND idempotence, LINK transitivity, EFFECT
    associativity, VIEW purity, TICK monotonicity, FORGET completeness

What this does NOT do (yet):

  - Real physics. The 2-DOF arm is kinematic only — no torque,
    no inertia, no collision. Use a proper simulator (MuJoCo,
    Isaac, Brax) for those.
  - Vision. The "vision" channel is a synthetic 1-D feature,
    not pixels. JEPA-style latent prediction would go here.
  - Reinforcement learning. The control loop is deterministic
    (forecast -> decide -> execute), not policy-gradient.
"""

from .sensor_cell import SensorCell
from .action_cell import ActionCell
from .control_loop import ControlLoop, RobotState, RobotAction
from .pick_and_place import PickAndPlaceDemo, TwoDOFArm

__all__ = [
    "SensorCell",
    "ActionCell",
    "ControlLoop",
    "RobotState",
    "RobotAction",
    "PickAndPlaceDemo",
    "TwoDOFArm",
]
