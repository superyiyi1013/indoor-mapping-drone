#!/usr/bin/env python3
"""
阶段07-02：Offboard 航线模式人工接管测试。

流程：
1. 起飞到指定高度
2. 预备悬停
3. 给一个微小前向航点 setpoint，进入路线任务形态
4. 持续发送航点 setpoint 并等待飞手切出 OFFBOARD
5. 检测到模式离开 OFFBOARD 后停止发送 setpoint，由飞手接管
6. 超时未接管则自动降落
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core import safety_config as sc
from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.set_defaults(alt=1.0, hover_time=0.0)
    parser.add_argument("--pre-hover", type=float, default=5.0)
    parser.add_argument("--forward-distance", type=float, default=0.5)
    parser.add_argument("--forward-speed", type=float, default=0.12)
    parser.add_argument("--takeover-timeout", type=float, default=15.0)


def run(fly, args):
    if args.forward_distance <= 0.0 or args.forward_distance > sc.MAX_FORWARD_DISTANCE_M:
        raise ValueError("前向距离必须在 (0, {:.2f}]m 范围内".format(sc.MAX_FORWARD_DISTANCE_M))
    if args.forward_speed <= 0.0 or args.forward_speed > sc.MAX_FORWARD_SPEED_MPS:
        raise ValueError("前向速度必须在 (0, {:.2f}]m/s 范围内".format(sc.MAX_FORWARD_SPEED_MPS))
    if args.takeover_timeout <= 0.0:
        raise ValueError("接管等待时间必须大于 0")

    fly.takeoff(args.alt)
    print("预备悬停 {:.1f}s，确认高度和局部坐标稳定...".format(args.pre_hover))
    fly.hover(args.pre_hover, alt_m=args.alt)

    target_dx, target_dy = fly.body_forward_offset(args.forward_distance)
    target_x = fly._home_x + target_dx
    target_y = fly._home_y + target_dy
    target_z = fly._home_z - args.alt

    print("进入航线接管测试：微小前向航点 {:.2f}m，等待 {:.1f}s 内人工接管。".format(
        args.forward_distance, args.takeover_timeout
    ))
    print("请明显打摇杆或拨模式开关离开 OFFBOARD。")

    start = time.monotonic()
    deadline = start + args.takeover_timeout
    last_print = 0.0
    travel_time = max(2.0, args.forward_distance / args.forward_speed)

    while time.monotonic() < deadline:
        now = time.monotonic()
        ratio = min(1.0, (now - start) / travel_time)
        fly.t.send_setpoint_local(
            fly._home_x + target_dx * ratio,
            fly._home_y + target_dy * ratio,
            target_z,
        )
        s = fly.t.get_state()
        if s.mode != "OFFBOARD":
            print("已检测到人工接管，当前模式：{}".format(s.mode))
            print("停止发送 Offboard setpoint，由飞手继续控制并手动降落。")
            return
        if now - last_print > 1.0:
            rel_x, rel_y, rel_alt = fly.get_relative_position()
            print("等待接管中：模式={}，相对坐标=({:.2f}, {:.2f}, {:.2f})，剩余={}s".format(
                s.mode, rel_x, rel_y, rel_alt, max(0, int(deadline - now))
            ))
            last_print = now
        time.sleep(sc.SETPOINT_DT)

    print("{:.0f}s 内未检测到人工接管，开始自动降落。".format(args.takeover_timeout))
    fly.land()
    print("阶段07-02完成：未接管超时后已执行自动降落。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage07_route_takeover_check",
        add_args,
        run,
        MavrosTransport(),
    ))
