"""Choose a turtle velocity command from the latest pose and settings."""

from geometry_msgs.msg import Twist


def command_from_pose(pose, linear_speed=0.5, turn_rate=0.3):
    """Return zero before the first pose, then use the configured speeds."""
    command = Twist()
    if pose is not None:
        command.linear.x = float(linear_speed)
        command.angular.z = float(turn_rate)
    return command
