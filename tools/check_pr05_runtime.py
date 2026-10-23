#!/usr/bin/env python3
"""Verify live QoS, conditional MCAP recording and replay of the same bag."""

import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import time

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/pr05'
BAG = OUT / 'bag'
ENV = dict(os.environ, ROS_DOMAIN_ID='118', QT_QPA_PLATFORM='offscreen')
BEFORE = []
AFTER = []


def start(arguments, log_name):
    """Start an owned process and save its complete output."""
    log = (OUT / log_name).open('w')
    process = subprocess.Popen(
        arguments, cwd=ROOT, env=ENV, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True,
    )
    print('$ ' + shlex.join(arguments), flush=True)
    return process, log


def stop(process, log):
    """Let launch or bag finalize its children and metadata on SIGINT."""
    if process.poll() is None:
        if process.args[:2] == ['ros2', 'launch']:
            process.send_signal(signal.SIGINT)
        else:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
    log.close()


def command(arguments, sections, timeout=10):
    """Record real CLI output, including expected missing-message timeouts."""
    process = subprocess.Popen(
        arguments, cwd=ROOT, env=ENV, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, start_new_session=True,
    )
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGINT)
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            output, _ = process.communicate(timeout=5)
    rc = 124 if timed_out else process.returncode
    block = '$ ' + shlex.join(arguments) + '\n' + output + f'\nexit={rc}\n'
    sections.append(block)
    print(block, flush=True)
    return rc, output


def echo(policy, sections, expected):
    """Check delivery with exactly the specified subscriber reliability."""
    rc, output = command([
        'ros2', 'topic', 'echo', '/robot_a/sensor_pose',
        '--qos-reliability', policy, '--once',
    ], sections, timeout=4)
    if expected:
        assert rc == 0 and 'x:' in output, output
    else:
        assert rc == 124 and 'x:' not in output, output


def launch(policy, record, log_name, bag_dir):
    """Start all system nodes using the submitted launch description."""
    return start([
        'ros2', 'launch', 'course_bringup', 'patrol.launch.py',
        'namespace:=robot_a', 'subscriber_reliability:=' + policy,
        'record:=' + record, 'bag_dir:=' + str(bag_dir),
    ], log_name)


def main():
    """Use one corrected input recording for both replay QoS observations."""
    OUT.mkdir(parents=True, exist_ok=True)
    if BAG.exists():
        raise SystemExit('evidence/pr05/bag already exists; preserve or rename it before rerunning')
    unused = OUT / 'record-disabled-must-not-exist'
    if unused.exists():
        raise SystemExit('record=false sentinel path unexpectedly exists')
    bad, bad_log = launch('reliable', 'false', 'live-before.log', unused)
    try:
        time.sleep(3)
        rc, nodes = command([
            'ros2', 'node', 'list', '--no-daemon', '--spin-time', '1',
        ], BEFORE)
        assert rc == 0
        for name in ['/turtlesim', '/robot_a/patrol',
                     '/robot_a/pose_relay', '/robot_a/pose_listener']:
            assert name in nodes, nodes
        command(['ros2', 'topic', 'list', '-t'], BEFORE)
        command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], BEFORE)
        command(['ros2', 'node', 'info', '/robot_a/patrol'], BEFORE)
        echo('reliable', BEFORE, expected=False)
        assert not unused.exists(), 'record=false started the recorder'
    finally:
        stop(bad, bad_log)
    bad_text = (OUT / 'live-before.log').read_text()
    assert 'Received pose #' not in bad_text
    BEFORE.append('Launch log (reliable subscriber, record=false):\n' + bad_text)
    time.sleep(1)
    good, good_log = launch('best_effort', 'true', 'live-after.log', BAG)
    try:
        time.sleep(3)
        command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], AFTER)
        echo('best_effort', AFTER, expected=True)
        time.sleep(4)
    finally:
        stop(good, good_log)
    good_text = (OUT / 'live-after.log').read_text()
    assert 'Received pose #' in good_text
    AFTER.append('Launch log (best-effort subscriber, record=true):\n' + good_text)
    assert (BAG / 'metadata.yaml').is_file()
    metadata = yaml.safe_load((BAG / 'metadata.yaml').read_text())['rosbag2_bagfile_information']
    topics = metadata['topics_with_message_count']
    assert metadata['storage_identifier'] == 'mcap'
    assert len(topics) == 1
    assert topics[0]['topic_metadata']['name'] == '/robot_a/sensor_pose'
    assert topics[0]['message_count'] > 0
    shutil.copyfile(BAG / 'metadata.yaml', OUT / 'bag-metadata.yaml')
    time.sleep(2)
    rc, nodes = command([
        'ros2', 'node', 'list', '--no-daemon', '--spin-time', '1',
    ], AFTER)
    assert '/robot_a/pose_relay' not in nodes and '/turtlesim' not in nodes
    player, player_log = start([
        'ros2', 'bag', 'play', str(BAG), '--loop',
        '--disable-keyboard-controls',
        '--qos-profile-overrides-path', 'config/qos-overrides.yaml',
    ], 'replay.log')
    try:
        time.sleep(2)
        listener, listener_log = start([
            'ros2', 'run', 'course_bringup', 'pose_listener', '--ros-args',
            '-r', '__ns:=/robot_a', '-p', 'subscriber_reliability:=reliable',
        ], 'replay-before.log')
        try:
            time.sleep(2)
            command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], BEFORE)
            echo('reliable', BEFORE, expected=False)
        finally:
            stop(listener, listener_log)
        text = (OUT / 'replay-before.log').read_text()
        assert 'Received pose #' not in text
        BEFORE.append('Replay reliable listener log:\n' + text)
        listener, listener_log = start([
            'ros2', 'run', 'course_bringup', 'pose_listener', '--ros-args',
            '-r', '__ns:=/robot_a', '-p', 'subscriber_reliability:=best_effort',
        ], 'replay-after.log')
        try:
            time.sleep(2)
            command(['ros2', 'topic', 'info', '/robot_a/sensor_pose', '--verbose'], AFTER)
            echo('best_effort', AFTER, expected=True)
        finally:
            stop(listener, listener_log)
        text = (OUT / 'replay-after.log').read_text()
        assert 'Received pose #' in text
        AFTER.append('Replay best-effort listener log:\n' + text)
    finally:
        stop(player, player_log)
    rc, info = command(['ros2', 'bag', 'info', str(BAG)], AFTER)
    assert rc == 0 and 'mcap' in info and '/robot_a/sensor_pose' in info
    summary = {
        'domain_id': 118,
        'live_reliable_received': False,
        'live_best_effort_received': True,
        'record_false_created_bag': False,
        'storage': 'mcap',
        'recorded_topics': len(topics),
        'recorded_messages': topics[0]['message_count'],
        'replay_reliable_received': False,
        'replay_best_effort_received': True,
        'same_bag_used_for_both_replay_profiles': True,
    }
    (OUT / 'runtime-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    try:
        main()
    finally:
        OUT.mkdir(parents=True, exist_ok=True)
        header = 'Real ROS 2 CLI evidence, domain 118, turtlesim offscreen.\n'
        (OUT / 'qos-before.txt').write_text(header + '\n'.join(BEFORE))
        (OUT / 'qos-after.txt').write_text(header + '\n'.join(AFTER))
        subprocess.run(['ros2', 'daemon', 'stop'], env=ENV, timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
