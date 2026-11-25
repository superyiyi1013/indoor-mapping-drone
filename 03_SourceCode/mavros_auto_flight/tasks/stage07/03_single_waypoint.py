#!/usr/bin/env python3
"""
阶段07-03：单边短距离航点飞行测试。

流程：
1. 起飞到指定高度
2. 悬停确认稳定
3. 按当前机头方向生成前方局部航点
4. 低速飞向航点，进入容差后到点悬停
5. 自动降落
"""

import math
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
    parser.add_argument("--waypoint-hover", type=float, default=5.0)


def run(fly, args):
    if args.forward_distance <= 0.0 or args.forward_distance > sc.MAX_FORWARD_DISTANCE_M:
        raise ValueError("前向距离必须在 (0, {:.2f}]m 范围内".format(sc.MAX_FORWARD_DISTANCE_M))

    fly.takeoff(args.alt)
    start = fly.get_relative_position()
    print("起点坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*start))
    print("预备悬停 {:.1f}s...".format(args.pre_hover))
    fly.hover(args.pre_hover, alt_m=args.alt)

    target_dx, target_dy = fly.body_forward_offset(args.forward_distance)
    print("目标航点相对起点：x={:.3f}, y={:.3f}, alt={:.3f}".format(
        target_dx, target_dy, args.alt
    ))
    final_err = fly.move_to_local_offset(
        target_dx,
        target_dy,
        alt_m=args.alt,
        speed_mps=args.forward_speed,
        tolerance_m=args.waypoint_tolerance,
    )
    actual = fly.get_relative_position()
    print("实际到达坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*actual))
    print("到达误差：{:.3f} m".format(final_err))

    print("到点悬停 {:.1f}s...".format(args.waypoint_hover))
    fly.hold_at_offset(target_dx, target_dy, args.alt, args.waypoint_hover)
    after_hover = fly.get_relative_position()
    hover_drift = math.hypot(after_hover[0] - actual[0], after_hover[1] - actual[1])
    print("到点悬停结束坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*after_hover))
    print("到点悬停漂移：{:.3f} m".format(hover_drift))

    fly.land()
    print("通过：阶段07-03单边短距离航点飞行测试完成。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage07_single_waypoint",
        add_args,
        run,
        MavrosTransport(),
    ))
