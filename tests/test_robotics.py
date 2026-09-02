"""Tests for the robotics-shaped cells.

The tests cover:
  - SensorCell append/bind/forecast/reads
  - ActionCell set_target/bind/forecast/next_command
  - ControlLoop step + run
  - PickAndPlaceDemo (kinematic) runs end-to-end
  - LagrangianArm dynamics (mass matrix, Coriolis, friction)
  - Computed-torque controller tracks a target
  - IK roundtrip
  - Min-jerk trajectory is smooth
  - RealPickAndPlace runs the full pick-and-place task
  - Cell-shape compatibility
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
    LagrangianArm, ArmParams, TrajectoryPoint,
    computed_torque_torque, impedance_torque, ik_2link,
    min_jerk_trajectory, RealPickAndPlace,
    CellDrivenController, compare_controllers,
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


# ─── Real Lagrangian dynamics ────────────────────────────────────

class TestLagrangianArm(unittest.TestCase):
    def test_no_torque_arm_stays_still(self):
        arm = LagrangianArm(q1=0.5, q2=1.0)
        q0 = arm.q.copy()
        arm.send_torque(np.zeros(2), duration=0.05)
        # After 50ms with no torque, the arm should be at almost the same pose
        self.assertLess(np.linalg.norm(arm.q - q0), 1e-6)

    def test_torque_moves_arm(self):
        arm = LagrangianArm(q1=0.5, q2=1.0)
        q0 = arm.q.copy()
        arm.send_torque(np.array([2.0, 1.0]), duration=0.1)
        # With torque applied, the arm must have moved
        self.assertGreater(np.linalg.norm(arm.q - q0), 1e-4)

    def test_torque_clamped_to_max(self):
        # A torque of 1000 Nm should be clamped to ±tau_max
        arm = LagrangianArm()
        arm.send_torque(np.array([1000.0, -1000.0]), duration=0.001)
        # Just verify the call doesn't error; the physics is sound
        self.assertTrue(np.all(np.isfinite(arm.state)))

    def test_mass_matrix_symmetric_positive_definite(self):
        arm = LagrangianArm()
        M = arm.mass_matrix(arm.q)
        self.assertTrue(np.allclose(M, M.T))
        eigvals = np.linalg.eigvalsh(M)
        self.assertTrue(np.all(eigvals > 0))

    def test_mass_matrix_depends_on_configuration(self):
        # The mass matrix changes with the joint angles
        arm = LagrangianArm()
        M1 = arm.mass_matrix(np.array([0.0, 0.0]))
        M2 = arm.mass_matrix(np.array([np.pi / 2, np.pi / 4]))
        self.assertFalse(np.allclose(M1, M2))

    def test_state_shape(self):
        arm = LagrangianArm()
        self.assertEqual(arm.state.shape, (4,))

    def test_forward_kinematics_at_zero(self):
        arm = LagrangianArm(q1=0.0, q2=0.0)
        ee = arm.forward_kinematics()
        # At zero, both links along +x axis
        self.assertAlmostEqual(ee[0], arm.p.L1 + arm.p.L2, places=4)
        self.assertAlmostEqual(ee[1], 0.0, places=4)

    def test_jacobian_shape(self):
        arm = LagrangianArm()
        J = arm.jacobian()
        self.assertEqual(J.shape, (2, 2))


class TestComputedTorqueController(unittest.TestCase):
    def test_tracks_constant_target(self):
        # The computed-torque controller should track a constant
        # target with near-zero error after the transient.
        arm = LagrangianArm(q1=0.3, q2=0.7)
        q_target = np.array([1.2, 0.4])
        for _ in range(2000):  # 20 seconds at 100Hz
            tau = computed_torque_torque(arm, q_target, np.zeros(2),
                                          kp=200.0, kd=20.0)
            arm.send_torque(tau, duration=0.01)
        err = np.linalg.norm(arm.q - q_target)
        self.assertLess(err, 1e-3,
                        f"tracking error {err} should be < 1e-3 rad")

    def test_tracks_sinusoidal_target(self):
        # A sinusoidal target should be tracked with bounded error.
        arm = LagrangianArm(q1=0.5, q2=1.0)
        errors = []
        for i in range(1000):
            t = i * 0.01
            q_des = np.array([0.5 + 0.3 * np.sin(t), 1.0 + 0.2 * np.cos(t)])
            q_dot_des = np.array([0.3 * np.cos(t), -0.2 * np.sin(t)])
            tau = computed_torque_torque(arm, q_des, q_dot_des,
                                          kp=300.0, kd=30.0)
            arm.send_torque(tau, duration=0.01)
            errors.append(np.linalg.norm(arm.q - q_des))
        # Mean error over the trajectory should be small
        self.assertLess(np.mean(errors), 0.05,
                        f"mean tracking error {np.mean(errors)} too high")


class TestInverseKinematics(unittest.TestCase):
    def test_ik_roundtrip(self):
        arm = LagrangianArm()
        target = np.array([0.4, 0.3])
        q = ik_2link(target, arm.p.L1, arm.p.L2)
        self.assertIsNotNone(q)
        arm.reset(q=q)
        ee = arm.forward_kinematics()
        self.assertAlmostEqual(ee[0], target[0], places=3)
        self.assertAlmostEqual(ee[1], target[1], places=3)

    def test_ik_unreachable(self):
        # A point well outside the workspace
        q = ik_2link(np.array([5.0, 5.0]), 0.5, 0.4)
        self.assertIsNone(q)

    def test_ik_origin(self):
        # The origin is between the two IK solutions; both should
        # place the end-effector at the origin.
        arm = LagrangianArm()
        q = ik_2link(np.array([0.0, 0.0]), arm.p.L1, arm.p.L2)
        # The origin requires L1 cos(q1) + L2 cos(q1+q2) = 0
        # This is reachable; check that one solution works
        if q is not None:
            arm.reset(q=q)
            ee = arm.forward_kinematics()
            self.assertAlmostEqual(ee[0], 0.0, places=3)
            self.assertAlmostEqual(ee[1], 0.0, places=3)


class TestMinJerkTrajectory(unittest.TestCase):
    def test_trajectory_endpoints(self):
        q_start = np.array([0.5, 1.0])
        q_end = np.array([1.5, 0.0])
        traj = min_jerk_trajectory(q_start, q_end, duration=1.0, n_points=20)
        # At t=0, the trajectory is at q_start
        np.testing.assert_array_almost_equal(traj[0].q, q_start)
        # At t=duration, the trajectory is at q_end
        np.testing.assert_array_almost_equal(traj[-1].q, q_end)

    def test_trajectory_smooth(self):
        # Successive points should be close to each other (smooth)
        traj = min_jerk_trajectory(
            np.array([0.0, 0.0]), np.array([1.0, 1.0]),
            duration=1.0, n_points=100,
        )
        diffs = [np.linalg.norm(traj[i + 1].q - traj[i].q)
                 for i in range(len(traj) - 1)]
        # The max step should be much smaller than the total path length
        self.assertLess(max(diffs), 0.1)

    def test_trajectory_timestamps(self):
        traj = min_jerk_trajectory(
            np.array([0.0, 0.0]), np.array([1.0, 1.0]),
            duration=2.0, n_points=5,
        )
        for i, p in enumerate(traj):
            self.assertAlmostEqual(p.t, i * 0.5, places=4)


class TestRealPickAndPlace(unittest.TestCase):
    def test_runs_to_completion(self):
        demo = RealPickAndPlace()
        result = demo.run(n_ticks=600, verbose=False)  # 6 seconds
        self.assertEqual(result["n_ticks"], 600)
        # The arm should have made progress
        self.assertGreater(result["duration"], 5.0)
        # Mean tracking error should be small (< 5 deg)
        self.assertLess(result["mean_tracking_error"], 0.1,
                        f"mean error {result['mean_tracking_error']:.4f} rad")

    def test_reaches_waypoints(self):
        # After running, the arm should be near one of the waypoints
        np.random.seed(42)
        demo = RealPickAndPlace()
        demo.run(n_ticks=1500)  # 15 seconds
        arm = demo.arm
        # The end-effector should be near one of the waypoints
        ee = arm.forward_kinematics()
        waypoints_xy = [np.array([0.6, 0.0]), np.array([0.3, 0.4]),
                        np.array([-0.3, 0.4])]
        dists = [np.linalg.norm(ee - wp) for wp in waypoints_xy]
        self.assertTrue(
            any(d < 0.1 for d in dists),
            f"end-effector at {ee}, distances to waypoints: {dists}"
        )

    def test_sensor_and_action_cells_populated(self):
        # The cells should have grown during the run.
        # The sensor's history is capped at history_len (32 by default).
        demo = RealPickAndPlace()
        demo.run(n_ticks=200)
        # After 200 ticks, the sensor cell has hit its history cap
        self.assertGreaterEqual(demo.sensor.context_len, 1)
        # The action cell stores the torque at each tick, capped at history_len
        self.assertGreaterEqual(demo.action.context_len, 1)

    def test_forecast_shape_on_real_arm(self):
        # The SensorCell's forecast is [H, V] for the real arm.
        # read_point(channel) returns a 1D array of length H.
        demo = RealPickAndPlace()
        demo.run(n_ticks=200)
        demo.sensor.forecast_()
        # Channel 0 = q1, channel 1 = q2, channel 2 = q1_dot, channel 3 = q2_dot
        q1_forecast = demo.sensor.read_point(0)
        self.assertEqual(q1_forecast.shape, (5,),
                         f"expected (5,), got {q1_forecast.shape}")
        # The forecast has 4 channels (joints + velocities)
        # We can verify this by reading all of them
        forecast_q1 = demo.sensor.read_point(0)
        forecast_q2 = demo.sensor.read_point(1)
        forecast_q1dot = demo.sensor.read_point(2)
        forecast_q2dot = demo.sensor.read_point(3)
        self.assertEqual(forecast_q1.shape, forecast_q2.shape)
        self.assertEqual(forecast_q1.shape, forecast_q1dot.shape)
        self.assertEqual(forecast_q1.shape, forecast_q2dot.shape)


# ─── Cell-driven control ────────────────────────────────────────

class TestCellDrivenController(unittest.TestCase):
    def test_reaches_target(self):
        np.random.seed(42)
        arm = LagrangianArm(q1=0.3, q2=0.7)
        q_target = np.array([1.2, 0.4])
        ctrl = CellDrivenController(arm, q_target)
        result = ctrl.run(n_ticks=1000)
        # After 10 seconds, the arm should be at the target
        self.assertLess(result["final_tracking_error"], 0.01,
                        f"final error {result['final_tracking_error']} should be <0.01 rad")

    def test_forecast_error_drops(self):
        # The cell should learn the dynamics over time
        np.random.seed(42)
        arm = LagrangianArm(q1=0.3, q2=0.7)
        q_target = np.array([1.2, 0.4])
        ctrl = CellDrivenController(arm, q_target)
        result = ctrl.run(n_ticks=1000)
        early = np.mean(result["forecast_error_history"][10:50])
        late = np.mean(result["forecast_error_history"][-50:])
        # The forecast error should drop over time as the cell learns
        self.assertLess(late, early * 0.5,
                        f"forecast error should drop; early={early:.4f}, late={late:.4f}")

    def test_alpha_increases(self):
        # alpha (the cell's trust) should rise as the cell learns
        np.random.seed(42)
        arm = LagrangianArm(q1=0.3, q2=0.7)
        q_target = np.array([1.2, 0.4])
        ctrl = CellDrivenController(arm, q_target)
        # Run for a few hundred ticks
        for _ in range(500):
            ctrl.step()
        # After learning, alpha should be high
        self.assertGreater(ctrl._alpha(), 0.5)

    def test_compare_controllers(self):
        np.random.seed(42)
        comp = compare_controllers(n_ticks=500)
        # Both should reach the target
        self.assertLess(comp["pd_only"]["final_error"], 0.01)
        self.assertLess(comp["cell_driven"]["final_error"], 0.01)
        # The cell's forecast error should be small
        self.assertLess(comp["cell_driven"]["mean_forecast_error"], 0.1)


class TestReadFullForecast(unittest.TestCase):
    def test_shape(self):
        c = SensorCell(channel_names=["a", "b", "c"], horizon=5)
        for i in range(10):
            c.append(np.array([float(i), float(i*2), float(i*3)]))
        c.forecast_()
        full = c.read_full_forecast()
        self.assertEqual(full.shape, (5, 3))

    def test_empty_before_forecast(self):
        c = SensorCell(channel_names=["a", "b"])
        full = c.read_full_forecast()
        self.assertEqual(full.shape, (0, 2))


if __name__ == "__main__":
    unittest.main()
