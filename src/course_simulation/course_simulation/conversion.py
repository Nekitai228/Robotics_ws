"""Pure contracts for the drive and odometry boundaries."""

from copy import deepcopy
import math

from geometry_msgs.msg import TransformStamped, Twist


def drive_to_twist(message, now_ns):
    """Return bounded body velocities or a zero command with a refusal reason."""
    result = Twist()
    fields = [message.drive.speed, message.drive.steering_angle,
              message.drive.steering_angle_velocity, message.drive.acceleration,
              message.drive.jerk]
    if not all(math.isfinite(value) for value in fields):
        return result, 'non_finite'
    stamp = message.header.stamp.sec * 10**9 + message.header.stamp.nanosec
    age = (now_ns - stamp) / 1e9
    if now_ns <= 0:
        return result, 'no_clock'
    if age > 0.25:
        return result, 'stale'
    if age < -1e-6:
        return result, 'future_stamp'
    speed = min(max(message.drive.speed, 0.0), 1.2)
    steering = min(max(message.drive.steering_angle, -0.45), 0.45)
    result.linear.x = speed
    result.angular.z = speed * math.tan(steering) / 0.8
    return result, 'ok'


def normalize_odometry(message):
    """Copy data unchanged except frames and create the matching dynamic tf."""
    if (message.header.frame_id != 'course_ackermann/odom' or
            message.child_frame_id != 'course_ackermann/base_link'):
        raise ValueError('unexpected_frames')
    pose = message.pose.pose
    twist = message.twist.twist
    values = [pose.position.x, pose.position.y, pose.position.z,
              pose.orientation.x, pose.orientation.y, pose.orientation.z,
              pose.orientation.w, twist.linear.x, twist.linear.y, twist.linear.z,
              twist.angular.x, twist.angular.y, twist.angular.z]
    values += list(message.pose.covariance) + list(message.twist.covariance)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('non_finite')
    if sum(v*v for v in values[3:7]) < 1e-12:
        raise ValueError('zero_quaternion')
    result = deepcopy(message)
    result.header.frame_id = 'odom'
    result.child_frame_id = 'base_link'
    transform = TransformStamped()
    transform.header = deepcopy(result.header)
    transform.child_frame_id = 'base_link'
    transform.transform.translation.x = pose.position.x
    transform.transform.translation.y = pose.position.y
    transform.transform.translation.z = pose.position.z
    transform.transform.rotation = deepcopy(pose.orientation)
    return result, transform
