#!/usr/bin/env python3
"""
阶段06-04：Offboard短距离前进与地面站前向距离观察测试。

流程：
1. 起飞至 0.8m
2. 悬停 hover_time 秒（给 QGC 观察前向距离）
3. 向前飞行 forward_distance 米
4. 悬停 hover_time 秒
5. 自动降落
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport
from flight_core import safety_config as sc


def add_args(parser):
    parser.add_argument("--forward-distance", type=float, default=1.0)
    parser.add_argument("--forward-speed", type=float, default=sc.DEFAULT_FORWARD_SPEED_MPS)


def run(fly, args):
    if args.forward_distance > sc.MAX_FORWARD_DISTANCE_M:
        raise ValueError("--forward-distance 超过上限 {:.2f}m".format(
            sc.MAX_FORWARD_DISTANCE_M))
    if args.forward_speed > sc.MAX_FORWARD_SPEED_MPS:
        raise ValueError("--forward-speed 超过上限 {:.2f}m/s".format(
            sc.MAX_FORWARD_SPEED_MPS))

    fly.takeoff(args.alt)
    print("将在 {:.2f}m 高度悬停 {:.1f}秒，请在 QGC 观察前向距离...".format(
        args.alt, args.hover_time))
    fly.hover(args.hover_time)

    fly.move_forward(args.forward_distance, speed_mps=args.forward_speed,
                     alt_m=args.alt)

    print("短距离前进结束，悬停保持...")
    fly.hover(args.hover_time)
    fly.land()
    print("通过：阶段06短距离前进任务完成。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage06_short_forward",
        add_args,
        run,
        MavrosTransport(),
    ))
