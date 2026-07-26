#!/usr/bin/env python3
"""
Maze simulation wrapper launch — all parameters baked in, no CLI args needed.

Important — run cleanup before launching:
  bash $HOME/nav2_article_code/nav2_algorithm_lab/cleanup.sh

Usage: ros2 launch $HOME/nav2_article_code/nav2_algorithm_lab/launch/maze_simulation_launch.py
"""

import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav2_launch_dir = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch')
    home = os.path.expanduser('~')
    lab_dir = os.path.join(home, 'nav2_article_code', 'nav2_algorithm_lab')

    move_box_node = ExecuteProcess(
        cmd=['python3', os.path.join(lab_dir, 'move_box.py')],
        output='screen',
    )

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_launch_dir, 'tb3_simulation_launch.py')),
            launch_arguments={
                'world': os.path.join(lab_dir, 'worlds', 'maze.world'),
                'map': os.path.join(lab_dir, 'maps', 'maze.yaml'),
                'params_file': os.path.join(lab_dir, 'nav2_params_config1.yaml'),
                'x_pose': '-2.0',
                'y_pose': '-2.5',
                'yaw': '0.0',
                'headless': 'False',
            }.items()
        ),
        move_box_node,
    ])
