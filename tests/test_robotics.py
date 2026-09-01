"""Tests for the robotics-shaped cells.

The tests cover:
  - SensorCell append/bind/forecast/reads
  - ActionCell set_target/bind/forecast/next_command
  - ControlLoop step + run
  - PickAndPlaceDemo runs end-to-end
  - Cell-shape compatibility: SensorCell and ActionCell have the
    same forecast shape [H, V] and quantile shape [9, H, V].
"""
import os
os.environ.setdefault("QUILT_TIMESFM_SYNTHETIC", "1")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import warnings

warnings.simplefilter("ignore", RuntimeWarning)

import numpy as np

from robotics import (
    SensorCell, ActionCell, ControlLoop, RobotAction,
    PickAndPlaceDemo, TwoDOFArm,
)


class TestSensorCell(unittest.TestCase):
    def test_initial_state(self):
        c = SensorCell(channel_names=["q1", "q2"])
        self.assertEqual(c.n_channels, 2)
        self.assertIsNone(c.context)
        self.assertEqual(c.context_len, 0)

    def test_append(self):
        c = SensorCell(channel_names=["q1", "q2"])
        c.append(np.array([0.5, 1.0]))
        c.append(np.array([0.6, 1.1]))
        self.assertEqual(c.context_len, 2)
        self.assertEqual(c.context.shape, (2, 2))

    def test_forecast_shape(self):
        c = SensorCell(channel_names=["q1", "q2", "q3"], horizon=5)
        for i in range(20):
            c.append(np.array([np.sin(i * 0.1), np.cos(i * 0.1), np.sin(i * 0.05)]))
        rc = c.forecast_()
        self.assertEqual(rc, 0)
        p = c.read_point(0)
        self.assertEqual(p.shape, (5,))
        q = c.read_quantile(0.5, 1)
        self.assertEqual(q.shape, (5,))

    def test_read_invalid_channel(self):
        c = SensorCell(channel_names=["q1"])
        c.append(np.array([1.0]))
        c.forecast_()
        self.assertEqual(c.read_point(5).shape, (0,))

    def test_snapshot(self):
        c = SensorCell(channel_names=["q1", "q2"])
        c.append(np.array([0.1, 0.2]))
        snap = c.snapshot()
        self.assertIn("channel_names", snap)
        self.assertIn("context", snap)
        self.assertEqual(snap["context_len"], 1)


class TestActionCell(unittest.TestCase):
    def test_set_target(self):
        c = ActionCell(actuator_names=["q1", "q2"])
        c.set_target(np.array([0.5, 1.0]))
        self.assertEqual(c.context_len, 1)
        c.set_target(np.array([0.6, 1.1]))
        self.assertEqual(c.context_len, 2)

    def test_forecast_and_next_command(self):
        c = ActionCell(actuator_names=["q1", "q2"], horizon=3)
        for i in range(5):
            c.set_target(np.array([0.1 * i, 0.2 * i]))
        self.assertEqual(c.forecast_(), 0)
        cmd = c.next_command()
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.shape, (2,))
        # The next command should be near the most recent target
        self.assertAlmostEqual(cmd[0], 0.4, places=1)
        self.assertAlmostEqual(cmd[1], 0.8, places=1)

    def test_read_point_shape(self):
        c = ActionCell(actuator_names=["q1"], horizon=4)
        for i in range(3):
            c.set_target(np.array([float(i)]))
        c.forecast_()
        p = c.read_point(0)
        self.assertEqual(p.shape, (4,))


class TestTwoDOFArm(unittest.TestCase):
    def test_forward_kinematics_zero(self):
        arm = TwoDOFArm(q1=0.0, q2=0.0)
        xy = arm.forward_kinematics()
        # At (0, 0), the arm is fully extended along +x
        self.assertAlmostEqual(xy[0], 2.0, places=4)
        self.assertAlmostEqual(xy[1], 0.0, places=4)

    def test_inverse_kinematics_roundtrip(self):
        arm = TwoDOFArm()
        # Try a reachable target
        target = np.array([1.0, 1.0])
        q = arm.inverse_kinematics(target)
        self.assertIsNotNone(q)
        arm.q1, arm.q2 = q
        actual = arm.forward_kinematics()
        self.assertAlmostEqual(actual[0], target[0], places=4)
        self.assertAlmostEqual(actual[1], target[1], places=4)

    def test_unreachable_target(self):
        arm = TwoDOFArm()
        # A point further than the arm can reach
        target = np.array([3.0, 0.0])
        q = arm.inverse_kinematics(target)
        self.assertIsNone(q)

    def test_step_with_command(self):
        arm = TwoDOFArm(q1=0.0, q2=0.0)
        new_reading = arm.step(np.array([0.5, 0.5]), noise_std=0.0)
        # With first-order lag and zero noise, the new reading is
        # alpha * command = 0.3 * 0.5 = 0.15
        self.assertAlmostEqual(new_reading[0], 0.15, places=4)
        self.assertAlmostEqual(new_reading[1], 0.15, places=4)


