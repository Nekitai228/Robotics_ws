"""Check geometry, physical values and the semantic sensor parent contract."""

import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import xacro

SOURCE = Path(os.environ.get('COURSE_XACRO',
              Path(__file__).parents[1] / 'urdf/vehicle.urdf.xacro'))


@pytest.fixture
def robot():
    """Expand the actual description, including macro expressions."""
    return ET.fromstring(xacro.process_file(str(SOURCE)).toxml())


def test_sensor_parents(robot):
    """A structurally valid tree must also have the correct sensor parent."""
    for name in ('camera', 'lidar', 'imu'):
        joint = robot.find(f"joint[@name='{name}_joint']")
        assert joint.find('parent').get('link') == 'base_link', name
        assert joint.find('child').get('link') == name + '_link'
        assert [float(v) for v in joint.find('origin').get('xyz').split()] == [0.28, 0, 0.38]


def test_tree(robot):
    """Require one connected, acyclic graph with one parent per child."""
    links = [link.get('name') for link in robot.findall('link')]
    assert len(links) == len(set(links)) == 10
    parent = {}
    for joint in robot.findall('joint'):
        child = joint.find('child').get('link')
        assert child not in parent
        parent[child] = joint.find('parent').get('link')
        assert child in links and parent[child] in links
    assert set(links) - parent.keys() == {'base_link'}
    for link in links:
        visited = set()
        while link in parent:
            assert link not in visited
            visited.add(link)
            link = parent[link]
        assert link == 'base_link'


def test_physical_values(robot):
    """Mass and principal inertias are finite, positive and satisfy triangles."""
    for link in robot.findall('link'):
        mass = float(link.find('inertial/mass').get('value'))
        inertia = link.find('inertial/inertia')
        diagonal = [float(inertia.get(k)) for k in ('ixx', 'iyy', 'izz')]
        assert all(math.isfinite(v) and v > 0 for v in [mass] + diagonal)
        assert 2 * max(diagonal) <= sum(diagonal) + 1e-12
    for link in robot.findall('link'):
        if 'knuckle' not in link.get('name'):
            assert link.find('visual/geometry') is not None
            assert link.find('collision/geometry') is not None


def test_parameterization():
    """Changing base, track and radius changes geometry in SI units."""
    robot = ET.fromstring(xacro.process_file(str(SOURCE), mappings={
        'wheel_base': '1.0', 'track': '0.8', 'wheel_radius': '0.15',
    }).toxml())
    origin = robot.find("joint[@name='front_left_steering_joint']/origin")
    assert [float(v) for v in origin.get('xyz').split()] == [0.5, 0.4, 0]
    wheel = robot.find("link[@name='rear_left_wheel']/visual/geometry/cylinder")
    assert float(wheel.get('radius')) == 0.15
    for joint in robot.findall("joint[@type='continuous']"):
        assert joint.find('axis').get('xyz') == '0 1 0'
