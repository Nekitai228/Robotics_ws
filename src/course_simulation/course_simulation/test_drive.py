"""Publish a bounded test command with a fresh stamp from the ROS clock."""

import signal

from ackermann_msgs.msg import AckermannDriveStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class TestDrive(Node):
    """Provide the temporary source for /drive/safe before the supervisor exists."""

    __test__ = False

    def __init__(self):
        """Configure a constant speed and steering angle, published at 20 Hz."""
        super().__init__('test_drive')
        self.speed = float(self.declare_parameter('speed', 0.3).value)
        self.steering = float(self.declare_parameter('steering', 0.0).value)
        topic = self.declare_parameter('drive_topic', '/drive/safe').value
        self.publisher = self.create_publisher(AckermannDriveStamped, topic, 10)
        self.timer = self.create_timer(0.05, self.publish_command)

    def publish_command(self):
        """Read simulation time anew for each command instead of reusing a stamp."""
        if self.get_clock().now().nanoseconds <= 0:
            return
        message = AckermannDriveStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'base_link'
        message.drive.speed = self.speed
        message.drive.steering_angle = self.steering
        self.publisher.publish(message)


def main(args=None):
    """Spin until shutdown and release the node cleanly."""
    rclpy.init(args=args)
    node = TestDrive()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
