#!/bin/bash
# Clean stale Gazebo/ROS2 processes — run before any Nav2 launch in the testbed
#
# Usage:
#   bash $HOME/nav2_article_code/nav2_testbed/scripts/cleanup.sh
#   bash $HOME/nav2_article_code/nav2_algorithm_lab/cleanup.sh   # also still works (aliased)

echo "=== Killing stale processes ==="
kill -9 $(pgrep -x gzserver) 2>/dev/null
kill -9 $(pgrep -x gzclient) 2>/dev/null
pkill -f "spawn_entity.py" 2>/dev/null
pkill -f "robot_state_publisher" 2>/dev/null
pkill -f "component_container" 2>/dev/null
pkill -f "move_box.py" 2>/dev/null
pkill -f "send_goal.py" 2>/dev/null
pkill -f "rviz2" 2>/dev/null
sleep 1

echo "=== Cleaning SHM ==="
rm -f /tmp/gazebo_${USER}* 2>/dev/null
rm -f /dev/shm/gazebo* 2>/dev/null
rm -f /dev/shm/fastrtps* 2>/dev/null
rm -f /dev/shm/sem.fastrtps* 2>/dev/null

echo "=== Status ==="
pgrep gz 2>/dev/null && echo "WARNING: Gazebo still running" || echo "Clean — ready to launch"

# Reset ROS2 daemon to clear stale node discovery cache
ros2 daemon stop 2>/dev/null
ros2 daemon start 2>/dev/null
