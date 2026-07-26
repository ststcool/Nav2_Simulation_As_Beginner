#!/usr/bin/env python3
"""visual_slam_fake_scan_launch.py — 纯视觉 SLAM launch（无实体激光）。

将深度相机图像转换为虚拟 LaserScan，替代实体 LiDAR。
RTAB-Map 独占 /map 话题和 map→odom TF。

与标准版 (visual_slam_launch.py) 的 4 处差异：
    1. 新增 depthimage_to_laserscan 节点
    2. RTAB-Map 订阅 /fake_scan 替代 /scan
    3. Nav2 costmap 通过 params_file 覆盖 scan topic 为 /fake_scan
    4. 数据库路径追加 _fakescan 后缀，避免与标准版冲突

Usage:
    ros2 launch $HOME/nav2_visual_slam/launch/visual_slam_fake_scan_launch.py
    ros2 launch $HOME/nav2_visual_slam/launch/visual_slam_fake_scan_launch.py \
        world:=obstacle_course.world headless:=True
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
    fake_scan_range_arg = DeclareLaunchArgument(
        'fake_scan_range_max', default_value='5.0',
        description='Max range of virtual laser scan (m)')

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

    # --- Gazebo (直接启动，避开 SLAM Toolbox) ---
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

    # --- spawn 机器人 (无激光版) ---
    start_spawner = Node(
        package='gazebo_ros', executable='spawn_entity.py', output='screen',
        arguments=[
            '-entity', 'turtlebot3_waffle',
            '-file', f'{slam_dir}/models/turtlebot3_waffle_depth_nolaser.sdf',
            '-x', '-2.0', '-y', '-2.5', '-z', '0.01',
            '-R', '0.0', '-P', '0.0', '-Y', '0.0'])

    # --- Nav2 导航栈 (只启动 Planner + Controller + Behavior，不含 SLAM/AMCL/Map Server) ---
    # 使用 fake_scan 专用 params (costmap 订阅 /fake_scan)
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_launch_dir, 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': 'True',
            'autostart': 'True',
            'use_composition': 'False',
            'use_respawn': 'False',
            'params_file': f'{slam_dir}/config/nav2_params_fake_scan.yaml',
        }.items())

    # --- RTAB-Map ---
    rtabmap_remappings = [
        ('rgb/image', '/camera/image_raw'),
        ('rgb/camera_info', '/camera/camera_info'),
        ('depth/image', '/camera/depth/image_raw'),
        ('scan', '/fake_scan'),                     # 订阅虚拟激光而非 /scan
    ]

    rtabmap_params = {
        'use_sim_time': True,
        'frame_id': 'base_footprint',
        'subscribe_rgbd': True,
        'subscribe_scan': True,
        'use_action_for_goal': True,
        'database_path': f'{slam_dir}/results/rtabmap_fake_scan.db',
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
        arguments=['-d'],
    )

    # --- depthimage_to_laserscan ---
    depth_to_scan_node = Node(
        package='depthimage_to_laserscan',
        executable='depthimage_to_laserscan_node',
        output='screen',
        parameters=[{
            'scan_height': 10,
            'scan_time': 0.033,
            'range_min': 0.3,
            'range_max': LaunchConfiguration('fake_scan_range_max'),
            'output_frame': 'base_link',
        }],
        remappings=[
            ('depth', '/camera/depth/image_raw'),
            ('depth_camera_info', '/camera/camera_info'),
            ('scan', '/fake_scan'),
        ],
    )

    # --- RViz ---
    rviz_node = Node(
        condition=IfCondition(LaunchConfiguration('rviz')),
        package='rviz2',
        executable='rviz2',
        arguments=['-d', f'{slam_dir}/config/nav2_default_view_fake_scan.rviz'],
    )

    return LaunchDescription([
        world_arg, headless_arg, move_box_arg,
        move_x_arg, move_min_y_arg, move_max_y_arg, move_speed_arg,
        rviz_arg, fake_scan_range_arg,
        move_box_cmd,
        start_gazebo_server,
        start_gazebo_client,
        start_robot_state_publisher,
        start_spawner,
        nav2_navigation,
        rgbd_sync_node,
        rtabmap_node,
        depth_to_scan_node,
        rviz_node,
    ])