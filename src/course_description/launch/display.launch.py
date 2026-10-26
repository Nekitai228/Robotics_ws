"""Publish the URDF and optionally display it with base_link as fixed frame."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    """Create one owner of static transforms and an optional RViz process."""
    share = Path(get_package_share_directory('course_description'))
    description = xacro.process_file(str(share / 'urdf/vehicle.urdf.xacro')).toxml()
    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', output='screen', parameters=[{
                 'robot_description': description,
                 'use_sim_time': LaunchConfiguration('use_sim_time'),
             }]),
        Node(package='rviz2', executable='rviz2', output='screen',
             arguments=['-d', str(share / 'rviz/vehicle.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
