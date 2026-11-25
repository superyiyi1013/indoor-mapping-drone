#!/usr/bin/env python3
"""
阶段06-03：Offboard低空起飞悬停测试。

流程：
1. 起飞至 0.8m
2. 悬停 hover_time 秒
3. 自动降落
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    pass


def run(fly, args):
    fly.takeoff(args.alt)
    print("将在 {:.2f} m 高度悬停 {:.1f}秒...".format(args.alt, args.hover_time))
    fly.hover(args.hover_time)
    fly.land()
    print("通过：阶段06低空悬停任务完成。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage06_low_alt_hover",
        add_args,
        run,
        MavrosTransport(),
    ))
