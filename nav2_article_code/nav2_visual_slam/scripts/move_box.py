#!/usr/bin/env python3
# 来源: nav2_article_code/nav2_algorithm_lab/move_box.py (改造: 增加命令行参数)
"""Drive a moving_box model back and forth along the Y axis via set_entity_state.

Usage:
    python3 move_box.py --x 1.5 --min_y -3.0 --max_y 3.0 --speed 1.5 --model moving_box

推荐参数:
    maze.world:           --x 1.5  --min_y -3.0 --max_y 3.0   (右侧走廊)
    obstacle_course.world: --x 3.0 --min_y -2.0 --max_y 2.0   (贴右围栏内侧, 避开 cyl5/cyl6)
"""

import argparse
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import EntityState


class MoveBox(Node):

    def __init__(self, x, min_y, max_y, speed, model_name):
        super().__init__('move_box')

        self.set_x = x
        self.min_y = min_y
        self.max_y = max_y
        self.speed = speed
        self.model_name = model_name
        self.dt = 0.05
        self.direction = 1.0
        self.current_y = self.min_y
        self.fail_count = 0

        self.cli = self.create_client(SetEntityState, '/set_entity_state')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /set_entity_state ...')
        self.get_logger().info('Connected to /set_entity_state')

        self.timer = self.create_timer(self.dt, self.tick)
        self.get_logger().info(
            f'MoveBox started — x={self.set_x}, '
            f'range [{self.min_y}, {self.max_y}] m, '
            f'speed {self.speed} m/s, model={self.model_name}')

    def tick(self):
        self.current_y += self.direction * self.speed * self.dt
        if self.current_y >= self.max_y:
            self.current_y = self.max_y
            self.direction = -1.0
        elif self.current_y <= self.min_y:
            self.current_y = self.min_y
            self.direction = 1.0

        req = SetEntityState.Request()
        req.state = EntityState()
        req.state.name = f'{self.model_name}::link'
        req.state.pose.position.x = self.set_x
        req.state.pose.position.y = self.current_y
        req.state.pose.position.z = 0.25
        req.state.pose.orientation.w = 1.0
        req.state.reference_frame = 'world'

        future = self.cli.call_async(req)
        future.add_done_callback(self._response_cb)

    def _response_cb(self, future):
        try:
            resp = future.result()
            if not resp.success:
                self.fail_count += 1
                if self.fail_count <= 3:
                    self.get_logger().warn(
                        f'set_entity_state failed: {resp.status_message}')
                elif self.fail_count == 4:
                    self.get_logger().warn('Suppressing further failure logs')
        except Exception as e:
            self.get_logger().error(f'Service call exception: {e}')


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Drive a Gazebo model back and forth along Y axis')
    parser.add_argument('--x', type=float, default=1.5,
                        help='Fixed X coordinate (m)')
    parser.add_argument('--min_y', type=float, default=-3.0,
                        help='Y lower bound (m)')
    parser.add_argument('--max_y', type=float, default=3.0,
                        help='Y upper bound (m)')
    parser.add_argument('--speed', type=float, default=1.5,
                        help='Movement speed (m/s)')
    parser.add_argument('--model', type=str, default='moving_box',
                        help='Gazebo model name')

    parsed, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args if ros_args else None)

    node = MoveBox(
        x=parsed.x,
        min_y=parsed.min_y,
        max_y=parsed.max_y,
        speed=parsed.speed,
        model_name=parsed.model,
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
