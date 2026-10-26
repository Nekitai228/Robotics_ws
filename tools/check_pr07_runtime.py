#!/usr/bin/env python3
"""Verify the real headless chain and record a reusable simulation time fixture."""

from collections import defaultdict, deque
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, Imu, LaserScan
from tf2_msgs.msg import TFMessage
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/pr07'
BAG = ROOT / 'fixtures/pr07-sensors'
ENV = dict(os.environ, ROS_DOMAIN_ID='120', GZ_PARTITION='pr07-codex',
           LIBGL_ALWAYS_SOFTWARE='1', EGL_PLATFORM='surfaceless')
os.environ.update({key: ENV[key] for key in (
    'ROS_DOMAIN_ID', 'GZ_PARTITION', 'LIBGL_ALWAYS_SOFTWARE', 'EGL_PLATFORM')})
PROCESSES = []


def start(args, name, launch=False):
    """Keep an owned process and its log for reliable cleanup."""
    log = (OUT / name).open('w')
    print('$ ' + ' '.join(map(str, args)), flush=True)
    process = subprocess.Popen(args, cwd=ROOT, env=ENV, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
    PROCESSES.append((process, log, launch))
    return process


def stop(process):
    """Allow launch to forward SIGINT once; signal wrappers as a group."""
    entry = next(item for item in PROCESSES if item[0] is process)
    if process.poll() is None:
        if entry[2]:
            process.send_signal(signal.SIGINT)
        else:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=25)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
    entry[1].flush()


def run(args, filename, timeout=12, expected=(0,)):
    """Capture CLI observations, marking a deliberate timeout as 124."""
    print('$ ' + ' '.join(map(str, args)), flush=True)
    process = subprocess.Popen(args, cwd=ROOT, env=ENV, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               start_new_session=True)
    try:
        text, _ = process.communicate(timeout=timeout)
        code = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGINT)
        text, _ = process.communicate(timeout=10)
        code = 124
    with (OUT / filename).open('a') as out:
        out.write('$ ' + ' '.join(map(str, args)) + '\n' + text + f'\nexit={code}\n')
    assert code in expected, (args, code, text[-1200:])
    return text


def stamp(message):
    """Read a timestamp as seconds without converting to host wall time."""
    value = message.clock if isinstance(message, Clock) else message.header.stamp
    return value.sec + value.nanosec / 1e9


