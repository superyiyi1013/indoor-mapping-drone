"""
MAVLink Transport — 基于 pymavlink 直连的通信实现。

运行环境：Windows 地面电脑（或任何有 pymavlink 的环境），
通过数传电台 / UDP / 串口 MAVLink 连接 Pixhawk。
不依赖 ROS。
"""

import time
from typing import Optional

from pymavlink import mavutil

from . import Transport, VehicleState


class MavlinkTransport(Transport):
    """通过 pymavlink MAVLink 直连 Pixhawk。"""

    def __init__(self, connection: str = "udpin:0.0.0.0:14540"):
        self._connection = connection
        self._master = None
        self._local_position = None
        self._home_position = None
        self._landed_state = None
        self._target_system = 0
        self._target_component = 0

    def connect(self) -> None:
        self._master = mavutil.mavlink_connection(
            self._connection,
            autoreconnect=True,
            source_system=255,
            source_component=0,
        )
        heartbeat = self._master.wait_heartbeat(timeout=30)
        if heartbeat is None:
            raise RuntimeError("未收到心跳，请检查数传、端口、波特率和 PX4 MAVLink 实例")
        self._target_system = self._master.target_system
        self._target_component = self._master.target_component

        self._wait_local_position()

    def close(self) -> None:
        if self._master is not None:
            self._master.close()
            self._master = None

    # ── 内部 ──────────────────────────────────────────────

    def _pump_messages(self, timeout: float = 0.0) -> None:
        end = time.monotonic() + (timeout or 0)
        while True:
            wait = max(0.0, min(0.1, end - time.monotonic())) if timeout > 0 else 0
            msg = self._master.recv_match(blocking=timeout > 0, timeout=wait)
            if msg is None:
                return
            mtype = msg.get_type()
            if mtype == "LOCAL_POSITION_NED":
                self._local_position = dict(
                    x=float(msg.x), y=float(msg.y), z=float(msg.z),
                    vx=float(msg.vx), vy=float(msg.vy), vz=float(msg.vz),
                )
            elif mtype == "EXTENDED_SYS_STATE":
                self._landed_state = int(msg.landed_state)
            if timeout > 0 and time.monotonic() >= end:
                return

    def _wait_local_position(self, timeout_s: float = 20.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            self._pump_messages(timeout=0.5)
            if self._local_position is not None:
                self._home_position = dict(self._local_position)
                return
        raise RuntimeError("未收到 LOCAL_POSITION_NED")

    def _wait_command_ack(self, command: int, timeout_s: float = 5.0) -> Optional[int]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            msg = self._master.recv_match(type="COMMAND_ACK", blocking=True, timeout=0.5)
            if msg is None:
                self._pump_messages()
                continue
            if int(msg.command) == int(command):
                return int(msg.result)
        return None

    def _relative_altitude_m(self) -> float:
        if self._home_position is None or self._local_position is None:
            return 0.0
        return max(0.0, self._home_position["z"] - self._local_position["z"])

    def _z_for_altitude(self, alt_m: float) -> float:
        if self._home_position is None:
            raise RuntimeError("缺少起飞前位置基准")
        return self._home_position["z"] - alt_m

    # ── Transport 接口实现 ────────────────────────────────

    def get_state(self) -> VehicleState:
        self._pump_messages(timeout=0.01)
        st = VehicleState()
        st.connected = self._master is not None
        if self._local_position is not None:
            st.x = self._local_position["x"]
            st.y = self._local_position["y"]
            st.z = self._local_position["z"]
        st.yaw = 0.0  # MavlinkTransport 不跟踪 yaw
        st.front_distance_m = None  # MavlinkTransport 不提供避障距离
        return st

    def send_setpoint_local(self, x: float, y: float, z: float,
                            yaw: float = 0.0, use_current_yaw: bool = True) -> None:
        mask = (
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_VY_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
        )
        self._master.mav.set_position_target_local_ned_send(
            int(time.monotonic() * 1000) & 0xFFFFFFFF,
            self._target_system,
            self._target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            mask, x, y, z,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        )

    def set_mode(self, mode: str) -> bool:
        if mode.upper() == "OFFBOARD":
            return self._set_offboard_mode()
        try:
            mode_map = self._master.mode_mapping()
            if mode_map and mode in mode_map:
                self._master.set_mode(mode_map[mode])
                return True
        except Exception:
            pass
        return False

    def _set_offboard_mode(self) -> bool:
        try:
            mode_map = self._master.mode_mapping()
            if mode_map and "OFFBOARD" in mode_map:
                self._master.set_mode(mode_map["OFFBOARD"])
                return True
        except Exception:
            pass
        self._master.mav.command_long_send(
            self._target_system, self._target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6,
            0, 0, 0, 0, 0,
        )
        ack = self._wait_command_ack(mavutil.mavlink.MAV_CMD_DO_SET_MODE)
        return ack in (mavutil.mavlink.MAV_RESULT_ACCEPTED,
                       mavutil.mavlink.MAV_RESULT_IN_PROGRESS)

    def arm(self) -> bool:
        self._master.mav.command_long_send(
            self._target_system, self._target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            1, 0, 0, 0, 0, 0, 0,
        )
        ack = self._wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                                     timeout_s=8.0)
        return ack in (mavutil.mavlink.MAV_RESULT_ACCEPTED,
                       mavutil.mavlink.MAV_RESULT_IN_PROGRESS)

    def disarm(self) -> bool:
        self._master.mav.command_long_send(
            self._target_system, self._target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            0, 0, 0, 0, 0, 0, 0,
        )
        ack = self._wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                                     timeout_s=8.0)
        return ack is not None

    def send_land(self) -> bool:
        self._master.mav.command_long_send(
            self._target_system, self._target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND, 0,
            0, 0, 0, 0, 0, 0, 0,
        )
        ack = self._wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_LAND)
        return ack in (mavutil.mavlink.MAV_RESULT_ACCEPTED,
                       mavutil.mavlink.MAV_RESULT_IN_PROGRESS)

    def has_landed(self) -> bool:
        self._pump_messages(timeout=0.01)
        return self._landed_state == mavutil.mavlink.MAV_LANDED_STATE_ON_GROUND

    # ── MavlinkTransport 专有方法 ──────────────────────────

    def relative_altitude_m(self) -> float:
        """获取当前相对于起飞点的 NED 高度（m）。"""
        return self._relative_altitude_m()

    def wait_on_ground(self, timeout_s: float = 35.0) -> bool:
        """等待 PX4 报告 ON_GROUND，用于确认已落地。"""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            msg = self._master.recv_match(
                type="EXTENDED_SYS_STATE", blocking=True, timeout=0.5
            )
            self._pump_messages()
            if msg is None:
                continue
            if int(msg.landed_state) == mavutil.mavlink.MAV_LANDED_STATE_ON_GROUND:
                return True
        return False
