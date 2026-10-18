"""Publish turtle commands with validated parameters and a single timer."""

from geometry_msgs.msg import Twist
from patrol.controller import command_from_pose
from patrol.parameters import DEFAULT_PARAMETERS, parameter_error
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


class Patrol(Node):
    """Store the latest pose and publish commands at a configurable rate."""

    def __init__(self, **kwargs):
        """Declare validated settings and create ROS communication objects."""
        super().__init__('patrol', **kwargs)
        for name, default in DEFAULT_PARAMETERS.items():
            self.declare_parameter(name, default)
        self.settings = {
            name: self.get_parameter(name).value
            for name in DEFAULT_PARAMETERS
        }
        error = parameter_error(self.settings)
        if error:
            self.destroy_node()
            raise ValueError(error)
        self.latest_pose = None
        self.pose_subscription = self.create_subscription(
            Pose, '/turtle1/pose', self.pose_callback, 10,
        )
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.command_timer = self.create_timer(
            1.0 / self.settings['publish_hz'], self.timer_callback,
        )
        self.add_on_set_parameters_callback(self.validate_update)
        self.add_post_set_parameters_callback(self.apply_update)

    def candidate_settings(self, parameters):
        """Merge an update into a copy of the current active settings."""
        candidate = self.settings.copy()
        for parameter in parameters:
            if parameter.name in candidate:
                candidate[parameter.name] = parameter.value
        return candidate

    def validate_update(self, parameters):
        """Validate the entire candidate without changing state or timers."""
        candidate = self.candidate_settings(parameters)
        # Deliberate PR04 defect: do not validate the requested frequency.
        candidate['publish_hz'] = self.settings['publish_hz']
        error = parameter_error(candidate)
        return SetParametersResult(successful=not error, reason=error)

    def apply_update(self, parameters):
        """Apply accepted values and replace the timer only if needed."""
        candidate = self.candidate_settings(parameters)
        if candidate['publish_hz'] != self.settings['publish_hz']:
            self.destroy_timer(self.command_timer)
            self.command_timer = self.create_timer(
                1.0 / candidate['publish_hz'], self.timer_callback,
            )
        self.settings = candidate

    def pose_callback(self, message):
        """Save the latest pose message."""
        self.latest_pose = message

    def timer_callback(self):
        """Choose a command using the currently accepted speeds."""
        command = command_from_pose(
            self.latest_pose,
            self.settings['linear_speed'],
            self.settings['turn_rate'],
        )
        self.command_publisher.publish(command)


def main(args=None):
    """Initialize ROS, process callbacks and release resources."""
    rclpy.init(args=args)
    node = Patrol()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
