"""Verify actual pose relay delivery and mismatch with ROS entities."""

import time

from course_bringup.pose_listener import PoseListener
from course_bringup.pose_relay import PoseRelay
from course_bringup.qos import pose_qos
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from turtlesim.msg import Pose


def test_relay_and_reliability_delivery():
    """Forward identical data to best effort while reliable receives none."""
    rclpy.init()
    executor = SingleThreadedExecutor()
    source = Node('pose_test_source', namespace='/qos_test')
    relay = PoseRelay(namespace='/qos_test')
    bad = PoseListener(namespace='/qos_test', parameter_overrides=[
        Parameter('subscriber_reliability', value='reliable'),
    ])
    good = PoseListener(namespace='/qos_test')
    publisher = source.create_publisher(Pose, 'turtle1/pose', 10)
    received = []
    subscription = source.create_subscription(
        Pose, 'sensor_pose', received.append, pose_qos('best_effort'),
    )
    pose = Pose()
    pose.x, pose.y, pose.theta = 3.0, 4.0, 0.25
    timer = source.create_timer(0.02, lambda: publisher.publish(pose))
    nodes = [source, relay, bad, good]
    try:
        for node in nodes:
            executor.add_node(node)
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.02)
        assert good.received_count > 0
        assert bad.received_count == 0
        assert received
        assert received[-1] == pose
        assert subscription.topic_name == '/qos_test/sensor_pose'
        assert timer.timer_period_ns == 20_000_000
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        rclpy.shutdown()
