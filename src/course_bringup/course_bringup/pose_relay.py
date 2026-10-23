"""Forward turtle poses to a relative topic using best-effort reliability."""

import signal

from course_bringup.qos import pose_qos
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseRelay(Node):
    """Keep the input pose unchanged and publish it as a sensor stream."""

    def __init__(self, **kwargs):
        """Create relative input and output topics for launch remapping."""
        super().__init__('pose_relay', **kwargs)
        self.publisher = self.create_publisher(
            Pose, 'sensor_pose', pose_qos('best_effort'),
        )
        self.subscription = self.create_subscription(
            Pose, 'turtle1/pose', self.pose_callback, 10,
        )

    def pose_callback(self, message):
        """Forward the original pose message without changing its values."""
        self.publisher.publish(message)


def main(args=None):
    """Run the relay until interrupted."""
    rclpy.init(args=args)
    node = PoseRelay()
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
