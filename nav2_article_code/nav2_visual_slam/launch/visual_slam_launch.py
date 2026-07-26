#!/usr/bin/env python3
"""visual_slam_launch.py — RTAB-Map SLAM launch for Gazebo Classic + TurtleBot3.

RTAB-Map 独占 /map 话题和 map→odom TF，Nav2 不启动 SLAM Toolbox / AMCL / Map Server。

Usage:
    ros2 launch $HOME/nav2_visual_slam/launch/visual_slam_launch.py
    ros2 launch $HOME/nav2_visual_slam/launch/visual_slam_launch.py \
        world:=obstacle_course.world headless:=True move_box:=True

Launch Arguments:
    world       Gazebo world filename (default: maze.world)
                Looked up in $HOME/nav2_visual_slam/worlds/
    headless    Hide Gazebo GUI (default: False)
    move_box    Launch move_box.py as a dynamic obstacle (default: False)
    move_x      Box X coordinate (default: depends on world)
    move_min_y  Box Y min (default: depends on world)
    move_max_y  Box Y max (default: depends on world)
    move_speed  Box speed m/s (default: 1.5)
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
    headless_arg = DeclareLaunchArgument(
        'headless', default_value='False',
        description='Hide Gazebo GUI')
    move_box_arg = DeclareLaunchArgument(
        'move_box', default_value='False',
        description='Run move_box.py dynamic obstacle')
    move_x_arg = DeclareLaunchArgument(
        'move_x', default_value='auto',
        description='Box X coordinate (auto = select by world)')
    move_min_y_arg = DeclareLaunchArgument(
        'move_min_y', default_value='auto',
        description='Box Y min (auto = select by world)')
    move_max_y_arg = DeclareLaunchArgument(
        'move_max_y', default_value='auto',
        description='Box Y max (auto = select by world)')
    move_speed_arg = DeclareLaunchArgument(
        'move_speed', default_value='1.5',
        description='Box speed (m/s)')
    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='True',
        description='Launch RViz2')

    # --- worlds path ---
    world = LaunchConfiguration('world')
    world_path = PythonExpression([
        f'"{slam_dir}/worlds/" + "', world, '"'
    ])

    # --- move_box auto coordinates ---
    move_x_val = LaunchConfiguration('move_x')
    move_min_y_val = LaunchConfiguration('move_min_y')
    move_max_y_val = LaunchConfiguration('move_max_y')

    actual_x = PythonExpression([
        f'"1.5" if "', move_x_val, f'"=="auto" and "', world,
        f'"=="maze.world" else ("3.0" if "', move_x_val, f'"=="auto" else "',
        move_x_val, '")'
    ])
    actual_min_y = PythonExpression([
        f'"-3.0" if "', move_min_y_val, f'"=="auto" and "', world,
        f'"=="maze.world" else ("-2.0" if "', move_min_y_val, f'"=="auto" else "',
        move_min_y_val, '")'
    ])
    actual_max_y = PythonExpression([
        f'"3.0" if "', move_max_y_val, f'"=="auto" and "', world,
        f'"=="maze.world" else ("2.0" if "', move_max_y_val, f'"=="auto" else "',
        move_max_y_val, '")'
    ])

    # --- move_box process ---
    move_box_cmd = ExecuteProcess(
        condition=IfCondition(LaunchConfiguration('move_box')),
        cmd=[
            'python3', f'{slam_dir}/scripts/move_box.py',
            '--x', actual_x,
            '--min_y', actual_min_y,
            '--max_y', actual_max_y,
            '--speed', LaunchConfiguration('move_speed'),
        ],
        output='screen',
    )

    # --- Gazebo (不通过 tb3_simulation_launch, 直接启动以避开 SLAM Toolbox) ---
    start_gazebo_server = ExecuteProcess(
        cmd=['gzserver', '-s', 'libgazebo_ros_init.so',
             '-s', 'libgazebo_ros_factory.so', world_path],
        output='screen')

    start_gazebo_client = ExecuteProcess(
        condition=UnlessCondition(PythonExpression([LaunchConfiguration('headless')])),
        cmd=['gzclient'], output='screen')

    # --- robot_state_publisher (读取 URDF 发布 TF) ---
    urdf_path = os.path.join(nav2_bringup_dir, 'urdf', 'turtlebot3_waffle.urdf')
    with open(urdf_path, 'r') as infp:
        robot_description = infp.read()

    start_robot_state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        name='robot_state_publisher', output='screen',
        parameters=[{'use_sim_time': True, 'robot_description': robot_description}],
        remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')])

    # --- spawn 机器人 (使用深度相机 SDF) ---
    start_spawner = Node(
        package='gazebo_ros', executable='spawn_entity.py', output='screen',
        arguments=[
            '-entity', 'turtlebot3_waffle',
            '-file', f'{slam_dir}/models/turtlebot3_waffle_depth.sdf',
            '-x', '-2.0', '-y', '-2.5', '-z', '0.01',
            '-R', '0.0', '-P', '0.0', '-Y', '0.0'])

    # --- Nav2 导航栈 (只启动 Planner + Controller + Behavior，不含 SLAM/AMCL/Map Server) ---
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_launch_dir, 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': 'True',
            'autostart': 'True',
            'use_composition': 'False',
            'use_respawn': 'False',
        }.items())

    # --- RTAB-Map ---
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
        'database_path': f'{slam_dir}/results/rtabmap.db',
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
        # 将 RTAB-Map 的栅格地图发布到 /map (替代 Map Server / SLAM Toolbox)
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
            ('grid_map', '/map'),               # 栅格地图 → /map 话题
        ],
        arguments=['-d'],
    )

    # --- RViz ---
    rviz_node = Node(
        condition=IfCondition(LaunchConfiguration('rviz')),
        package='rviz2',
        executable='rviz2',
        arguments=['-d', f'{nav2_bringup_dir}/rviz/nav2_default_view.rviz'],
    )

    return LaunchDescription([
        world_arg, headless_arg, move_box_arg,
        move_x_arg, move_min_y_arg, move_max_y_arg, move_speed_arg,
        rviz_arg,
        move_box_cmd,
        start_gazebo_server,
        start_gazebo_client,
        start_robot_state_publisher,
        start_spawner,
        nav2_navigation,
        rgbd_sync_node,
        rtabmap_node,
        rviz_node,
    ])