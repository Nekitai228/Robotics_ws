"""Guard /drive/safe and convert the central steering angle to body yaw rate."""

import signal

from ackermann_msgs.msg import AckermannDriveStamped
from course_simulation.conversion import drive_to_twist
from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class DriveAdapter(Node):
    """Publish zero when commands are absent, rejected or stale in simulation time."""

    def __init__(self):
        """Create reliable endpoints and a simulation time watchdog."""
        super().__init__('drive_adapter')
        incoming = self.declare_parameter('drive_topic', '/drive/safe').value
        outgoing = self.declare_parameter('command_topic', '/vehicle/gz_cmd_vel').value
        self.publisher = self.create_publisher(Twist, outgoing, 10)
        self.subscription = self.create_subscription(
            AckermannDriveStamped, incoming, self.receive, 10)
        self.command = None
        self.reason = None
        self.timer = self.create_timer(0.05, self.publish_current)

    def receive(self, message):
        """Reject invalid input immediately and forget the previous command."""
        _, reason = drive_to_twist(message, self.get_clock().now().nanoseconds)
        self.command = message if reason == 'ok' else None
        self.publish_current(reason if reason != 'ok' else None)

    def publish_current(self, rejection=None):
        """Never repeat a command after its header exceeds the allowed age."""
        if self.command is None:
            velocity, reason = Twist(), rejection or 'no_command'
        else:
            velocity, reason = drive_to_twist(
                self.command, self.get_clock().now().nanoseconds)
            if reason != 'ok':
                self.command = None
        self.publisher.publish(velocity)
        if reason != self.reason:
            self.get_logger().info('drive: ' + reason)
            self.reason = reason


def main(args=None):
    """Spin until shutdown and release the node cleanly."""
    rclpy.init(args=args)
    node = DriveAdapter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
