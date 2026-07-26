#!/usr/bin/env python3
"""
参数化测试框架启动脚本。
Usage:
  ros2 launch $HOME/nav2_article_code/nav2_testbed/launch/testbed.launch.py \
      world:=$HOME/nav2_article_code/nav2_testbed/worlds/maze.world \
      map:=$HOME/nav2_article_code/nav2_testbed/maps/maze.yaml \
      params:=$HOME/nav2_article_code/nav2_testbed/params/config1.yaml

  # SLAM mode:
  ros2 launch $HOME/nav2_article_code/nav2_testbed/launch/testbed.launch.py slam:=True \
      world:=$HOME/nav2_article_code/nav2_testbed/worlds/obstacle_course.world
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav2_launch_dir = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch')
    home = os.path.expanduser('~')
    testbed_dir = os.path.join(home, 'nav2_article_code', 'nav2_testbed')

    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(testbed_dir, 'worlds', 'maze.world'),
        description='Full path to world (.world or .sdf)')

    declare_map_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(testbed_dir, 'maps', 'maze.yaml'),
        description='Full path to map YAML')

    declare_params_cmd = DeclareLaunchArgument(
        'params',
        default_value=os.path.join(testbed_dir, 'params', 'config1.yaml'),
        description='Full path to nav2 params YAML')

    declare_x_cmd = DeclareLaunchArgument(
        'x_pose', default_value='-2.0',
        description='Robot initial X')

    declare_y_cmd = DeclareLaunchArgument(
        'y_pose', default_value='-2.5',
        description='Robot initial Y')

    declare_yaw_cmd = DeclareLaunchArgument(
        'yaw', default_value='0.0',
        description='Robot initial yaw')

    declare_headless_cmd = DeclareLaunchArgument(
        'headless', default_value='False',
        description='Run gzclient? (True for headless batch testing)')

    declare_slam_cmd = DeclareLaunchArgument(
        'slam', default_value='False',
        description='Run SLAM instead of AMCL localization')

    return LaunchDescription([
        declare_world_cmd,
        declare_map_cmd,
        declare_params_cmd,
        declare_x_cmd,
        declare_y_cmd,
        declare_yaw_cmd,
        declare_headless_cmd,
        declare_slam_cmd,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_launch_dir, 'tb3_simulation_launch.py')),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'map': LaunchConfiguration('map'),
                'params_file': LaunchConfiguration('params'),
                'slam': LaunchConfiguration('slam'),
                'x_pose': LaunchConfiguration('x_pose'),
                'y_pose': LaunchConfiguration('y_pose'),
                'yaw': LaunchConfiguration('yaw'),
                'headless': LaunchConfiguration('headless'),
            }.items()
        ),
    ])
