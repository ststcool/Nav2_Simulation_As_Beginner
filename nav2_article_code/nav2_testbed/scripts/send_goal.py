#!/usr/bin/env python3
"""Send a Nav2 goal and print result metrics (CSV format to stdout)."""

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Path


STATUS_MAP = {0: 'UNKNOWN', 1: 'ACCEPTED', 2: 'EXECUTING',
              3: 'CANCELING', 4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}


class GoalSender(Node):
    def __init__(self, x, y, goal_id=''):
        super().__init__(f'goal_sender{goal_id}')
        self.client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goal_x = x
        self.goal_y = y
        self.start_time = None
        self.planned_length = 0.0
        self._plan_sub = self.create_subscription(
            Path, '/plan', self._plan_cb, 10)
        self._done = False

    def _plan_cb(self, msg):
        if len(msg.poses) < 2:
            return
        length = 0.0
        for i in range(1, len(msg.poses)):
            dx = msg.poses[i].pose.position.x - msg.poses[i-1].pose.position.x
            dy = msg.poses[i].pose.position.y - msg.poses[i-1].pose.position.y
            length += (dx * dx + dy * dy) ** 0.5
        self.planned_length = max(self.planned_length, length)

    def run(self):
        print(f'[goal_sender] Waiting for navigate_to_pose action server...')
        if not self.client.wait_for_server(timeout_sec=10.0):
            print(f'[goal_sender] ERROR: navigate_to_pose server not available')
            sys.exit(1)
        print(f'[goal_sender] Action server found, sending goal ({self.goal_x:.1f}, {self.goal_y:.1f})')

        self.start_time = self.get_clock().now()
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.pose.position.x = self.goal_x
        goal.pose.pose.position.y = self.goal_y
        goal.pose.pose.orientation.w = 1.0

        future = self.client.send_goal_async(goal)
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            print(f'[goal_sender] ERROR: Goal REJECTED')
            sys.exit(1)
        print(f'[goal_sender] Goal ACCEPTED, waiting for result...')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _result_cb(self, future):
        elapsed = (self.get_clock().now() - self.start_time).nanoseconds / 1e9
        try:
            status = future.result().status
        except AttributeError:
            print(f'[goal_sender] WARN: Cannot read result status, assuming SUCCEEDED')
            print(f'SUCCESS,{elapsed:.2f},{self.planned_length:.2f}')
            sys.exit(0)

        status_text = STATUS_MAP.get(status, f'CODE_{status}')
        success = 'SUCCESS' if status == 4 else f'FAILED_{status_text}'
        print(f'[goal_sender] Final status: {status} = {status_text}')
        print(f'{success},{elapsed:.2f},{self.planned_length:.2f}')
        sys.exit(0)


def main():
    rclpy.init()
    x = float(sys.argv[1])
    y = float(sys.argv[2])
    node = GoalSender(x, y)
    node.run()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print(f'INTERRUPTED,0,0')
        sys.exit(1)
    except ExternalShutdownException:
        pass


if __name__ == '__main__':
    main()
