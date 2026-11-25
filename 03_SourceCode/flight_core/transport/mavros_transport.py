"""
MAVROS Transport — 基于 ROS + MAVROS 的通信实现。

运行环境：机载电脑 Ubuntu 20.04 + ROS Noetic + MAVROS。
使用前需先启动 MAVROS 节点和 roscore。
"""

import math
import time

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import ExtendedState, State
from mavros_msgs.srv import CommandBool, SetMode
from sensor_msgs.msg import Range

from . import Transport, VehicleState


class MavrosTransport(Transport):
    """通过 MAVROS topic/service 与 Pixhawk 通信。"""

    def __init__(self, range_topic: str = "/x400/obstacle/front_distance",
                 setpoint_hz: float = 10.0,
                 ready_timeout: float = 30.0):
        self._range_topic = range_topic
        self._setpoint_hz = setpoint_hz
        self._ready_timeout = ready_timeout
        self._ros_initialised = False

        self._state = State()
        self._extended_state = ExtendedState()
        self._pose = None
        self._front_range = None
        self._pub = None
        self._set_mode_srv = None
        self._arm_srv = None

    def connect(self) -> None:
        if not self._ros_initialised:
            if not rospy.core.is_initialized():
                rospy.init_node("flight_core_mavros", anonymous=True)
            self._ros_initialised = True

        self._pub = rospy.Publisher(
            "/mavros/setpoint_position/local", PoseStamped, queue_size=10
        )
        rospy.Subscriber("/mavros/state", State, self._state_cb)
        rospy.Subscriber("/mavros/extended_state", ExtendedState, self._extended_state_cb)
        rospy.Subscriber("/mavros/local_position/pose", PoseStamped, self._pose_cb)
        rospy.Subscriber(self._range_topic, Range, self._range_cb)

        rospy.wait_for_service("/mavros/set_mode", timeout=20)
        rospy.wait_for_service("/mavros/cmd/arming", timeout=20)
        self._set_mode_srv = rospy.ServiceProxy("/mavros/set_mode", SetMode)
        self._arm_srv = rospy.ServiceProxy("/mavros/cmd/arming", CommandBool)

        self._wait_ready()

    def close(self) -> None:
        if self._pub is not None:
            self._pub.unregister()
        # ROS Subscriber/ServiceProxy 随节点生命周期释放

    # ── 回调 ──────────────────────────────────────────────

    def _state_cb(self, msg: State) -> None:
        self._state = msg

    def _extended_state_cb(self, msg: ExtendedState) -> None:
        self._extended_state = msg

    def _pose_cb(self, msg: PoseStamped) -> None:
        self._pose = msg

    def _range_cb(self, msg: Range) -> None:
        self._front_range = msg.range

    # ── 内部 ──────────────────────────────────────────────

    def _wait_ready(self) -> None:
        deadline = time.time() + self._ready_timeout
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and time.time() < deadline:
            if self._state.connected and self._pose is not None:
                return
            rate.sleep()
        raise RuntimeError("MAVROS 未连接，或本地位置数据不可用")

    def _yaw_from_pose(self) -> float:
        if self._pose is None:
            return 0.0
        q = self._pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw_enu = math.atan2(siny_cosp, cosy_cosp)
        return self._wrap_pi((math.pi * 0.5) - yaw_enu)

    @staticmethod
    def _wrap_pi(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    # ── Transport 接口实现 ────────────────────────────────

    def get_state(self) -> VehicleState:
        st = VehicleState()
        st.connected = self._state.connected
        st.armed = self._state.armed
        st.mode = self._state.mode
        if self._pose is not None:
            p = self._pose.pose.position
            # MAVROS local_position/pose is ENU. The Transport interface used by
            # Fly is local NED, so convert at the ROS boundary.
            st.x = p.y
            st.y = p.x
            st.z = -p.z
        st.yaw = self._yaw_from_pose()
        st.front_distance_m = self._front_range
        return st

    def send_setpoint_local(self, x: float, y: float, z: float,
                            yaw: float = 0.0, use_current_yaw: bool = True) -> None:
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        # Convert Transport NED setpoint to MAVROS ENU PoseStamped.
        msg.pose.position.x = y
        msg.pose.position.y = x
        msg.pose.position.z = -z
        if use_current_yaw and self._pose is not None:
            msg.pose.orientation = self._pose.pose.orientation
        else:
            # yaw → quaternion (只绕 Z 轴)
            half = yaw * 0.5
            msg.pose.orientation.z = math.sin(half)
            msg.pose.orientation.w = math.cos(half)
        self._pub.publish(msg)

    def set_mode(self, mode: str) -> bool:
        if self._set_mode_srv is None:
            return False
        try:
            resp = self._set_mode_srv(custom_mode=mode)
            return resp.mode_sent
        except rospy.ServiceException:
            return False

    def arm(self) -> bool:
        if self._arm_srv is None:
            return False
        try:
            resp = self._arm_srv(True)
            return resp.success
        except rospy.ServiceException:
            return False

    def disarm(self) -> bool:
        if self._arm_srv is None:
            return False
        try:
            resp = self._arm_srv(False)
            return resp.success
        except rospy.ServiceException:
            return False

    def send_land(self) -> bool:
        return self.set_mode("AUTO.LAND")

    def has_landed(self) -> bool:
        return self._extended_state.landed_state == ExtendedState.LANDED_STATE_ON_GROUND
