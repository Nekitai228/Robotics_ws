"""Observe sensor poses with reliability selected at node startup."""

import signal

from course_bringup.qos import pose_qos
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseListener(Node):
    """Count incoming poses to make a QoS mismatch observable."""

    def __init__(self, **kwargs):
        """Create a subscription using the requested reliability policy."""
        super().__init__('pose_listener', **kwargs)
        reliability = self.declare_parameter(
            'subscriber_reliability', 'best_effort',
        ).value
        try:
            qos = pose_qos(reliability)
        except ValueError:
            self.destroy_node()
            raise
        self.received_count = 0
        self.subscription = self.create_subscription(
            Pose, 'sensor_pose', self.pose_callback, qos,
        )
        self.get_logger().info(f'Subscriber reliability: {reliability}')

    def pose_callback(self, message):
        """Count actual received messages and log occasional samples."""
        self.received_count += 1
        if self.received_count == 1 or self.received_count % 50 == 0:
            self.get_logger().info(
                f'Received pose #{self.received_count}: '
                f'x={message.x:.3f}, y={message.y:.3f}',
            )


def main(args=None):
    """Run the subscriber until interrupted."""
    rclpy.init(args=args)
    node = PoseListener()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
