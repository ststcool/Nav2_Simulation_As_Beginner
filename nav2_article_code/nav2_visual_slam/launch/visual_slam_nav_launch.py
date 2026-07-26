#!/usr/bin/env python3
"""visual_slam_nav_launch.py — RTAB-Map 定位导航（融合模式：激光 + RGB-D）。

使用建图阶段保存的 rtabmap.db，RTAB-Map 切为定位模式（Mem/IncrementalMemory=false）。
传感器方案与建图阶段一致（激光 + RGB-D），Nav2 不启动 SLAM Toolbox / AMCL / Map Server。

Usage:
    ros2 launch $HOME/nav2_visual_slam/launch/visual_slam_nav_launch.py \
        database:=results/rtabmap.db
    ros2 launch $HOME/nav2_visual_slam/launch/visual_slam_nav_launch.py \
        world:=obstacle_course.world database:=results/rtabmap.db headless:=True

Launch Arguments:
    world       Gazebo world filename (default: maze.world)
    database    数据库路径 (default: results/rtabmap.db)
    headless    Hide Gazebo GUI (default: False)
    rviz        Launch RViz2 (default: True)
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    home = os.environ['HOME']
    slam_dir = f'{home}/nav2_article_code/nav2_visual_slam'
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    nav2_launch_dir = os.path.join(nav2_bringup_dir, 'launch')

    # --- arguments ---
    world_arg = DeclareLaunchArgument(
        'world', default_value='maze.world',
        description='Gazebo world filename (looked up in worlds/)')
    database_arg = DeclareLaunchArgument(
        'database', default_value=f'{slam_dir}/results/rtabmap.db',
        description='RTAB-Map database path (built during SLAM)')
    headless_arg = DeclareLaunchArgument(
        'headless', default_value='False',
        description='Hide Gazebo GUI')
    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='True',
        description='Launch RViz2')

    # --- worlds path ---
    world = LaunchConfiguration('world')
    world_path = PythonExpression([
        f'"{slam_dir}/worlds/" + "', world, '"'
    ])

    # --- Gazebo ---
    start_gazebo_server = ExecuteProcess(
        cmd=['gzserver', '-s', 'libgazebo_ros_init.so',
             '-s', 'libgazebo_ros_factory.so', world_path],
        output='screen')

    start_gazebo_client = ExecuteProcess(
        condition=UnlessCondition(PythonExpression([LaunchConfiguration('headless')])),
        cmd=['gzclient'], output='screen')

    # --- robot_state_publisher ---
    urdf_path = os.path.join(nav2_bringup_dir, 'urdf', 'turtlebot3_waffle.urdf')
    with open(urdf_path, 'r') as infp:
        robot_description = infp.read()

    start_robot_state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        name='robot_state_publisher', output='screen',
        parameters=[{'use_sim_time': True, 'robot_description': robot_description}],
        remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')])

    # --- spawn 机器人 (深度相机 SDF，激光+RGB-D) ---
    start_spawner = Node(
        package='gazebo_ros', executable='spawn_entity.py', output='screen',
        arguments=[
            '-entity', 'turtlebot3_waffle',
            '-file', f'{slam_dir}/models/turtlebot3_waffle_depth.sdf',
            '-x', '-2.0', '-y', '-2.5', '-z', '0.01',
            '-R', '0.0', '-P', '0.0', '-Y', '0.0'])

    # --- Nav2 导航栈 (不含 SLAM/AMCL/Map Server) ---
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_launch_dir, 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': 'True',
            'autostart': 'True',
            'use_composition': 'False',
            'use_respawn': 'False',
        }.items())

    # --- RTAB-Map 定位模式 ---
    rtabmap_remappings = [
        ('rgb/image', '/camera/image_raw'),
        ('rgb/camera_info', '/camera/camera_info'),
        ('depth/image', '/camera/depth/image_raw'),
    ]

    rtabmap_params = {
        'use_sim_time': True,
        'frame_id': 'base_footprint',
        'subscribe_rgbd': True,
        'subscribe_scan': True,
        'use_action_for_goal': True,
        'database_path': LaunchConfiguration('database'),
        # 定位模式：不增量建图，只匹配已有数据库
        'Mem/IncrementalMemory': 'false',
        'initial_pose': '-2.0 -2.5 0.0 0.0 0.0 0.0',
        'Reg/Strategy': '1',
        'Reg/Force3DoF': 'true',
        'RGBD/NeighborLinkRefining': 'True',
        'Grid/RayTracing': 'true',
        'Grid/3D': 'false',
        'Grid/RangeMax': '3',
        'Grid/NormalsSegmentation': 'true',
        'Grid/Sensor': '2',
        'Grid/MaxGroundHeight': '0.15',
        'Grid/MaxObstacleHeight': '0.4',
        'Grid/RangeMin': '0.3',
        'Optimizer/GravitySigma': '0',
        'map_frame_id': 'map',
        'odom_frame_id': 'odom',
    }

    rgbd_sync_node = Node(
        package='rtabmap_sync', executable='rgbd_sync', output='screen',
        parameters=[{'approx_sync': False, 'use_sim_time': True}],
        remappings=rtabmap_remappings,
    )

    rtabmap_node = Node(
        package='rtabmap_slam', executable='rtabmap', output='screen',
        parameters=[rtabmap_params],
        remappings=rtabmap_remappings + [
            ('grid_map', '/map'),
        ],
    )

    # --- RViz ---
    rviz_node = Node(
        condition=IfCondition(LaunchConfiguration('rviz')),
        package='rviz2',
        executable='rviz2',
        arguments=['-d', f'{nav2_bringup_dir}/rviz/nav2_default_view.rviz'],
    )

    return LaunchDescription([
        world_arg, database_arg, headless_arg, rviz_arg,
        start_gazebo_server,
        start_gazebo_client,
        start_robot_state_publisher,
        start_spawner,
        nav2_navigation,
        rgbd_sync_node,
        rtabmap_node,
        rviz_node,
    ])
