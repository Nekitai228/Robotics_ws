#!/usr/bin/env python3
"""Collect real PR04 CLI evidence in an isolated ROS domain."""

import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/pr04'
ENV = dict(os.environ, ROS_DOMAIN_ID='116', QT_QPA_PLATFORM='offscreen')
SECTIONS = []


def stop(process):
    """Stop only a process group started by this script."""
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)


def command(arguments, timeout=12, env=None):
    """Capture a real command and preserve expected measurement timeouts."""
    process = subprocess.Popen(
        arguments, cwd=ROOT, env=env or ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, start_new_session=True,
    )
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop(process)
        output, _ = process.communicate()
    result = 124 if timed_out else process.returncode
    block = '$ ' + shlex.join(arguments) + '\n' + output
    block += f'\nexit={result}\n'
    SECTIONS.append(block)
    print(block, flush=True)
    return result, output


def start(arguments, filename, env=None):
    """Start a background node and send its log directly to a file."""
    log = (EVIDENCE / filename).open('w')
    process = subprocess.Popen(
        arguments, cwd=ROOT, env=env or ENV,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    return process, log


def check_rate(expected, filename):
    """Measure the actual command stream for ten seconds."""
    _, output = command(
        ['ros2', 'topic', 'hz', '/turtle1/cmd_vel'], timeout=10,
    )
    (EVIDENCE / filename).write_text(output)
    rates = re.findall(r'average rate: ([0-9.]+)', output)
    assert rates, 'No command frequency was measured'
    measured = float(rates[-1])
    assert abs(measured - expected) < expected * 0.25, rates
    return measured


def main():
    """Run the deliberate defect and then verify the fixed live system."""
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    worktree = tempfile.mkdtemp(prefix='patrol-pr04-reproduce-')
    subprocess.run(
        ['git', 'worktree', 'add', '--detach', worktree, 'pr04-defect'],
        cwd=ROOT, check=True,
    )
    broken_env = dict(ENV)
    broken_env['PYTHONPATH'] = (
        worktree + '/src/patrol:' + ENV.get('PYTHONPATH', '')
    )
    broken, broken_log = start(
        ['ros2', 'run', 'patrol', 'patrol', '--ros-args',
         '-r', 'cmd_vel:=/turtle1/cmd_vel'],
        'defect-node.txt', env=broken_env,
    )
    try:
        time.sleep(2)
        command(['ros2', 'param', 'get', '/patrol', 'publish_hz'])
        command(['ros2', 'param', 'set', '/patrol', 'publish_hz', '0.0'],
                timeout=6)
        broken.wait(timeout=5)
        assert broken.returncode != 0
    finally:
        stop(broken)
        broken_log.close()
        subprocess.run(
            ['git', 'worktree', 'remove', worktree], cwd=ROOT, check=True,
        )
    traceback = (EVIDENCE / 'defect-node.txt').read_text()
    assert 'ZeroDivisionError' in traceback, traceback
    SECTIONS.append('Deliberate defect process log:\n' + traceback)
    (EVIDENCE / 'defect-cli.txt').write_text('\n'.join(SECTIONS))
    SECTIONS.clear()
    time.sleep(1)
    simulator, simulator_log = start(
        ['ros2', 'run', 'turtlesim', 'turtlesim_node'], 'simulator.txt',
    )
    patrol, patrol_log = start(
        ['ros2', 'run', 'patrol', 'patrol', '--ros-args',
         '-r', 'cmd_vel:=/turtle1/cmd_vel'], 'patrol.txt',
    )
    try:
        time.sleep(2)
        rc, _ = command(['ros2', 'param', 'list', '/patrol'])
        assert rc == 0
        command(['ros2', 'param', 'get', '/patrol', 'linear_speed'])
        command(['ros2', 'param', 'get', '/patrol', 'turn_rate'])
        rc, output = command(
            ['ros2', 'param', 'get', '/patrol', 'publish_hz'],
        )
        assert rc == 0 and '10.0' in output
        command(['ros2', 'topic', 'echo', '/turtle1/pose', '--once'])
        initial_rate = check_rate(10.0, 'hz-10.txt')
        for name, value in [('linear_speed', '0.8'), ('turn_rate', '-0.5')]:
            rc, output = command(
                ['ros2', 'param', 'set', '/patrol', name, value],
            )
            assert rc == 0 and 'success' in output.lower()
        rc, output = command(
            ['ros2', 'topic', 'echo', '/turtle1/cmd_vel', '--once'],
        )
        assert rc == 0 and 'x: 0.8' in output and 'z: -0.5' in output
        rc, output = command(
            ['ros2', 'param', 'set', '/patrol', 'publish_hz', '5.0'],
        )
        assert rc == 0 and 'success' in output.lower()
        changed_rate = check_rate(5.0, 'hz-5.txt')
        rc, output = command(
            ['ros2', 'param', 'set', '/patrol', 'publish_hz', '0.0'],
        )
        assert 'failed' in output.lower() and 'publish_hz' in output
        rc, output = command(
            ['ros2', 'param', 'get', '/patrol', 'publish_hz'],
        )
        assert rc == 0 and '5.0' in output
        preserved_rate = check_rate(5.0, 'hz-after-zero.txt')
        rc, output = command(
            ['ros2', 'service', 'call', '/clear', 'std_srvs/srv/Empty', '{}'],
        )
        assert rc == 0 and 'response:' in output
        rc, output = command(['ros2', 'action', 'list', '-t'])
        assert rc == 0 and '/turtle1/rotate_absolute' in output
        command(['ros2', 'topic', 'echo', '/turtle1/pose', '--once'])
        assert patrol.poll() is None
        summary = (
            f'10 Hz measured: {initial_rate}\n'
            f'5 Hz measured: {changed_rate}\n'
            f'After rejected zero: {preserved_rate} Hz\n'
        )
        (EVIDENCE / 'runtime-summary.txt').write_text(summary)
        print(summary, flush=True)
    finally:
        stop(patrol)
        stop(simulator)
        patrol_log.close()
        simulator_log.close()
        (EVIDENCE / 'runtime-cli.txt').write_text('\n'.join(SECTIONS))


if __name__ == '__main__':
    main()
