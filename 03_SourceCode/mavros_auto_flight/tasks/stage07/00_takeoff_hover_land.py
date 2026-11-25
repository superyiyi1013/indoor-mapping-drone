#!/usr/bin/env python3
"""
阶段07-00：起飞降落稳定性循环测试。

流程：
1. 起飞到指定高度
2. 定点悬停
3. 自动降落

用途：每当起飞或降落程序有改动后，先运行本任务验证起飞和降落
是否正常工作。不评估 XY 漂移，仅判断能否完成完整起飞→悬停→降落流程。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.set_defaults(alt=1.0, hover_time=10.0)


def run(fly, args):
    fly.takeoff(args.alt)
    print("起飞完成，开始悬停 {:.1f}s...".format(args.hover_time))
    fly.hover(args.hover_time, alt_m=args.alt)
    fly.land()
    print("阶段07-00完成：起飞→悬停→降落全流程通过。")


if __name__ == "__main__":
    sys.exit(run_task(
        "takeoff_hover_land",
        add_args,
        run,
        MavrosTransport(),
    ))
