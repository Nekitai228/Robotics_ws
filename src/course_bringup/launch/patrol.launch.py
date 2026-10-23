"""Launch the namespaced patrol system and optionally record one MCAP stream."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Declare launch arguments and connect the system to one global turtle."""
    namespace = LaunchConfiguration('namespace')
    record = LaunchConfiguration('record')
    bag_dir = LaunchConfiguration('bag_dir')
    reliability = LaunchConfiguration('subscriber_reliability')
    sensor_topic = PathJoinSubstitution(['/', namespace, 'sensor_pose'])
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        DeclareLaunchArgument('record', default_value='false'),
        DeclareLaunchArgument('bag_dir', default_value='evidence/pr05/bag'),
        DeclareLaunchArgument(
            'subscriber_reliability', default_value='best_effort',
            choices=['reliable', 'best_effort'],
        ),
        LogInfo(msg=[
            'namespace=', namespace, ', record=', record,
            ', subscriber_reliability=', reliability,
        ]),
        Node(
            package='turtlesim', executable='turtlesim_node',
            namespace='/', output='screen',
        ),
        Node(
            package='patrol', executable='patrol',
            namespace=namespace, output='screen',
            remappings=[
                ('turtle1/pose', '/turtle1/pose'),
                ('cmd_vel', '/turtle1/cmd_vel'),
            ],
        ),
        Node(
            package='course_bringup', executable='pose_relay',
            namespace=namespace, output='screen',
            remappings=[('turtle1/pose', '/turtle1/pose')],
        ),
        Node(
            package='course_bringup', executable='pose_listener',
            namespace=namespace, output='screen',
            parameters=[{'subscriber_reliability': reliability}],
        ),
        ExecuteProcess(
            cmd=[
                'ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir,
                '--disable-keyboard-controls', '--topics', sensor_topic,
            ],
            condition=IfCondition(record), output='screen',
            sigterm_timeout='10', sigkill_timeout='5',
        ),
    ])
