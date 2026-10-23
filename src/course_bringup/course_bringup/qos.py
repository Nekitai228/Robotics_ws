"""Build explicit and validated reliability profiles for the QoS experiment."""

from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)


def pose_qos(reliability):
    """Return a volatile keep-last profile for a supported reliability name."""
    policies = {
        'best_effort': ReliabilityPolicy.BEST_EFFORT,
        'reliable': ReliabilityPolicy.RELIABLE,
    }
    if reliability not in policies:
        raise ValueError('subscriber_reliability must be reliable or best_effort')
    return QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=policies[reliability],
        durability=DurabilityPolicy.VOLATILE,
    )
