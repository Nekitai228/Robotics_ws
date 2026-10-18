"""Test parameter boundaries, non-finite values and normal updates."""

from patrol.parameters import DEFAULT_PARAMETERS, parameter_error
import pytest


@pytest.mark.parametrize('frequency', [1.0, 5.0, 10.0, 30.0])
def test_valid_frequency(frequency):
    """Accept normal frequencies, including the required 10 to 5 change."""
    values = dict(DEFAULT_PARAMETERS, publish_hz=frequency)
    assert parameter_error(values) == ''


@pytest.mark.parametrize('name, value', [
    ('publish_hz', 0.0),
    ('publish_hz', -1.0),
    ('publish_hz', 31.0),
    ('publish_hz', float('nan')),
    ('publish_hz', float('inf')),
    ('publish_hz', float('-inf')),
    ('linear_speed', -0.1),
    ('linear_speed', 1.1),
    ('linear_speed', float('nan')),
    ('turn_rate', -1.1),
    ('turn_rate', 1.1),
    ('turn_rate', float('inf')),
    ('publish_hz', True),
    ('publish_hz', '5.0'),
])
def test_invalid_parameter(name, value):
    """Reject invalid values without modifying the candidate dictionary."""
    values = dict(DEFAULT_PARAMETERS, **{name: value})
    assert parameter_error(values)
    assert values[name] is value


@pytest.mark.parametrize('speed, turn', [(0.0, -1.0), (1.0, 1.0)])
def test_valid_speed_boundaries(speed, turn):
    """Accept both endpoints of the speed and turn ranges."""
    values = dict(DEFAULT_PARAMETERS, linear_speed=speed, turn_rate=turn)
    assert parameter_error(values) == ''
