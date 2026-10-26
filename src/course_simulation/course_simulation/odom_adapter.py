"""Own normalized odometry and the single dynamic odom to base_link tf."""

import signal

from course_simulation.conversion import normalize_odometry
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


class OdomAdapter(Node):
    """Normalize frames exactly once, preserving all measurements and stamps."""

    def __init__(self):
        """Create reliable odometry endpoints and the sole dynamic broadcaster."""
        super().__init__('odom_adapter')
        incoming = self.declare_parameter('raw_odom_topic', '/vehicle/odom_gz').value
        outgoing = self.declare_parameter('odom_topic', '/vehicle/odom').value
        self.publisher = self.create_publisher(Odometry, outgoing, 10)
        self.broadcaster = TransformBroadcaster(self)
        self.subscription = self.create_subscription(Odometry, incoming, self.receive, 10)
        self.last_error = None

    def receive(self, message):
        """Reject unexpected frames or invalid numbers without publishing tf."""
        try:
            result, transform = normalize_odometry(message)
        except ValueError as error:
            if str(error) != self.last_error:
                self.get_logger().warning('odometry rejected: ' + str(error))
                self.last_error = str(error)
            return
        self.last_error = None
        self.publisher.publish(result)
        self.broadcaster.sendTransform(transform)


def main(args=None):
    """Spin until shutdown and release the node cleanly."""
    rclpy.init(args=args)
    node = OdomAdapter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
