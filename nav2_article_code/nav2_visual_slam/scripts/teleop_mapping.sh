#!/bin/bash
# teleop_mapping.sh — 键盘遥控建图助手
# 用法: bash $HOME/nav2_article_code/nav2_visual_slam/scripts/teleop_mapping.sh
#
# 前提: 已启动 visual_slam_launch.py 或 visual_slam_fake_scan_launch.py
#
# 键盘控制:
#   w/x     前进/后退 (增加线速度)
#   a/d     左转/右转 (增加角速度)
#   s       紧急停止
#   空格键   匀速模式 (按住保持当前速度)
#
# 建图技巧:
#   - 慢速匀速移动 (按 w 1-2 次即可，不要一直加速)
#   - 尽量覆盖所有走廊，对每个方向都让相机看一遍
#   - 回到起点附近触发闭环检测

# 恢复终端模式（上轮 Ctrl+C 可能残留异常 termios 状态，导致按键不响应）
stty sane 2>/dev/null

echo "============================================"
echo "  键盘遥控建图 — 操作说明"
echo "============================================"
echo ""
echo "  控制方式:"
echo "    w / x    前进 / 后退"
echo "    a / d    左转 / 右转"
echo "    s 或 空格  停止"
echo ""
echo "  建图技巧:"
echo "    1. 慢速匀速移动 (按 w 1-2 次即可，不要长按)"
echo "    2. 覆盖所有走廊和角落"
echo "    3. 回到起点附近 → 触发闭环检测"
echo "    4. 绕障碍物一圈 → 让相机看到多角度纹理"
echo ""
echo "  完成后在新终端保存地图:"
echo "    ros2 run nav2_map_server map_saver_cli -f <prefix>"
echo "    例如: ros2 run nav2_map_server map_saver_cli -f ~/nav2_visual_slam/maps/my_rtabmap_map"
echo "============================================"
echo ""

ros2 run turtlebot3_teleop teleop_keyboard

# Ctrl+C 退出后恢复终端
stty sane 2>/dev/null
