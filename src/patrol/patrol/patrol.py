"""Publish turtle velocity commands using a pose subscription and timer."""

from geometry_msgs.msg import Twist
from patrol.controller import command_from_pose
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


class Patrol(Node):
    """Store the latest pose and publish a command every 0.1 seconds."""

    def __init__(self):
        """Create the subscription, publisher and timer."""
        super().__init__('patrol')
        self.latest_pose = None
        self.pose_subscription = self.create_subscription(
            Pose,
            '/turtle1/pose',
            self.pose_callback,
            10,
        )
        self.command_publisher = self.create_publisher(
            Twist,
            'cmd_vel',
            10,
        )
        self.command_timer = self.create_timer(
            0.1,
            self.timer_callback,
        )

    def pose_callback(self, message):
        """Save the latest pose message."""
        self.latest_pose = message

    def timer_callback(self):
        """Choose and publish the current velocity command."""
        command = command_from_pose(self.latest_pose)
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
