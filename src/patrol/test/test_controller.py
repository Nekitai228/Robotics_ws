"""Test command selection without running a ROS node."""

from patrol.controller import command_from_pose
from turtlesim.msg import Pose


def test_no_pose_produces_zero_command():
    """Check all velocity fields before the first pose."""
    command = command_from_pose(None)

    assert command.linear.x == 0.0
    assert command.linear.y == 0.0
    assert command.linear.z == 0.0
    assert command.angular.x == 0.0
    assert command.angular.y == 0.0
    assert command.angular.z == 0.0


def test_pose_produces_patrol_command():
    """Check the command after receiving an ordinary pose."""
    pose = Pose()
    pose.x = 5.0
    pose.y = 5.0
    pose.theta = 0.5

    command = command_from_pose(pose)

    assert command.linear.x == 0.5
    assert command.linear.y == 0.0
    assert command.linear.z == 0.0
    assert command.angular.x == 0.0
    assert command.angular.y == 0.0
    assert command.angular.z == 0.3
