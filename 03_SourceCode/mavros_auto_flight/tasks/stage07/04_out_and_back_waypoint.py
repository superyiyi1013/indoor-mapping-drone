#!/usr/bin/env python3
"""
阶段07-04：往返直线航点飞行测试。

流程：
1. 起飞到指定高度
2. 悬停确认稳定
3. 飞向当前机头前方短距离航点
4. 到点悬停
5. 返回起点附近
6. 到点悬停并计算起点回差
7. 自动降落
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core import safety_config as sc
from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.set_defaults(alt=1.0, hover_time=0.0)
    parser.add_argument("--pre-hover", type=float, default=5.0)
    parser.add_argument("--forward-distance", type=float, default=1.0)
    parser.add_argument("--forward-speed", type=float, default=0.12)
    parser.add_argument("--waypoint-tolerance", type=float, default=0.15)
    parser.add_argument("--return-tolerance", type=float, default=0.25)
    parser.add_argument("--waypoint-hover", type=float, default=2.0)


def run(fly, args):
    if args.forward_distance <= 0.0 or args.forward_distance > sc.MAX_FORWARD_DISTANCE_M:
        raise ValueError("前向距离必须在 (0, {:.2f}]m 范围内".format(sc.MAX_FORWARD_DISTANCE_M))
    if args.return_tolerance <= 0.0:
        raise ValueError("返回容差必须大于 0")

    fly.takeoff(args.alt)
    start = fly.get_relative_position()
    print("起点坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*start))
    print("预备悬停 {:.1f}s...".format(args.pre_hover))
    fly.hover(args.pre_hover, alt_m=args.alt)

    target_dx, target_dy = fly.body_forward_offset(args.forward_distance)
    print("前方目标航点：x={:.3f}, y={:.3f}, alt={:.3f}".format(
        target_dx, target_dy, args.alt
    ))
    forward_err = fly.move_to_local_offset(
        target_dx,
        target_dy,
        alt_m=args.alt,
        speed_mps=args.forward_speed,
        tolerance_m=args.waypoint_tolerance,
    )
    forward_actual = fly.get_relative_position()
    print("前方实际到达坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*forward_actual))
    print("前方航点到达误差：{:.3f} m".format(forward_err))
    fly.hold_at_offset(target_dx, target_dy, args.alt, args.waypoint_hover)

    print("返回起点附近...")
    return_err = fly.move_to_local_offset(
        0.0,
        0.0,
        alt_m=args.alt,
        speed_mps=args.forward_speed,
        tolerance_m=args.return_tolerance,
    )
    return_actual = fly.get_relative_position()
    print("返回后坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*return_actual))
    print("起点回差：{:.3f} m".format(return_err))
    fly.hold_at_offset(0.0, 0.0, args.alt, args.waypoint_hover)

    fly.land()
    print("通过：阶段07-04往返直线航点飞行测试完成。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage07_out_and_back_waypoint",
        add_args,
        run,
        MavrosTransport(),
    ))
