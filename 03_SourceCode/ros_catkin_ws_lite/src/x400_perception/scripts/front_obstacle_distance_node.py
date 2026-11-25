#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D435i 前向障碍距离节点。

输入：
- D435i 深度图：/camera/depth/image_rect_raw

输出：
- 项目内部前向距离：/x400/obstacle/front_distance
- 可选 MAVROS 距离传感器话题：/mavros/distance_sensor/rangefinder
- 可选 MAVROS obstacle 输入话题：/mavros/obstacle/send

说明：
- 本节点只做第一阶段前向中心区域距离检测，不等于完整三维避障。
- 是否能经 MAVROS 转成 PX4 DISTANCE_SENSOR / OBSTACLE_DISTANCE，需要在机载电脑和 QGC 中实测确认。
"""

import math

import numpy as np
import rospy
from sensor_msgs.msg import Image, LaserScan, Range


class FrontObstacleDistanceNode:
    def __init__(self):
        rospy.init_node("front_obstacle_distance", anonymous=False)

        self.depth_topic = rospy.get_param("~depth_topic", "/camera/depth/image_rect_raw")
        self.distance_topic = rospy.get_param("~distance_topic", "/x400/obstacle/front_distance")
        self.mavros_distance_topic = rospy.get_param("~mavros_distance_topic", "/mavros/distance_sensor/rangefinder")
        self.publish_mavros_range = rospy.get_param("~publish_mavros_range", True)
        self.mavros_obstacle_topic = rospy.get_param("~mavros_obstacle_topic", "/mavros/obstacle/send")
        self.publish_mavros_obstacle = rospy.get_param("~publish_mavros_obstacle", True)

        self.fov_horizontal_deg = rospy.get_param("~fov_horizontal_deg", 87.0)
        self.min_distance_m = rospy.get_param("~min_distance_m", 0.10)
        self.max_distance_m = rospy.get_param("~max_distance_m", 10.0)
        self.roi_ratio = rospy.get_param("~roi_ratio", 0.30)
        self.frame_id = rospy.get_param("~frame_id", "d435i_front_link")
        self.obstacle_scan_bins = max(8, int(rospy.get_param("~obstacle_scan_bins", 72)))

        self.pub_distance = rospy.Publisher(self.distance_topic, Range, queue_size=10)
        self.pub_mavros_distance = None
        if self.publish_mavros_range:
            self.pub_mavros_distance = rospy.Publisher(self.mavros_distance_topic, Range, queue_size=10)
        self.pub_mavros_obstacle = None
        if self.publish_mavros_obstacle:
            self.pub_mavros_obstacle = rospy.Publisher(self.mavros_obstacle_topic, LaserScan, queue_size=10)

        self.sub_depth = rospy.Subscriber(self.depth_topic, Image, self.depth_callback, queue_size=1)

        rospy.loginfo("X400 front obstacle distance node started")
        rospy.loginfo("  depth_topic=%s", self.depth_topic)
        rospy.loginfo("  distance_topic=%s", self.distance_topic)
        rospy.loginfo("  publish_mavros_range=%s", self.publish_mavros_range)
        rospy.loginfo("  publish_mavros_obstacle=%s", self.publish_mavros_obstacle)

    def depth_callback(self, msg):
        try:
            depth_m = self.image_to_depth_meters(msg)
            distance = self.compute_front_distance(depth_m)
            self.publish_range(distance)
        except Exception as exc:
            rospy.logerr_throttle(1.0, "Depth processing error: %s", exc)

    def image_to_depth_meters(self, msg):
        if msg.encoding in ("16UC1", "mono16"):
            depth = np.frombuffer(msg.data, dtype=np.uint16).reshape((msg.height, msg.width))
            return depth.astype(np.float32) / 1000.0

        if msg.encoding == "32FC1":
            return np.frombuffer(msg.data, dtype=np.float32).reshape((msg.height, msg.width))

        raise ValueError("Unsupported depth encoding: %s" % msg.encoding)

    def compute_front_distance(self, depth_m):
        height, width = depth_m.shape
        roi_width = max(1, int(width * self.roi_ratio))
        roi_height = max(1, int(height * self.roi_ratio))

        x0 = max(0, width // 2 - roi_width // 2)
        x1 = min(width, width // 2 + roi_width // 2)
        y0 = max(0, height // 2 - roi_height // 2)
        y1 = min(height, height // 2 + roi_height // 2)

        roi = depth_m[y0:y1, x0:x1]
        valid = np.isfinite(roi) & (roi >= self.min_distance_m) & (roi <= self.max_distance_m)
        if not valid.any():
            return self.max_distance_m

        return float(np.nanpercentile(roi[valid], 10))

    def publish_range(self, distance):
        msg = Range()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = self.frame_id
        msg.radiation_type = Range.INFRARED
        msg.field_of_view = math.radians(self.fov_horizontal_deg)
        msg.min_range = self.min_distance_m
        msg.max_range = self.max_distance_m
        msg.range = max(self.min_distance_m, min(distance, self.max_distance_m))

        self.pub_distance.publish(msg)
        if self.pub_mavros_distance is not None:
            self.pub_mavros_distance.publish(msg)
        if self.pub_mavros_obstacle is not None:
            self.pub_mavros_obstacle.publish(self.build_obstacle_scan(msg))

    def build_obstacle_scan(self, range_msg):
        fov_rad = math.radians(self.fov_horizontal_deg)
        angle_increment = (2.0 * math.pi) / float(self.obstacle_scan_bins)
        scan = LaserScan()
        scan.header = range_msg.header
        scan.angle_min = -math.pi
        scan.angle_max = math.pi - angle_increment
        scan.angle_increment = angle_increment
        scan.time_increment = 0.0
        scan.scan_time = 1.0 / 15.0
        scan.range_min = range_msg.min_range
        scan.range_max = range_msg.max_range
        scan.ranges = [
            range_msg.range if abs(self.normalize_angle(scan.angle_min + i * angle_increment)) <= 0.5 * fov_rad else math.inf
            for i in range(self.obstacle_scan_bins)
        ]
        scan.intensities = []
        return scan

    @staticmethod
    def normalize_angle(angle):
        return math.atan2(math.sin(angle), math.cos(angle))

    def run(self):
        rospy.spin()


def main():
    try:
        FrontObstacleDistanceNode().run()
    except rospy.ROSInterruptException:
        pass


if __name__ == "__main__":
    main()
