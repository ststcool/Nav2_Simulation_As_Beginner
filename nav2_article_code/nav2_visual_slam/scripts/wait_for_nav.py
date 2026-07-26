# 来源: nav2_article_code/nav2_testbed/scripts/wait_for_nav.py
#!/usr/bin/env python3
"""Wait for Nav2 stack and AMCL to be ready. Exit 0 if ready, 1 on timeout."""

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose


class WaitForNav(Node):
    def __init__(self, max_wait=90):
        super().__init__('wait_for_nav')
        self.max_wait = max_wait
        self.client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    def check(self):
        return self.client.wait_for_server(timeout_sec=1.0)


def main():
    rclpy.init()
    max_wait = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    node = WaitForNav(max_wait)
    elapsed = 0
    while elapsed < max_wait:
        ok = node.check()
        elapsed += 1
        if ok:
            print('READY')
            sys.exit(0)
    print('TIMEOUT')
    sys.exit(1)


if __name__ == '__main__':
    main()
