"""Run one Gazebo server, one bridge, the description and both adapters."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def start(context):
    """Resolve paths and choose actual headless rendering flags."""
    share = Path(get_package_share_directory('course_simulation'))
    description_share = Path(get_package_share_directory('course_description'))
    world = LaunchConfiguration('world').perform(context)
    bridge = LaunchConfiguration('bridge_config').perform(context)
    namespace = LaunchConfiguration('namespace').perform(context)
    headless = LaunchConfiguration('headless').perform(context).lower() == 'true'
    resource = str(share / 'models')
    if os.environ.get('GZ_SIM_RESOURCE_PATH'):
        resource += os.pathsep + os.environ['GZ_SIM_RESOURCE_PATH']
    command = ['gz', 'sim', '-r', '-v', '3']
    if headless:
        command += ['-s', '--headless-rendering']
    command += [world]
    description = xacro.process_file(
        str(description_share / 'urdf/vehicle.urdf.xacro')).toxml()
    common = {'use_sim_time': True}
    return [
        ExecuteProcess(cmd=command, output='screen',
                       additional_env={'GZ_SIM_RESOURCE_PATH': resource},
                       sigterm_timeout='15', sigkill_timeout='5'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             namespace=namespace, output='screen',
             parameters=[common, {'robot_description': description}]),
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             name='bridge', namespace=namespace, output='screen',
             parameters=[common, {'config_file': bridge}]),
        Node(package='course_simulation', executable='drive_adapter',
             namespace=namespace, output='screen', parameters=[common]),
        Node(package='course_simulation', executable='odom_adapter',
             namespace=namespace, output='screen', parameters=[common]),
    ]


def generate_launch_description():
    """Expose installed resources and preserve the contractual global topics."""
    share = Path(get_package_share_directory('course_simulation'))
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=str(share / 'worlds/mcity-minimal.sdf')),
        DeclareLaunchArgument('bridge_config', default_value=str(share / 'config/bridge.yaml')),
        DeclareLaunchArgument('headless', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        OpaqueFunction(function=start),
    ])
