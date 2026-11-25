"""
Fly 层 — 飞行原语。

所有方法只依赖 Transport 接口，不依赖 pymavlink 或 ROS。
安全参数来自 safety_config，可通过构造函数覆盖。

每个飞行原语都是同步阻塞的——执行完毕后返回，或异常时抛出。

起飞基准约定：
  takeoff() 执行时记录 3 个 home 值（x/y/z NED 坐标），
  后续 hover/land/move_forward 全部以这组值为基准，
  确保所有飞行阶段 XY 不漂、高度参考一致。
"""

import math
import time
from typing import Callable, Optional, Tuple

from .transport import Transport, VehicleState
from . import safety_config as sc


class FlyError(RuntimeError):
    """飞行异常。"""
    pass


class Fly:
    """运输无关的飞行控制器。"""

    def __init__(self, transport: Transport):
        self.t = transport
        self._home_x: Optional[float] = None
        self._home_y: Optional[float] = None
        self._home_z: Optional[float] = None

    # ── connect / close ────────────────────────────────────

    def connect(self) -> None:
        """建立连接并验证链路。"""
        self.t.connect()

    def close(self) -> None:
        """关闭连接。"""
        self.t.close()

    @property
    def is_home_set(self) -> bool:
        """是否已记录起飞基准（takeoff() 被调用过）。"""
        return self._home_z is not None

    # ── takeoff ───────────────────────────────────────────

    def takeoff(self, target_alt_m: float = sc.DEFAULT_TARGET_ALT_M) -> None:
        """
        起飞到目标高度。

        流程：
        1. 地面静止采样位置 → 设为本次 home/高度基准
        2. 预发台阶 setpoint → 切 OFFBOARD → 解锁
        3. 起跳段：给 0.70m 台阶目标，先明确离地并脱离地面效应
        4. 爬升段：从台阶目标单调爬升到 target_alt_m，setpoint 不回缩
        5. 到达目标高度后返回
        """
        if target_alt_m <= 0.0 or target_alt_m > sc.MAX_SAFE_ALT_M:
            raise ValueError(
                "目标高度 {:.2f}m 必须在 (0.0, {:.2f}] 范围内".format(
                    target_alt_m, sc.MAX_SAFE_ALT_M
                )
            )

        # ── 记录本次地面基准（显式缓存，不用懒加载） ──
        self._record_ground_baseline()

        liftoff_alt_m = min(sc.LIFTOFF_TARGET_ALT_M, target_alt_m)
        target_z = self._home_z - target_alt_m
        liftoff_z = self._home_z - liftoff_alt_m

        # 预发送 setpoint
        self._publish_setpoint_for(
            self._home_x, self._home_y, liftoff_z,
            sc.PRESEND_OFFBOARD_DURATION_S
        )

        # 切 OFFBOARD
        if not self.t.set_mode("OFFBOARD"):
            raise FlyError("PX4 拒绝切入 OFFBOARD 模式")

        self._publish_setpoint_for(self._home_x, self._home_y, liftoff_z, 1.0)

        # 解锁
        if not self.t.arm():
            raise FlyError("PX4 拒绝解锁请求")

        # 起跳段
        self._liftoff_from_ground(liftoff_z, liftoff_alt_m, target_alt_m)

        # 爬升段
        self._climb_to_altitude(target_alt_m, target_z, liftoff_alt_m)

    # ── hover ─────────────────────────────────────────────

    def hover(self, duration_s: float = sc.DEFAULT_HOVER_TIME_S,
              alt_m: Optional[float] = None) -> None:
        """
        在起飞基准 XY 上悬停 duration_s 秒。

        alt_m: 悬停高度（m，相对起飞点）。默认保持当前高度。
        """
        target_z = self._hover_target_z(alt_m)
        deadline = time.monotonic() + duration_s
        last_print = 0.0

        while time.monotonic() < deadline:
            self.t.send_setpoint_local(self._home_x, self._home_y, target_z)
            now = time.monotonic()
            if now - last_print > 1.0:
                s = self.t.get_state()
                rel_alt = self._home_z - s.z
                remaining = max(0, int(deadline - now))
                print("悬停中：高度≈{:.2f}m，剩余={}s".format(rel_alt, remaining))
                last_print = now
            time.sleep(sc.SETPOINT_DT)

    # ── move_forward ───────────────────────────────────────

    def move_forward(self, distance_m: float,
                     speed_mps: float = sc.DEFAULT_FORWARD_SPEED_MPS,
                     alt_m: Optional[float] = None) -> None:
        """
        沿机头方向前进 distance_m 米。

        distance_m: 前进距离（m），正数=前，负数=后
        speed_mps: 前进速率
        alt_m: 保持的目标高度（相对于起飞点），默认不改变当前高度

        注意：当前 yaw 从 transport.get_state().yaw 获取。
        若 transport 不提供 yaw（返回 0），move_forward 默认往北飞
        （MAV_FRAME_LOCAL_NED 的 X+ 方向）。这是 MavlinkTransport
        的已知限制——需要机载电脑 + MAVROS 才能做机头方向前进。
        """
        if abs(distance_m) > sc.MAX_FORWARD_DISTANCE_M:
            raise ValueError(
                "前进距离 {:.2f}m 超过上限 {:.2f}m".format(
                    distance_m, sc.MAX_FORWARD_DISTANCE_M
                )
            )
        if speed_mps <= 0.0 or speed_mps > sc.MAX_FORWARD_SPEED_MPS:
            raise ValueError(
                "前进速率 {:.2f} 必须在 (0.0, {:.2f}] 范围内".format(
                    speed_mps, sc.MAX_FORWARD_SPEED_MPS
                )
            )

        state = self.t.get_state()
        yaw = state.yaw
        if yaw == 0.0:
            print("警告：当前 yaw 读数为 0，前进方向默认为 NED X+（北）。"
                  "如果这不是你的意图，请检查 transport 是否支持 yaw。")

        target_z = self._hover_target_z(alt_m)
        dx_total = math.cos(yaw) * distance_m
        dy_total = math.sin(yaw) * distance_m

        travel_time = max(3.0, abs(distance_m) / speed_mps)
        steps = max(1, int(travel_time * sc.SETPOINT_HZ))

        print("以约 {:.2f} m/s 速度移动 {:.2f} m...".format(speed_mps, distance_m))
        for i in range(steps):
            ratio = float(i + 1) / float(steps)
            self.t.send_setpoint_local(
                self._home_x + dx_total * ratio,
                self._home_y + dy_total * ratio,
                target_z,
            )
            time.sleep(sc.SETPOINT_DT)

    # ── move_forward_until ────────────────────────────────

    def move_forward_until(self, max_distance_m: float,
                           stop_condition: Callable[[VehicleState], bool],
                           speed_mps: float = sc.DEFAULT_FORWARD_SPEED_MPS,
                           alt_m: Optional[float] = None,
                           max_time_s: float = 8.0) -> float:
        """
        沿机头方向前进，直到 stop_condition 返回 True 或达到 max_distance_m。

        返回实际移动距离（m）。

        stop_condition 每步调用一次，接收当前 VehicleState。
        典型用法：
            stop_condition=lambda s: s.front_distance_m is not None
                and s.front_distance_m <= 1.0
        """
        if max_distance_m <= 0.0 or max_distance_m > sc.MAX_FORWARD_DISTANCE_M:
            raise ValueError(
                "前进距离 {:.2f}m 超过上限 {:.2f}m".format(
                    max_distance_m, sc.MAX_FORWARD_DISTANCE_M
                )
            )

        state = self.t.get_state()
        yaw = state.yaw
        if yaw == 0.0:
            print("警告：当前 yaw 读数为 0，前进方向默认为 NED X+（北）。")

        target_z = self._hover_target_z(alt_m)
        max_steps = max(1, int(max_time_s * sc.SETPOINT_HZ))
        moved = 0.0

        print("开始低速前进：最大 {:.2f} m，或满足停止条件时中止。".format(max_distance_m))
        for _ in range(max_steps):
            s = self.t.get_state()
            if stop_condition(s):
                print("停止条件满足，已在 {:.2f} m 处停止。".format(moved))
                return moved

            moved = min(max_distance_m, moved + speed_mps / sc.SETPOINT_HZ)
            self.t.send_setpoint_local(
                self._home_x + math.cos(yaw) * moved,
                self._home_y + math.sin(yaw) * moved,
                target_z,
            )
            if moved >= max_distance_m:
                print("已达到最大前进距离 {:.2f} m。".format(max_distance_m))
                return moved
            time.sleep(sc.SETPOINT_DT)

        print("前进超时，已在 {:.2f} m 处停止。".format(moved))
        return moved

    # ── yaw ────────────────────────────────────────────────

    @staticmethod
    def _yaw_diff(target_rad: float, current_rad: float) -> float:
        """计算最短偏航角差（弧度），范围 [-π, π]。"""
        return math.atan2(math.sin(target_rad - current_rad),
                          math.cos(target_rad - current_rad))

    def yaw_to(self, target_yaw_rad: float) -> None:
        """
        原地旋转到目标偏航角（NED 弧度），阻塞直到到位或超时。

        锁定当前位置不变，仅旋转 yaw。到位判定：角差 ≤ YAW_TOLERANCE_DEG。
        """
        if not self.is_home_set:
            raise FlyError("未记录起飞基准，无法执行偏航旋转")

        tol_rad = math.radians(sc.YAW_TOLERANCE_DEG)
        deadline = time.monotonic() + sc.YAW_TIMEOUT_S
        last_print = 0.0

        # 锁定当前位置
        s = self.t.get_state()
        hold_x, hold_y, hold_z = s.x, s.y, s.z

        print("偏航旋转：目标={:.1f}°...".format(math.degrees(target_yaw_rad)))

        while time.monotonic() < deadline:
            self.t.send_setpoint_local(hold_x, hold_y, hold_z,
                                       yaw=target_yaw_rad,
                                       use_current_yaw=False)

            s = self.t.get_state()
            diff = self._yaw_diff(target_yaw_rad, s.yaw)
            now = time.monotonic()

            if now - last_print > 0.5:
                print("偏航旋转中：当前={:.1f}°，偏差={:.1f}°".format(
                    math.degrees(s.yaw), math.degrees(diff)
                ))
                last_print = now

            if abs(diff) <= tol_rad:
                print("偏航到位：当前={:.1f}°".format(math.degrees(s.yaw)))
                return

            time.sleep(sc.SETPOINT_DT)

        raise FlyError("偏航旋转超时 {:.0f}s，当前偏差={:.1f}°".format(
            sc.YAW_TIMEOUT_S,
            math.degrees(self._yaw_diff(target_yaw_rad, self.t.get_state().yaw))
        ))

    # ── local waypoint ─────────────────────────────────────

    def get_relative_position(self) -> Tuple[float, float, float]:
        """Return current position relative to takeoff home as (x, y, alt_m)."""
        if not self.is_home_set:
            raise FlyError("未记录起飞基准，无法计算相对坐标")
        s = self.t.get_state()
        return s.x - self._home_x, s.y - self._home_y, self._home_z - s.z

    def body_forward_offset(self, distance_m: float) -> Tuple[float, float]:
        """Return a home-relative NED XY offset for current body-forward distance."""
        yaw = self.t.get_state().yaw
        return math.cos(yaw) * distance_m, math.sin(yaw) * distance_m

    def hold_at_offset(self, offset_x: float, offset_y: float,
                       alt_m: float, duration_s: float) -> None:
        """Hold a home-relative local waypoint for duration_s seconds."""
        if not self.is_home_set:
            raise FlyError("未记录起飞基准，无法执行局部航点悬停")
        target_x = self._home_x + offset_x
        target_y = self._home_y + offset_y
        target_z = self._home_z - alt_m
        deadline = time.monotonic() + duration_s
        last_print = 0.0
        while time.monotonic() < deadline:
            self.t.send_setpoint_local(target_x, target_y, target_z)
            now = time.monotonic()
            if now - last_print > 1.0:
                s = self.t.get_state()
                err = math.hypot(target_x - s.x, target_y - s.y)
                rel_alt = self._home_z - s.z
                print("航点悬停中：XY误差≈{:.2f}m，高度≈{:.2f}m".format(err, rel_alt))
                last_print = now
            time.sleep(sc.SETPOINT_DT)

    def move_to_local_offset(self, offset_x: float, offset_y: float,
                             alt_m: float, speed_mps: float,
                             tolerance_m: float = 0.15,
                             max_time_s: Optional[float] = None) -> float:
        """Move to a home-relative local waypoint and return final XY error."""
        if not self.is_home_set:
            raise FlyError("未记录起飞基准，无法执行局部航点飞行")
        if speed_mps <= 0.0 or speed_mps > sc.MAX_FORWARD_SPEED_MPS:
            raise ValueError(
                "航点速度 {:.2f} 必须在 (0.0, {:.2f}] 范围内".format(
                    speed_mps, sc.MAX_FORWARD_SPEED_MPS
                )
            )
        if tolerance_m <= 0.0:
            raise ValueError("航点容差必须大于 0")
        target_dist = math.hypot(offset_x, offset_y)
        if target_dist > sc.MAX_FORWARD_DISTANCE_M:
            raise ValueError(
                "航点水平距离 {:.2f}m 超过上限 {:.2f}m".format(
                    target_dist, sc.MAX_FORWARD_DISTANCE_M
                )
            )
        if alt_m <= 0.0 or alt_m > sc.MAX_SAFE_ALT_M:
            raise ValueError(
                "航点高度 {:.2f}m 必须在 (0.0, {:.2f}] 范围内".format(
                    alt_m, sc.MAX_SAFE_ALT_M
                )
            )

        start = self.t.get_state()
        start_x = start.x
        start_y = start.y
        target_x = self._home_x + offset_x
        target_y = self._home_y + offset_y
        target_z = self._home_z - alt_m
        path_dist = math.hypot(target_x - start_x, target_y - start_y)
        travel_time = max(2.0, path_dist / speed_mps) if path_dist > 0.01 else 2.0
        deadline = time.monotonic() + (max_time_s or travel_time + 6.0)
        steps = max(1, int(travel_time * sc.SETPOINT_HZ))

        print("飞向局部航点：offset=({:.2f}, {:.2f})m，高度={:.2f}m，速度≈{:.2f}m/s".format(
            offset_x, offset_y, alt_m, speed_mps
        ))
        last_print = 0.0
        final_err = path_dist

        for i in range(steps):
            ratio = float(i + 1) / float(steps)
            cmd_x = start_x + (target_x - start_x) * ratio
            cmd_y = start_y + (target_y - start_y) * ratio
            self.t.send_setpoint_local(cmd_x, cmd_y, target_z)
            s = self.t.get_state()
            final_err = math.hypot(target_x - s.x, target_y - s.y)
            now = time.monotonic()
            if now - last_print > 1.0:
                print("航点飞行中：XY误差≈{:.2f}m".format(final_err))
                last_print = now
            time.sleep(sc.SETPOINT_DT)

        while time.monotonic() < deadline:
            self.t.send_setpoint_local(target_x, target_y, target_z)
            s = self.t.get_state()
            final_err = math.hypot(target_x - s.x, target_y - s.y)
            now = time.monotonic()
            if now - last_print > 1.0:
                print("等待进入航点容差：XY误差≈{:.2f}m，容差={:.2f}m".format(
                    final_err, tolerance_m
                ))
                last_print = now
            if final_err <= tolerance_m:
                print("已到达局部航点：XY误差={:.2f}m".format(final_err))
                return final_err
            time.sleep(sc.SETPOINT_DT)

        raise FlyError("航点到达超时：最终XY误差={:.2f}m，容差={:.2f}m".format(
            final_err, tolerance_m
        ))
    # ── glide land ─────────────────────────────────────────

    def glide_land(self, target_ox: float = 0.0, target_oy: float = 0.0,
                   alt_m: float = 1.0, angle_deg: float = 45.0) -> None:
        """
        45° 俯角滑降着陆。

        从当前位置飞到滑降起点（目标点正前方），沿指定角度同时下降+前进，
        降到 0.3m 后交 AUTO.LAND 完成触地上锁。

        target_ox, target_oy: 目标落点的 home 相对偏移
        alt_m:              当前飞行高度（相对 home）
        angle_deg:          滑降角度（°），默认 45
        """
        if not self.is_home_set:
            raise FlyError("未记录起飞基准，无法执行滑降着陆")

        angle_rad = math.radians(angle_deg)
        # 滑降起点与目标点的水平距离
        glide_dist = alt_m / math.tan(angle_rad)
        # 滑降方向与当前机头方向一致
        yaw = self.t.get_state().yaw
        glide_dir_x = math.cos(yaw)
        glide_dir_y = math.sin(yaw)

        start_ox = target_ox - glide_dir_x * glide_dist
        start_oy = target_oy - glide_dir_y * glide_dist
        target_x = self._home_x + target_ox
        target_y = self._home_y + target_oy

        # 先飞到滑降起点
        print("滑降着陆：先飞到滑降起点 offset=({:.2f}, {:.2f})".format(
            start_ox, start_oy
        ))
        self.move_to_local_offset(
            start_ox, start_oy, alt_m=alt_m,
            speed_mps=sc.DEFAULT_FORWARD_SPEED_MPS,
            tolerance_m=0.15,
        )

        # LED 闪烁提示（打印提示，硬件触发由 Task 层处理）
        print("=== LED 闪烁：开始 45° 滑降着陆 ===")

        # 沿滑降线飞行
        glide_start = self.t.get_state()
        glide_start_x = glide_start.x
        glide_start_y = glide_start.y
        path_dist = math.hypot(target_x - glide_start_x, target_y - glide_start_y)
        travel_time = path_dist / sc.DEFAULT_FORWARD_SPEED_MPS
        steps = max(1, int(travel_time * sc.SETPOINT_HZ))
        last_print = 0.0

        print("滑降中：角度={:.0f}°，目标落点=({:.2f}, {:.2f})".format(
            angle_deg, target_ox, target_oy
        ))

        for i in range(steps + 1):
            ratio = float(i) / float(max(steps, 1))
            cmd_x = glide_start_x + (target_x - glide_start_x) * ratio
            cmd_y = glide_start_y + (target_y - glide_start_y) * ratio
            cmd_alt = alt_m * (1.0 - ratio)
            cmd_z = self._home_z - cmd_alt

            self.t.send_setpoint_local(cmd_x, cmd_y, cmd_z)

            s = self.t.get_state()
            rel_alt = self._home_z - s.z
            now = time.monotonic()
            if now - last_print > 0.5:
                dist_remain = math.hypot(target_x - s.x, target_y - s.y)
                print("滑降中：高度={:.2f}m，水平剩余={:.2f}m".format(
                    rel_alt, dist_remain
                ))
                last_print = now

            # 降到 0.3m 以下交给 AUTO.LAND
            if rel_alt <= sc.TOUCHDOWN_BOTTOM_ALT_M + 0.12:
                print("滑降着陆：高度={:.2f}m，切换 AUTO.LAND".format(rel_alt))
                break

            time.sleep(sc.SETPOINT_DT)

        # 交给 AUTO.LAND
        self.t.send_land()
        print("已发 NAV_LAND，等待着陆完成...")
        time.sleep(5.0)

    # ── land ───────────────────────────────────────────────

    def land(self) -> None:
        """
        Offboard 分段慢速下降到底，检测触地后上锁。

        降落开始时锁定起飞基准 XY（home_x/home_y），使飞机在下降过程中
        回到起飞点附近。低空段同样使用同一 XY，避免贴地时位置抖动导致
        横向修正。
        触地确认必须同时满足下降目标到底和实际相对高度低于严格阈值。
        """
        if self.is_home_set:
            start = self.t.get_state()
            start_alt_m = self._home_z - start.z
            home_z = self._home_z
            land_x = self._home_x
            land_y = self._home_y
        else:
            start = self.t.get_state()
            start_alt_m = 0.5  # 安全猜测
            home_z = start.z
            land_x = start.x
            land_y = start.y
            print("警告：未记录起飞基准，使用当前位置作为地面参考。")

        print(
            "Offboard 分段下降：高空速度={:.2f}m/s，低空<{:.2f}m 后速度={:.2f}m/s，使用降落锁定XY，触地阈值<={:.2f}m，确认 {:.1f}s...".format(
                sc.DESCEND_RATE_MPS,
                sc.LAND_FINAL_ALT_M,
                sc.LAND_FINAL_DESCEND_RATE_MPS,
                sc.TOUCHDOWN_BOTTOM_ALT_M,
                sc.TOUCHDOWN_BOTTOM_HOLD_S,
            )
        )
        start_time = time.monotonic()
        print("降落锁定XY=({:.2f}, {:.2f})，低空段不再更新XY。".format(
            land_x, land_y
        ))
        touchdown_start = None
        last_print = 0.0
        last_bottom_wait_print = 0.0
        final_phase = False
        final_phase_start = None
        final_phase_start_alt = None
        last_commanded_alt = max(0.0, start_alt_m)

        while True:
            elapsed = time.monotonic() - start_time
            s = self.t.get_state()
            rel_alt = home_z - s.z
            now = time.monotonic()

            if not final_phase and rel_alt <= sc.LAND_FINAL_ALT_M:
                final_phase = True
                final_phase_start = now
                final_phase_start_alt = last_commanded_alt
                # 低空段不再读取当前 XY，避免贴地位置估计跳变造成横向修正。
                print("进入低空降落段：高度={:.2f}m，继续使用降落锁定XY=({:.2f}, {:.2f})。".format(
                    rel_alt, land_x, land_y
                ))

            if final_phase:
                phase_elapsed = now - final_phase_start
                raw_commanded_alt = max(
                    0.0,
                    final_phase_start_alt - sc.LAND_FINAL_DESCEND_RATE_MPS * phase_elapsed,
                )
            else:
                raw_commanded_alt = max(0.0, start_alt_m - sc.DESCEND_RATE_MPS * elapsed)

            commanded_alt = min(raw_commanded_alt, last_commanded_alt)
            last_commanded_alt = commanded_alt
            alt_z = home_z - commanded_alt
            self.t.send_setpoint_local(land_x, land_y, alt_z)

            if now - last_print > 1.0:
                phase = "低空" if final_phase else "高空"
                print("{}下降：当前相对高度={:.2f}m，下降目标={:.2f}m".format(
                    phase, rel_alt, commanded_alt
                ))
                last_print = now

            touchdown_zone = commanded_alt <= 0.001 and rel_alt <= sc.TOUCHDOWN_BOTTOM_ALT_M
            if touchdown_zone:
                if touchdown_start is None:
                    touchdown_start = now
                    print("触地候选：高度={:.2f}m，开始确认 {:.1f}s...".format(
                        rel_alt, sc.TOUCHDOWN_BOTTOM_HOLD_S
                    ))
                elif now - touchdown_start >= sc.TOUCHDOWN_BOTTOM_HOLD_S:
                    self._disarm_after_touchdown("触地确认", rel_alt)
                    return
            else:
                if commanded_alt <= 0.001 and now - last_bottom_wait_print > 1.0:
                    print("下降目标已到底，但高度={:.2f}m 未达到触地阈值<={:.2f}m，继续等待。".format(
                        rel_alt, sc.TOUCHDOWN_BOTTOM_ALT_M
                    ))
                    last_bottom_wait_print = now
                touchdown_start = None

            if elapsed > sc.DESCENT_TIMEOUT_S:
                raise FlyError(
                    "下降超时：下降目标已到底但未满足触地阈值（当前高度={:.2f}m，阈值={:.2f}m），请人工确认后接管/上锁".format(
                        rel_alt, sc.TOUCHDOWN_BOTTOM_ALT_M
                    )
                )

            time.sleep(sc.SETPOINT_DT)

    def _disarm_after_touchdown(self, reason: str, rel_alt: float) -> None:
        """
        触地确认后切入 AUTO.LAND，让 PX4 完成着陆检测和自动上锁。

        OFFBOARD 模式下持续发送地面 setpoint 会阻塞 PX4 的着陆检测，
        导致 MAVLink disarm 被拒绝（vehicle_land_detected.landed=false）。

        改为切入 AUTO.LAND 模式后，PX4 在 AUTO 模式下的着陆检测器
        能正常检测触地，然后 COM_DISARM_LAND 自动触发上锁。
        """
        print("{}完成，切入 AUTO.LAND 完成着陆上锁。".format(reason))
        self.t.send_land()

        # 等待自动上锁（COM_DISARM_LAND=1.0s + 着陆检测余量）
        deadline = time.monotonic() + sc.LAND_DISARM_WAIT_S
        while time.monotonic() < deadline:
            s = self.t.get_state()
            if not s.armed:
                print("已上锁，降落完成。")
                return
            time.sleep(sc.SETPOINT_DT)

        print("AUTO.LAND 上锁超时（{}s），尝试直接 disarm...".format(sc.LAND_DISARM_WAIT_S))
        for attempt in range(1, sc.DISARM_RETRY_COUNT + 1):
            ok = self.t.disarm()
            time.sleep(sc.DISARM_RECHECK_DELAY_S)
            armed = self.t.get_state().armed
            print("上锁尝试 {}/{}：service_ok={}，armed={}".format(
                attempt, sc.DISARM_RETRY_COUNT, ok, armed
            ))
            if not armed:
                print("已上锁，降落完成。")
                return

        raise FlyError("触地后标准上锁失败（高度={:.2f}m），请立即遥控器接管！".format(rel_alt))

    # ── 内部方法 ───────────────────────────────────────────

    def _record_ground_baseline(self) -> None:
        """采样地面静止位置，建立本次任务高度基准。"""
        deadline = time.monotonic() + sc.GROUND_BASELINE_DURATION_S
        samples = []
        print("起飞前采样地面高度基准 {:.1f}s...".format(
            sc.GROUND_BASELINE_DURATION_S
        ))
        while time.monotonic() < deadline:
            s = self.t.get_state()
            samples.append((s.x, s.y, s.z))
            time.sleep(sc.SETPOINT_DT)

        self._home_x = sum(p[0] for p in samples) / len(samples)
        self._home_y = sum(p[1] for p in samples) / len(samples)
        self._home_z = sum(p[2] for p in samples) / len(samples)
        print("地面基准已建立：home_z={:.3f}（后续高度均为本次基准高度差）".format(
            self._home_z
        ))
    def _hover_target_z(self, alt_m: Optional[float]) -> float:
        """根据输入的相对高度返回 setpoint 用的 NED Z 坐标。"""
        if alt_m is not None:
            if self.is_home_set:
                return self._home_z - alt_m
            else:
                return self.t.get_state().z - alt_m
        # 保持当前高度
        return self.t.get_state().z

    def _publish_setpoint_for(self, x: float, y: float, z: float,
                               duration_s: float) -> None:
        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            self.t.send_setpoint_local(x, y, z)
            time.sleep(sc.SETPOINT_DT)

    def _liftoff_from_ground(self, liftoff_z: float, liftoff_alt_m: float,
                             target_alt_m: float) -> None:
        """
        起跳段：发送台阶 setpoint，等待飞机离地。

        双重超时保护：
          第一层-高度停滞检测：高度连续 3s 没有明显增长才判定失败
          第二层-硬上限：12s 总超时兜底

        这样在电池电压偏低、爬升较慢时，只要高度仍在持续增长，
        就不会被一刀切的时间超时卡住。
        """
        print("起跳段：给 {:.2f}m 台阶目标，先离地再爬升...".format(liftoff_alt_m))
        stagnant_start = None             # 高度停滞的起始时间
        overall_deadline = time.monotonic() + sc.LIFTOFF_TOTAL_TIMEOUT_S  # 第二层保险：总超时
        last_print = 0.0
        detected = False
        detected_time = None
        last_rel_alt = -1.0               # 上次高度，用于判断是否在增长

        while time.monotonic() < overall_deadline:
            self.t.send_setpoint_local(self._home_x, self._home_y, liftoff_z)

            s = self.t.get_state()
            rel_alt = self._home_z - s.z
            now = time.monotonic()
            if now - last_print > 0.5:
                print("起跳中：相对高度={:.2f}m".format(rel_alt))
                last_print = now

            if not detected and rel_alt >= sc.LIFTOFF_DETECTED_ALT_M:
                detected = True
                detected_time = now
                print("已离地：相对高度={:.2f}m，继续保持台阶目标 {:.1f}s...".format(
                    rel_alt, sc.LIFTOFF_HOLD_AFTER_DETECTED_S
                ))

            if detected:
                held_long_enough = now - detected_time >= sc.LIFTOFF_HOLD_AFTER_DETECTED_S
                if held_long_enough:
                    print("起跳段完成：相对高度={:.2f}m，下一阶段从 {:.2f}m setpoint 继续爬升。".format(
                        rel_alt, liftoff_alt_m
                    ))
                    return

            # 第一层保险：检测高度是否在持续增加
            if rel_alt > last_rel_alt + sc.LIFTOFF_PROGRESS_THRESHOLD_M:  # 有进步
                stagnant_start = None
            else:
                if stagnant_start is None:
                    stagnant_start = now
                elif now - stagnant_start > sc.LIFTOFF_STALL_TIMEOUT_S:  # 连续停滞超时
                    raise FlyError("起跳停滞超过 {:.0f}s，请检查动力/载重/定高/电池".format(
                        sc.LIFTOFF_STALL_TIMEOUT_S))

            last_rel_alt = rel_alt
            time.sleep(sc.SETPOINT_DT)

        raise FlyError("起跳总超时 {:.0f}s，请检查动力/载重/定高/电池".format(
            sc.LIFTOFF_TOTAL_TIMEOUT_S))

    def _climb_to_altitude(self, target_alt_m: float, target_z: float,
                           climb_start_alt: float) -> None:
        climb_start_alt = min(max(climb_start_alt, sc.LIFTOFF_DETECTED_ALT_M), target_alt_m)
        min_climb_time = max(0.0, (target_alt_m - climb_start_alt) / sc.CLIMB_RATE_MPS)
        start_time = time.monotonic()
        last_print = 0.0
        while True:
            elapsed = time.monotonic() - start_time
            commanded_alt = min(target_alt_m,
                                climb_start_alt + sc.CLIMB_RATE_MPS * elapsed)
            commanded_z = self._home_z - commanded_alt

            self.t.send_setpoint_local(self._home_x, self._home_y, commanded_z)

            s = self.t.get_state()
            rel_alt = self._home_z - s.z
            now = time.monotonic()
            if now - last_print > 1.0:
                print("爬升中：当前={:.2f}m，目标={:.2f}m".format(
                    rel_alt, commanded_alt))
                last_print = now

            if rel_alt >= target_alt_m - 0.05 and elapsed >= min_climb_time:
                break
            if rel_alt > sc.MAX_SAFE_ALT_M:
                raise FlyError("高度 {:.2f}m 超过安全上限 {:.2f}m".format(
                    rel_alt, sc.MAX_SAFE_ALT_M
                ))
            if elapsed > sc.CLIMB_TIMEOUT_S:
                raise FlyError("爬升超时，请检查位置估计/Offboard/动力响应")

            time.sleep(sc.SETPOINT_DT)

        print("到达目标高度 {:.2f}m。".format(target_alt_m))
