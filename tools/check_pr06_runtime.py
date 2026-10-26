#!/usr/bin/env python3
"""Capture real PR06 geometry, semantic defect and late subscriber experiments."""

import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/pr06'
ENV = dict(os.environ, ROS_DOMAIN_ID='119', LIBGL_ALWAYS_SOFTWARE='1')


def run(args, output, timeout=15, expected=(0,), extra_env=None):
    """Capture a bounded command and its actual return code."""
    print('$ ' + ' '.join(map(str, args)), flush=True)
    process = subprocess.Popen(args, cwd=ROOT, env=extra_env or ENV,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, start_new_session=True)
    try:
        text, _ = process.communicate(timeout=timeout)
        code = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGINT)
        text, _ = process.communicate(timeout=8)
        code = 124
    output.write('$ ' + ' '.join(map(str, args)) + '\n' + text + f'\nexit={code}\n')
    output.flush()
    assert code in expected, (args, code, text[-1000:])
    return text


def stop(process):
    """Let launch forward SIGINT once to its children."""
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=20)


def inspect(xacro_file, label):
    """Read actual fixed transforms with one publisher active at a time."""
    import xacro
    import yaml

    # A parameter file avoids shell quoting of XML and supports a defect source.
    description = xacro.process_file(str(xacro_file)).toxml()
    params = OUT / (label + '-parameters.yaml')
    params.write_text(yaml.safe_dump({'robot_state_publisher': {
        'ros__parameters': {'robot_description': description}}}))
    with (OUT / (label + '-publisher.log')).open('w') as log:
        process = subprocess.Popen([
            'ros2', 'run', 'robot_state_publisher', 'robot_state_publisher',
            '--ros-args', '--params-file', str(params)], cwd=ROOT, env=ENV,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            time.sleep(2)
            assert process.poll() is None
            with (OUT / ('tf-qos.txt' if label == 'fixed' else 'defect-tf.txt')).open('w') as out:
                run(['ros2', 'topic', 'info', '/tf_static', '--verbose'], out)
                run(['ros2', 'topic', 'echo', '/tf_static', '--once',
                     '--qos-durability', 'transient_local',
                     '--qos-reliability', 'reliable'], out)
                run(['ros2', 'topic', 'echo', '/tf_static', '--once',
                     '--qos-durability', 'volatile',
                     '--qos-reliability', 'reliable'], out, timeout=4, expected=(124,))
                result = run(['ros2', 'run', 'tf2_ros', 'tf2_echo',
                              'base_link', 'lidar_link'], out,
                             timeout=5, expected=(124,))
                wanted = '[0.280, 0.000, 0.380]' if label == 'fixed' else '[0.560, 0.000, 0.760]'
                assert wanted in result, result
                run(['ros2', 'run', 'tf2_tools', 'view_frames',
                     '--output', str(OUT / (label + '-frames'))], out)
                out.write('\n/tf_static: reliable + transient_local; сохранённые fixed transforms\n'
                          'получает поздний transient_local подписчик. Volatile подписчик не получает\n'
                          'историю (exit=124). /tf передаёт текущие подвижные связи с volatile.\n')
        finally:
            # ros2 run is a wrapper; signal the owned process group.
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=15)


def main():
    """Compare the committed defect against the restored model."""
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pr06-defect-') as temporary:
        defect = Path(temporary) / 'vehicle.urdf.xacro'
        defect.write_bytes(subprocess.check_output([
            'git', 'show', 'pr06-defect:src/course_description/urdf/vehicle.urdf.xacro'],
            cwd=ROOT))
        with (OUT / 'model-check.txt').open('w') as out:
            out.write('Defect commit: ' + subprocess.check_output([
                'git', 'rev-parse', 'pr06-defect'], cwd=ROOT, text=True).strip() + '\n')
            for label, source, expected in [('defect', defect, (1,)),
                                           ('fixed', ROOT / 'src/course_description/urdf/vehicle.urdf.xacro', (0,))]:
                import xacro
                urdf = OUT / (label + '.urdf')
                urdf.write_text(xacro.process_file(str(source)).toxml())
                out.write('\n## ' + label + '\n')
                run(['check_urdf', str(urdf)], out)
                run(['python3', '-m', 'pytest', '-q',
                     'src/course_description/test/test_geometry.py'], out,
                    expected=expected, extra_env=dict(ENV, COURSE_XACRO=str(source)))
            out.write('check_urdf accepts both trees; only the semantic parent test detects this defect.\n')
        inspect(defect, 'defect')
        inspect(ROOT / 'src/course_description/urdf/vehicle.urdf.xacro', 'fixed')
    with (OUT / 'rviz.log').open('w') as log:
        process = subprocess.Popen([
            'ros2', 'launch', 'course_description', 'display.launch.py', 'rviz:=true'],
            cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)
        try:
            time.sleep(6)
            assert process.poll() is None
        finally:
            stop(process)
    log = (OUT / 'rviz.log').read_text()
    assert 'OpenGl version' in log and 'process has died' not in log, log
    subprocess.run(['ros2', 'daemon', 'stop'], env=ENV, capture_output=True)
    print('PR06 runtime checks passed', flush=True)


if __name__ == '__main__':
    main()
