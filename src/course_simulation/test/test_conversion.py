"""Verify safety bounds and lossless odometry normalization."""

from copy import deepcopy
import math

from ackermann_msgs.msg import AckermannDriveStamped
from course_simulation.conversion import drive_to_twist, normalize_odometry
from nav_msgs.msg import Odometry
import pytest


def command(speed=1.0, steering=0.0, stamp=10):
    """Create a finite command at a known simulation timestamp."""
    message = AckermannDriveStamped()
    message.header.stamp.sec = stamp
    message.drive.speed = float(speed)
    message.drive.steering_angle = float(steering)
    return message


@pytest.mark.parametrize('speed,angle,v,delta', [
    (0.5, 0, 0.5, 0), (0.8, 0.3, 0.8, 0.3), (0.8, -0.3, 0.8, -0.3),
    (0, 0.45, 0, 0.45), (-1, 0, 0, 0), (9, 9, 1.2, 0.45),
    (9, -9, 1.2, -0.45),
])
def test_drive(speed, angle, v, delta):
    """Check straight, both turns, zero speed and saturation."""
    result, reason = drive_to_twist(command(speed, angle), 10_100_000_000)
    assert reason == 'ok'
    assert result.linear.x == pytest.approx(v)
    assert result.angular.z == pytest.approx(v * math.tan(delta) / 0.8)
    assert result.linear.y == result.linear.z == result.angular.x == result.angular.y == 0


@pytest.mark.parametrize('field', [
    'speed', 'steering_angle', 'steering_angle_velocity', 'acceleration', 'jerk',
])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_non_finite(field, value):
    """Any invalid drive field stops, not only the two fields used in kinematics."""
    message = command()
    setattr(message.drive, field, value)
    result, reason = drive_to_twist(message, 10_100_000_000)
    assert reason == 'non_finite'
    assert result.linear.x == result.angular.z == 0


@pytest.mark.parametrize('now,reason', [
    (10_250_000_000, 'ok'), (10_250_000_001, 'stale'),
    (9_000_000_000, 'future_stamp'), (0, 'no_clock'),
])
def test_age(now, reason):
    """Use the message stamp, including the exact stale boundary."""
    result, actual = drive_to_twist(command(), now)
    assert actual == reason
    if reason != 'ok':
        assert result.linear.x == result.angular.z == 0


def odometry():
    """Create nontrivial data so accidental field loss is visible."""
    message = Odometry()
    message.header.frame_id = 'course_ackermann/odom'
    message.child_frame_id = 'course_ackermann/base_link'
    message.header.stamp.sec = 12
    message.header.stamp.nanosec = 345
    message.pose.pose.position.x = 1.2
    message.pose.pose.orientation.z = math.sin(0.1)
    message.pose.pose.orientation.w = math.cos(0.1)
    message.twist.twist.linear.x = 0.4
    message.pose.covariance = [float(i) for i in range(36)]
    message.twist.covariance = [i / 10.0 for i in range(36)]
    return message


def test_odometry_preserved():
    """Preserve stamps, pose, twist, covariances and the original message."""
    original = odometry()
    before = deepcopy(original)
    result, transform = normalize_odometry(original)
    assert original == before
    assert result.header.frame_id == 'odom' and result.child_frame_id == 'base_link'
    assert result.header.stamp == original.header.stamp == transform.header.stamp
    assert result.pose == original.pose and result.twist == original.twist
    assert transform.header.frame_id == 'odom' and transform.child_frame_id == 'base_link'
    assert transform.transform.translation.x == result.pose.pose.position.x
    assert transform.transform.rotation == result.pose.pose.orientation


@pytest.mark.parametrize('field,value', [
    ('header.frame_id', 'odom'), ('child_frame_id', 'base_link'),
    ('header.frame_id', 'other/odom'),
    ('pose.pose.position.x', float('nan')),
    ('twist.twist.angular.z', float('inf')),
    ('pose.pose.orientation.w', float('nan')),
])
def test_odometry_rejected(field, value):
    """Reject already normalized frames, unexpected prefixes and nonfinite data."""
    message = odometry()
    target = message
    names = field.split('.')
    for name in names[:-1]:
        target = getattr(target, name)
    setattr(target, names[-1], value)
    with pytest.raises(ValueError):
        normalize_odometry(message)


def test_bad_covariance():
    """Do not let invalid covariance enter odometry or the matching tf."""
    message = odometry()
    message.twist.covariance[7] = float('nan')
    with pytest.raises(ValueError):
        normalize_odometry(message)
