"""Validate patrol parameters without changing ROS state."""

import math


DEFAULT_PARAMETERS = {
    'linear_speed': 0.5,
    'turn_rate': 0.3,
    'publish_hz': 10.0,
}
PARAMETER_LIMITS = {
    'linear_speed': (0.0, 1.0),
    'turn_rate': (-1.0, 1.0),
    'publish_hz': (1.0, 30.0),
}


def parameter_error(values):
    """Return a rejection reason, or an empty string for valid values."""
    for name, (minimum, maximum) in PARAMETER_LIMITS.items():
        value = values[name]
        if type(value) not in (int, float) or not math.isfinite(value):
            return f'{name} must be a finite number'
        if not minimum <= value <= maximum:
            return f'{name} must be in [{minimum}, {maximum}]'
    return ''
