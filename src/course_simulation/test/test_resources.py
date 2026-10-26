"""Check command routing and physical wheel axes in the installed model sources."""

from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).parents[1]


def test_bridge_contract():
    """Keep a single safe command route and explicit sensor QoS."""
    config = yaml.safe_load((ROOT / 'config/bridge.yaml').read_text())
    topics = {e['ros_topic_name']: e for e in config}
    assert len(config) == len(topics) == 6
    assert '/drive/raw' not in str(config)
    assert topics['/vehicle/gz_cmd_vel']['direction'] == 'ROS_TO_GZ'
    assert topics['/vehicle/gz_cmd_vel']['gz_topic_name'] == '/model/course_ackermann/cmd_vel'
    assert '/vehicle/odom' not in topics
    assert topics['/vehicle/odom_gz']['direction'] == 'GZ_TO_ROS'
    for name in ['imu', 'scan', 'camera/image_raw']:
        assert topics['/vehicle/' + name]['qos_profile'] == 'SENSOR_DATA'
        assert topics['/vehicle/' + name]['gz_topic_name'] == '/vehicle/' + name


def test_model_axes_and_rate():
    """Rolling axes are transverse, steering axes vertical, IMU rate changed."""
    model = ET.parse(ROOT / 'models/course_ackermann/model.sdf').getroot().find('model')
    for joint in model.findall('joint'):
        if joint.get('name').endswith('_wheel_joint'):
            axis = joint.find('axis/xyz')
            assert axis.text == '0 1 0' and axis.get('expressed_in') == '__model__'
        if joint.get('name').endswith('_steering_joint'):
            assert joint.find('axis/xyz').text == '0 0 1'
    assert model.find("link[@name='imu_link']/sensor/update_rate").text == '50'
