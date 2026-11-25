#!/usr/bin/env python3
"""
阶段06-05：Offboard前方障碍停止或悬停测试。

流程：
1. 起飞至 0.8m
2. 悬停 hover_time 秒
3. 低速前进，遇到前方距离 <= obstacle_stop_distance 时停止
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
    parser.add_argument("--forward-distance", type=float, default=0.5)
    parser.add_argument("--forward-speed", type=float, default=0.12)
    parser.add_argument("--obstacle-stop-distance", type=float,
                        default=sc.DEFAULT_OBSTACLE_STOP_DISTANCE_M)
    parser.add_argument("--max-forward-time", type=float, default=8.0)


def run(fly, args):
    if args.obstacle_stop_distance <= 0.0:
        raise ValueError("--obstacle-stop-distance 必须大于 0.0")

    fly.takeoff(args.alt)
    print("将在 {:.2f}m 高度悬停 {:.1f}秒...".format(args.alt, args.hover_time))
    fly.hover(args.hover_time)

    actual_distance = fly.move_forward_until(
        max_distance_m=args.forward_distance,
        stop_condition=lambda s:
            s.front_distance_m is not None
            and s.front_distance_m <= args.obstacle_stop_distance,
        speed_mps=args.forward_speed,
        alt_m=args.alt,
        max_time_s=args.max_forward_time,
    )
    print("实际移动距离：{:.2f} m".format(actual_distance))

    print("悬停保持...")
    fly.hover(args.hover_time)
    fly.land()
    print("通过：阶段06前方障碍停止/悬停任务完成。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage06_obstacle_stop",
        add_args,
        run,
        MavrosTransport(),
    ))