class TestControlLoop(unittest.TestCase):
    def test_step(self):
        sensor = SensorCell(channel_names=["q1", "q2"])
        action = ActionCell(actuator_names=["q1", "q2"])
        loop = ControlLoop(
            sensor_cell=sensor, action_cell=action,
            n_channels=2, n_actuators=2,
            target=np.array([0.5, 0.5]),
            error_threshold=0.1, stop_threshold=5.0,
        )
        # First reading at (0, 0), target at (0.5, 0.5), error ~ 0.71
        state = loop.step(np.array([0.0, 0.0]))
        self.assertIn(state.action, RobotAction)
        # State is recorded
        self.assertEqual(len(loop.history), 1)

    def test_hold_when_on_target(self):
        sensor = SensorCell(channel_names=["q1", "q2"])
        action = ActionCell(actuator_names=["q1", "q2"])
        loop = ControlLoop(
            sensor_cell=sensor, action_cell=action,
            n_channels=2, n_actuators=2,
            target=np.array([0.5, 0.5]),
            error_threshold=0.1, stop_threshold=5.0,
        )
        state = loop.step(np.array([0.5, 0.5]))
        self.assertEqual(state.action, RobotAction.HOLD)

    def test_run_iterates(self):
        sensor = SensorCell(channel_names=["q1", "q2"])
        action = ActionCell(actuator_names=["q1", "q2"])
        loop = ControlLoop(
            sensor_cell=sensor, action_cell=action,
            n_channels=2, n_actuators=2,
            target=np.array([0.0, 0.0]),
            error_threshold=0.1, stop_threshold=5.0,
        )
        readings = (np.array([0.5, 0.5]) for _ in range(10))
        states = loop.run(readings)
        self.assertEqual(len(states), 10)


class TestPickAndPlaceDemo(unittest.TestCase):
    def test_runs_end_to_end(self):
        np.random.seed(42)
        demo = PickAndPlaceDemo()
        result = demo.run(n_steps=100)
        self.assertEqual(result["n_steps"], 100)
        # Should have at least one hold (we start at home)
        self.assertGreater(result["n_holds"], 0)
        # Should not be entirely stops (we should be able to make progress)
        self.assertLess(result["n_stops"], result["n_steps"])

    def test_arm_reaches_waypoints(self):
        np.random.seed(0)
        demo = PickAndPlaceDemo()
        demo.run(n_steps=200)
        # The last reading should be near one of the waypoints
        # (waypoints cycle: home -> pick -> place -> home ...)
        last_q = np.array([demo.arm.q1, demo.arm.q2])
        dists = [
            np.linalg.norm(last_q - home_q)
            for _, home_q, _ in demo.waypoints
        ]
        # The arm should be within 0.3 of some waypoint in joint space
        self.assertTrue(
            any(d < 0.3 for d in dists),
            f"arm is at q={last_q}, distances to waypoints: {dists}"
        )


class TestCellShapeCompatibility(unittest.TestCase):
    def test_same_forecast_shape(self):
        # SensorCell and ActionCell must produce forecasts of the same shape
        sensor = SensorCell(channel_names=["a", "b", "c"], horizon=5)
        action = ActionCell(actuator_names=["a", "b", "c"], horizon=5)
        for i in range(10):
            sensor.append(np.array([float(i), float(i*2), float(i*3)]))
            action.set_target(np.array([float(i), float(i*2), float(i*3)]))
        sensor.forecast_()
        action.forecast_()
        s_forecast = sensor.read_point(0)
        a_forecast = action.read_point(0)
        self.assertEqual(s_forecast.shape, a_forecast.shape)


if __name__ == "__main__":
    unittest.main()
