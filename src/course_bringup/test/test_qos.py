"""Test the intended reliability mismatch and accepted QoS settings."""

from course_bringup.qos import pose_qos
import pytest
from rclpy.qos import DurabilityPolicy, HistoryPolicy, ReliabilityPolicy


@pytest.mark.parametrize('name, expected', [
    ('best_effort', ReliabilityPolicy.BEST_EFFORT),
    ('reliable', ReliabilityPolicy.RELIABLE),
])
def test_explicit_qos(name, expected):
    """Keep reliability selectable while depth and durability stay fixed."""
    qos = pose_qos(name)
    assert qos.reliability == expected
    assert qos.depth == 10
    assert qos.history == HistoryPolicy.KEEP_LAST
    assert qos.durability == DurabilityPolicy.VOLATILE


@pytest.mark.parametrize('value', ['invalid', '', 'BEST_EFFORT', None])
def test_invalid_reliability(value):
    """Reject misspelled or missing policy names instead of guessing."""
    with pytest.raises(ValueError):
        pose_qos(value)
