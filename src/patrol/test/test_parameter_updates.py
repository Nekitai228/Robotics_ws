"""Verify accepted and rejected updates against a real ROS node."""

from patrol.patrol import Patrol
import pytest
import rclpy
from rclpy.parameter import Parameter


@pytest.fixture
def node():
    """Create and clean up an independent patrol node for each test."""
    rclpy.init()
    patrol = Patrol(enable_rosout=False)
    try:
        yield patrol
    finally:
        patrol.destroy_node()
        rclpy.shutdown()


def test_frequency_change_replaces_timer(node):
    """Apply 10 to 5 Hz and keep exactly one active timer."""
    old_timer = node.command_timer
    result = node.set_parameters_atomically([
        Parameter('publish_hz', value=5.0),
    ])
    assert result.successful
    assert node.get_parameter('publish_hz').value == 5.0
    assert node.settings['publish_hz'] == 5.0
    assert node.command_timer is not old_timer
    assert node.command_timer.timer_period_ns == 200_000_000
    assert list(node.timers) == [node.command_timer]


@pytest.mark.parametrize('frequency', [0.0, -1.0, float('nan')])
def test_bad_frequency_preserves_active_state(node, frequency):
    """Reject invalid input and retain the previous parameter and timer."""
    node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])
    old_timer = node.command_timer
    old_settings = node.settings.copy()
    result = node.set_parameters_atomically([
        Parameter('publish_hz', value=frequency),
    ])
    assert not result.successful
    assert result.reason
    assert node.get_parameter('publish_hz').value == 5.0
    assert node.settings == old_settings
    assert node.command_timer is old_timer
    assert not old_timer.is_canceled()
    assert list(node.timers) == [old_timer]


def test_mixed_invalid_update_is_atomic(node):
    """Keep the old speeds too when a batch contains a bad frequency."""
    old_timer = node.command_timer
    result = node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8),
        Parameter('publish_hz', value=0.0),
    ])
    assert not result.successful
    assert node.get_parameter('linear_speed').value == 0.5
    assert node.settings['linear_speed'] == 0.5
    assert node.command_timer is old_timer


def test_speed_change_keeps_timer(node):
    """Update both speeds without replacing an unchanged-frequency timer."""
    old_timer = node.command_timer
    result = node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8),
        Parameter('turn_rate', value=-0.5),
    ])
    assert result.successful
    assert node.settings['linear_speed'] == 0.8
    assert node.settings['turn_rate'] == -0.5
    assert node.command_timer is old_timer