class Probe(Node):
    """Collect counters, stamps and recent data while CLI commands run."""

    def __init__(self):
        super().__init__('pr07_probe', parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.counts = defaultdict(int)
        self.samples = defaultdict(lambda: deque(maxlen=10000))
        self.last = {}
        self.transforms = {}
        self.static = set()
        self.subscriptions_ = []
        sensor = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        static = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        for topic, kind, qos in [
            ('/clock', Clock, sensor),
            ('/vehicle/camera/image_raw', Image, sensor),
            ('/vehicle/scan', LaserScan, sensor),
            ('/vehicle/imu', Imu, sensor),
            ('/vehicle/odom_gz', Odometry, 50),
            ('/vehicle/odom', Odometry, 50),
            ('/vehicle/gz_cmd_vel', Twist, 10),
            ('/tf', TFMessage, 100), ('/tf_static', TFMessage, static),
        ]:
            self.subscriptions_.append(self.create_subscription(
                kind, topic, lambda msg, name=topic: self.receive(name, msg), qos))
        self.drive = self.create_publisher(AckermannDriveStamped, '/drive/safe', 10)
        self.raw_drive = self.create_publisher(AckermannDriveStamped, '/drive/raw', 10)
        self.speed = 0.0
        self.steering = 0.0
        self.enabled = False
        self.command_override = None
        self.command_timer = self.create_timer(0.05, self.publish_command)

    def publish_command(self):
        if not self.enabled or '/clock' not in self.last:
            return
        msg = AckermannDriveStamped()
        msg.header.stamp = deepcopy(self.last['/clock'].clock)
        msg.header.frame_id = 'base_link'
        msg.drive.speed, msg.drive.steering_angle = self.speed, self.steering
        if self.command_override == 'stale':
            msg.header.stamp.sec -= 1
        if self.command_override == 'nan':
            msg.drive.speed = float('nan')
        self.drive.publish(msg)

    def receive(self, topic, message):
        self.counts[topic] += 1
        self.last[topic] = message
        if hasattr(message, 'header') or isinstance(message, Clock):
            self.samples[topic].append((time.monotonic(), stamp(message)))
        if topic == '/tf':
            for transform in message.transforms:
                if transform.header.frame_id == 'odom' and transform.child_frame_id == 'base_link':
                    key = (transform.header.stamp.sec, transform.header.stamp.nanosec)
                    self.transforms[key] = transform
            if len(self.transforms) > 1000:
                self.transforms.pop(next(iter(self.transforms)))
        if topic == '/tf_static':
            self.static.update((t.header.frame_id, t.child_frame_id) for t in message.transforms)

    def wait(self, predicate, seconds=60, description='condition'):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        raise AssertionError(f'Timeout waiting for {description}; counts={dict(self.counts)}')

    def wait_sim(self, seconds):
        beginning = stamp(self.last['/clock'])
        self.wait(lambda: stamp(self.last['/clock']) - beginning >= seconds,
                  seconds=max(60, seconds * 15), description=f'{seconds} simulation seconds')


def gz_pose(filename):
    """Capture actual body and wheel poses from Gazebo, independently of odometry."""
    text = run(['gz', 'topic', '-e', '-t', '/world/mcity_minimal/dynamic_pose/info',
                '-n', '1', '--json-output'], filename)
    result = json.loads(text)
    return result


def model_pose(data):
    """Find the model-level world pose in a Pose_V message."""
    return next(pose for pose in data['pose'] if pose.get('name') == 'course_ackermann')


def verify_wheels(before, after):
    """Remove steering and cylinder mounting rotation to check the rolling axis."""
    def quat(pose):
        q = pose['orientation']
        return [q.get(k, 0.0) for k in ['x', 'y', 'z', 'w']]

    def conjugate(q):
        return [-q[0], -q[1], -q[2], q[3]]

    def multiply(a, b):
        x, y, z, w = a
        X, Y, Z, W = b
        return [w*X + x*W + y*Z - z*Y, w*Y - x*Z + y*W + z*X,
                w*Z + x*Y - y*X + z*W, w*W - x*X - y*Y - z*Z]

    old = {p['name']: p for p in before['pose']}
    new = {p['name']: p for p in after['pose']}
    result = {}
    for side in ['left', 'right']:
        knuckle = quat(new[f'front_{side}_knuckle'])
        yaw = 2 * math.atan2(knuckle[2], knuckle[3])
        assert abs(yaw) > 0.03, (side, 'no physical steering')
        result['steering_' + side + '_rad'] = yaw
        for end in ['front', 'rear']:
            name = f'{end}_{side}_wheel'
            rotation = quat(new[name])
            if end == 'front':
                rotation = multiply(conjugate(knuckle), rotation)
            delta = multiply(rotation, conjugate(quat(old[name])))
            assert abs(delta[0]) < 1e-5 and abs(delta[2]) < 1e-5, (name, delta)
            assert abs(delta[1]) > 0.03, (name, 'wheel did not roll')
            result[name + '_roll_delta_quaternion'] = delta
    return result


def main():
    """Reproduce an IMU typo, fix one bridge and validate every required stream."""
    if BAG.exists():
        raise SystemExit(f'Preserve existing fixture before rerunning: {BAG}')
    OUT.mkdir(parents=True, exist_ok=True)
    BAG.parent.mkdir(exist_ok=True)
    for name in ['diagnostics.txt', 'defect.txt', 'frequencies.txt', 'command-path.txt',
                 'body-before.txt', 'body-after.txt', 'bag-info.txt']:
        (OUT / name).write_text('')
    rclpy.init()
    probe = Probe()
    executor = SingleThreadedExecutor()
    executor.add_node(probe)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        bad = start(['ros2', 'launch', 'course_simulation', 'simulation.launch.py',
                     'headless:=true', 'bridge_config:=' + str(ROOT / 'src/course_simulation/config/bridge-defect.yaml')],
                    'defect-headless.txt', launch=True)
        probe.wait(lambda: probe.counts['/vehicle/scan'] > 3 and probe.counts['/clock'] > 3,
                   description='bad bridge clock and scan')
        run(['ros2', 'topic', 'info', '-v', '/vehicle/imu'], 'defect.txt')
        run(['gz', 'topic', '-i', '-t', '/vehicle/imu'], 'defect.txt')
        run(['gz', 'topic', '-e', '-t', '/vehicle/imu', '-n', '1'], 'defect.txt')
        run(['ros2', 'topic', 'echo', '/vehicle/imu', '--once',
             '--qos-reliability', 'best_effort'], 'defect.txt', timeout=4, expected=(124,))
        assert probe.counts['/vehicle/imu'] == 0
        stop(bad)
        assert bad.poll() is not None
        time.sleep(2)
        probe.counts.clear()
        probe.samples.clear()
        probe.last.clear()
        probe.static.clear()
        good = start(['ros2', 'launch', 'course_simulation', 'simulation.launch.py',
                      'headless:=true'], 'headless.txt', launch=True)
        sensors = ['/vehicle/camera/image_raw', '/vehicle/scan', '/vehicle/imu',
                   '/vehicle/odom_gz', '/vehicle/odom']
        probe.wait(lambda: all(probe.counts[t] > 5 for t in sensors) and
                   len(probe.static) == 3, description='all corrected streams and static tf')
        assert good.poll() is None
        run(['ros2', 'node', 'list', '--no-daemon', '--spin-time', '1'], 'diagnostics.txt')
        for topic in sensors + ['/vehicle/gz_cmd_vel', '/tf', '/tf_static']:
            run(['ros2', 'topic', 'info', '-v', topic], 'diagnostics.txt')
        run(['ros2', 'topic', 'echo', '/clock', '--once'], 'diagnostics.txt')
        # Check actual offered QoS, not just the names written into YAML.
        for topic in sensors[:3]:
            offers = probe.get_publishers_info_by_topic(topic)
            assert len(offers) == 1 and offers[0].qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
        assert len(probe.get_publishers_info_by_topic('/vehicle/odom')) == 1
        assert {p.node_name for p in probe.get_publishers_info_by_topic('/tf')} == {
            'robot_state_publisher', 'odom_adapter'}
        assert len(probe.get_publishers_info_by_topic('/tf_static')) == 1
        recorder = start(['ros2', 'bag', 'record', '-s', 'mcap', '--use-sim-time',
                          '--disable-keyboard-controls', '-o', str(BAG), '--topics',
                          '/vehicle/camera/image_raw', '/vehicle/scan', '/vehicle/imu',
                          '/vehicle/odom', '/tf', '/tf_static', '/clock'], 'recorder.log')
        time.sleep(2)
        start_clock = stamp(probe.last['/clock'])
        wall_start = time.monotonic()
        for topic in sensors[:3]:
            run(['ros2', 'topic', 'hz', topic], 'frequencies.txt', timeout=4, expected=(124,))
        before = gz_pose('body-before.txt')
        odom_before = deepcopy(probe.last['/vehicle/odom'])
        probe.enabled, probe.speed, probe.steering = True, 0.3, 0.15
        probe.wait_sim(1)
        run(['ros2', 'topic', 'echo', '/vehicle/gz_cmd_vel', '--once'], 'command-path.txt')
        run(['gz', 'topic', '-i', '-t', '/model/course_ackermann/cmd_vel'], 'command-path.txt')
        text = run(['gz', 'topic', '-e', '-t', '/model/course_ackermann/cmd_vel',
                    '-n', '1', '--json-output'], 'command-path.txt')
        command = json.loads(text)
        assert abs(command['linear']['x'] - 0.3) < 1e-6
        assert abs(command['angular']['z'] - 0.3 * math.tan(0.15) / 0.8) < 1e-6
        probe.wait_sim(2)
        after = gz_pose('body-after.txt')
        odom_after = deepcopy(probe.last['/vehicle/odom'])
        wheel_check = verify_wheels(before, after)
        p0, p1 = model_pose(before)['position'], model_pose(after)['position']
        physical_distance = math.hypot(p1.get('x', 0)-p0.get('x', 0), p1.get('y', 0)-p0.get('y', 0))
        odom_distance = math.hypot(odom_after.pose.pose.position.x-odom_before.pose.pose.position.x,
                                   odom_after.pose.pose.position.y-odom_before.pose.pose.position.y)
        assert physical_distance > 0.2 and odom_distance > 0.2, (physical_distance, odom_distance)
        probe.speed = probe.steering = 0.0
        probe.wait_sim(0.5)
        # Stale and NaN refusals are also checked on the running node.
        for refusal in ['stale', 'nan']:
            probe.speed = 0.4
            probe.command_override = refusal
            probe.wait_sim(0.4)
            assert probe.last['/vehicle/gz_cmd_vel'].linear.x == 0
        probe.speed = 0.0
        probe.command_override = None
        probe.wait_sim(0.4)
        probe.enabled = False
        # Raw commands must have no subscriber at this stage.
        assert probe.count_subscribers('/drive/raw') == 0
        raw = AckermannDriveStamped()
        raw.header.stamp = deepcopy(probe.last['/clock'].clock)
        raw.drive.speed = 1.0
        probe.raw_drive.publish(raw)
        probe.wait_sim(0.5)
        assert probe.last['/vehicle/gz_cmd_vel'].linear.x == 0
        # Match tf against a measured odometry stamp and pose.
        matched = deepcopy(probe.last['/vehicle/odom'])
        key = (matched.header.stamp.sec, matched.header.stamp.nanosec)
        probe.wait(lambda: key in probe.transforms, description='matching odometry tf')
        tf = probe.transforms[key]
        assert tf.transform.translation.x == matched.pose.pose.position.x
        assert tf.transform.rotation == matched.pose.pose.orientation
        # Finish at least 33 simulation seconds after recording was established.
        last_progress = 0
        while stamp(probe.last['/clock']) - start_clock < 33:
            elapsed = stamp(probe.last['/clock']) - start_clock
            if elapsed - last_progress >= 5:
                print(f'Recorded {elapsed:.1f} simulation seconds', flush=True)
                last_progress = elapsed
            assert time.monotonic() - wall_start < 600, 'simulation too slow'
            assert recorder.poll() is None and good.poll() is None
            time.sleep(0.2)
        stop(recorder)
        run(['ros2', 'bag', 'info', str(BAG)], 'bag-info.txt')
        metadata = yaml.safe_load((BAG / 'metadata.yaml').read_text())['rosbag2_bagfile_information']
        assert metadata['storage_identifier'] == 'mcap'
        assert metadata['duration']['nanoseconds'] >= 30e9
        counts = {t['topic_metadata']['name']: t['message_count'] for t in metadata['topics_with_message_count']}
        assert all(counts.get(t, 0) > 0 for t in [
            '/vehicle/camera/image_raw', '/vehicle/scan', '/vehicle/imu',
            '/vehicle/odom', '/tf', '/tf_static', '/clock'])
        (OUT / 'bag-metadata.yaml').write_bytes((BAG / 'metadata.yaml').read_bytes())
        declared = [20, 10, 50, 50, 50]
        data = []
        for topic, hz in zip(sensors, declared):
            samples = list(probe.samples[topic])
            wall_hz = (len(samples)-1) / (samples[-1][0]-samples[0][0])
            sim_hz = (len(samples)-1) / (samples[-1][1]-samples[0][1])
            message = probe.last[topic]
            assert message.header.frame_id == {
                '/vehicle/camera/image_raw': 'camera_link', '/vehicle/scan': 'lidar_link',
                '/vehicle/imu': 'imu_link', '/vehicle/odom_gz': 'course_ackermann/odom',
                '/vehicle/odom': 'odom'}[topic], (topic, message.header.frame_id)
            row = {'topic': topic, 'type': type(message).__module__.split('.')[0] + '/msg/' + type(message).__name__,
                   'frame_id': message.header.frame_id, 'source_time': '/clock (Gazebo simulation)',
                   'declared_hz': hz, 'measured_wall_hz': wall_hz, 'measured_sim_hz': sim_hz,
                   'observed_messages': len(samples)}
            if isinstance(message, Odometry):
                row['child_frame_id'] = message.child_frame_id
            data.append(row)
        rtf = (stamp(probe.last['/clock']) - start_clock) / (time.monotonic() - wall_start)
        result = {'sensors': data, 'imu_parameter_change': {'before_hz': 100, 'after_hz': 50},
                  'real_time_factor': rtf, 'physical_distance_m': physical_distance,
                  'odometry_distance_m': odom_distance, 'wheel_check': wheel_check, 'bag_duration_sim_s': metadata['duration']['nanoseconds']/1e9,
                  'bag_topic_counts': counts,
                  'frequency_explanation': 'Software OGRE2/EGL rendering and concurrent capture/CLI load lower wall-clock rates. Compare update_rate to stamp-based simulation rates; wall rates are approximately simulation rates times measured real-time factor.',
                  'environment': 'WSL2 Ubuntu 24.04 / Jazzy / Harmonic 8.15.0; adapted from kit Lyrical/Jetty baseline'}
        (OUT / 'sensors.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        fixture = {'path': 'fixtures/pr07-sensors', 'duration_sim_s': result['bag_duration_sim_s'],
                   'files': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in BAG.iterdir() if f.is_file()}}
        (OUT / 'fixture-sha256.json').write_text(json.dumps(fixture, indent=2)+'\n')
        assert good.poll() is None
        stop(good)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        print('PR07 runtime checks passed', flush=True)
    finally:
        for process, log, _ in reversed(PROCESSES):
            stop(process)
            log.close()
        executor.shutdown()
        thread.join(timeout=5)
        probe.destroy_node()
        rclpy.shutdown()
        subprocess.run(['ros2', 'daemon', 'stop'], env=ENV, capture_output=True)


if __name__ == '__main__':
    main()
