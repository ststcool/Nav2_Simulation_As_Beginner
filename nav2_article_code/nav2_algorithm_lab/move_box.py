#!/usr/bin/env python3
"""Drive the moving_box model back and forth along the Y axis via set_entity_state."""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import EntityState


class MoveBox(Node):

    def __init__(self):
        super().__init__('move_box')
        self.cli = self.create_client(SetEntityState, '/set_entity_state')
        self.fail_count = 0
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /set_entity_state ...')
        self.get_logger().info('Connected to /set_entity_state')

        self.min_y = -3.0
        self.max_y = 3.0
        self.current_y = self.min_y
        self.speed = 1.5          # m/s
        self.dt = 0.05            # 20 Hz update rate
        self.direction = 1.0      # +1 moving up, -1 moving down

        self.timer = self.create_timer(self.dt, self.tick)
        self.get_logger().info(
            f'MoveBox started — range [{self.min_y}, {self.max_y}] m, '
            f'speed {self.speed} m/s')

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
        req.state.name = 'moving_box::link'
        req.state.pose.position.x = 1.5
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
    rclpy.init(args=args)
    node = MoveBox()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
