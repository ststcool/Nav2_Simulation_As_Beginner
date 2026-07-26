#!/usr/bin/env python3
"""Extract ORB features from one camera frame and show them in a window.

Usage:
    python3 extract_features.py [--topic /camera/image_raw]

Output:
    Prints the number of ORB keypoints detected and displays them.

Note: Uses manual ROS Image → numpy conversion (no cv_bridge)
      to avoid NumPy 1.x / 2.x incompatibility with ROS2 Humble.
"""

import argparse
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

_ENCODING_TO_DTYPE = {
    'rgb8':    (np.uint8, 3),
    'bgr8':    (np.uint8, 3),
    'rgba8':   (np.uint8, 4),
    'bgra8':   (np.uint8, 4),
    'mono8':   (np.uint8, 1),
    'mono16':  (np.uint16, 1),
    '8UC1':    (np.uint8, 1),
    '8UC3':    (np.uint8, 3),
    '16UC1':   (np.uint16, 1),
}


def imgmsg_to_cv2(msg):
    """Convert sensor_msgs/Image to OpenCV BGR8 image.
    No cv_bridge dependency — works with NumPy 1.x or 2.x.
    """
    info = _ENCODING_TO_DTYPE.get(msg.encoding)
    if info is None:
        raise ValueError(f'Unsupported encoding: {msg.encoding}')
    dtype, channels = info

    arr = np.frombuffer(msg.data, dtype=dtype)
    if channels == 1:
        arr = arr.reshape(msg.height, msg.width)
    else:
        arr = arr.reshape(msg.height, msg.width, channels)

    if msg.encoding in ('rgb8', 'rgba8'):
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    elif msg.encoding in ('bgra8',):
        arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    return arr


class FeatureExtractor(Node):

    def __init__(self, topic):
        super().__init__('feature_extractor')
        self._done = False
        self._sub = self.create_subscription(Image, topic, self._cb, 1)
        self.get_logger().info(f'Waiting for one frame on {topic}...')

    def _cb(self, msg):
        if self._done:
            return
        self._done = True
        try:
            cv_img = imgmsg_to_cv2(msg)
        except Exception as e:
            self.get_logger().error(f'Image conversion error: {e}')
            raise SystemExit(1)

        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        print(f'ORB keypoints detected: {len(keypoints)}')

        if len(keypoints) == 0:
            self.get_logger().warn('No features found — texture may be too sparse')

        img_kp = cv2.drawKeypoints(cv_img, keypoints, None,
                                   color=(0, 255, 0), flags=0)
        cv2.imshow('ORB Features (press any key to close)', img_kp)
        self.get_logger().info('Press any key in the image window to exit...')
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='/camera/image_raw',
                        help='Camera image topic')
    args = parser.parse_args()

    rclpy.init()
    node = FeatureExtractor(args.topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
