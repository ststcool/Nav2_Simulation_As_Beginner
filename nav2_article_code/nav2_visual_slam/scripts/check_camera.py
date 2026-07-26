#!/usr/bin/env python3
"""Wait until RGB and depth camera topics have data, then exit.

Usage:
    python3 check_camera.py [--timeout 30]

Exit codes:
    0 = both camera topics ready
    1 = timeout waiting for camera data
"""

import argparse
import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class CameraChecker(Node):

    def __init__(self, timeout_sec):
        super().__init__('camera_checker')
        self.get_logger().info(f'Waiting up to {timeout_sec}s for camera topics...')
        self._rgb_ok = False
        self._depth_ok = False
        self._rgb_sub = self.create_subscription(
            Image, '/camera/image_raw', self._rgb_cb, 10)
        self._depth_sub = self.create_subscription(
            Image, '/camera/depth/image_raw', self._depth_cb, 10)
        self._timer = self.create_timer(timeout_sec, self._timeout_cb)

    def _rgb_cb(self, msg):
        if not self._rgb_ok:
            self._rgb_ok = True
            self.get_logger().info('RGB camera OK')

    def _depth_cb(self, msg):
        if not self._depth_ok:
            self._depth_ok = True
            self.get_logger().info('Depth camera OK')

    def _timeout_cb(self):
        if not self._rgb_ok:
            self.get_logger().warn('TIMEOUT: /camera/image_raw has no data')
        if not self._depth_ok:
            self.get_logger().warn('TIMEOUT: /camera/depth/image_raw has no data')
        sys.exit(0 if (self._rgb_ok and self._depth_ok) else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=30.0,
                        help='Max wait time in seconds')
    args = parser.parse_args()

    rclpy.init()
    node = CameraChecker(args.timeout)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    main()
