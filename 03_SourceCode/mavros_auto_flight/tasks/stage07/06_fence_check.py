#!/usr/bin/env python3
"""
阶段07-06：安全围栏验证测试。

验证飞行核心的安全常量围栏是否生效：
1. move_forward 超过 MAX_FORWARD_DISTANCE_M → 抛出 ValueError
2. move_to_local_offset 超过 MAX_FORWARD_DISTANCE_M → 抛出 ValueError
3. 合法距离正常飞行

本测试值范围小、高度低，仅验证围栏机制不涉及大范围飞行。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core import safety_config as sc
from flight_core.task_runner import run_task
from flight_core.fly import FlyError
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.set_defaults(alt=0.8, hover_time=3.0)
    parser.add_argument("--oversize-dist", type=float, default=3.0)
    parser.add_argument("--valid-dist", type=float, default=0.5)
    parser.add_argument("--fence-speed", type=float, default=0.15)


def run(fly, args):
    results = []

    fly.takeoff(args.alt)
    fly.hover(args.hover_time, alt_m=args.alt)

    # ── 测试1: move_forward 超限 ──
    print("─" * 40)
    print("测试1: move_forward({:.1f}m) 应被围栏拒绝".format(args.oversize_dist))
    try:
        fly.move_forward(args.oversize_dist, speed_mps=args.fence_speed,
                         alt_m=args.alt)
        results.append(("move_forward 超限拦截", False,
                        "未抛出异常，围栏未生效"))
    except ValueError as e:
        ok = "超过上限" in str(e) or "范围内" in str(e)
        results.append(("move_forward 超限拦截", ok, str(e)))
    except Exception as e:
        results.append(("move_forward 超限拦截", False, "异常类型错误: {}".format(e)))

    # ── 测试2: move_to_local_offset 超限 ──
    print("─" * 40)
    print("测试2: move_to_local_offset({:.1f}m) 应被围栏拒绝".format(args.oversize_dist))
    try:
        fly.move_to_local_offset(args.oversize_dist, 0.0, alt_m=args.alt,
                                 speed_mps=args.fence_speed, tolerance_m=0.15)
        results.append(("move_to_local_offset 超限拦截", False,
                        "未抛出异常，围栏未生效"))
    except ValueError as e:
        ok = "超过上限" in str(e) or "范围内" in str(e)
        results.append(("move_to_local_offset 超限拦截", ok, str(e)))
    except Exception as e:
        results.append(("move_to_local_offset 超限拦截", False, "异常类型错误: {}".format(e)))

    # ── 测试3: 合法距离正常飞行 ──
    print("─" * 40)
    print("测试3: move_forward({:.1f}m) 应正常飞行".format(args.valid_dist))
    try:
        fly.move_forward(args.valid_dist, speed_mps=args.fence_speed,
                         alt_m=args.alt)
        results.append(("合法距离飞行", True, "前飞 {:.1f}m 正常".format(args.valid_dist)))
    except Exception as e:
        results.append(("合法距离飞行", False, str(e)))

    # ── 打印结果 ──
    fly.hover(args.hover_time, alt_m=args.alt)
    fly.land()

    print("")
    print("=" * 56)
    print("安全围栏验证 — 结果")
    print("MAX_FORWARD_DISTANCE_M = {:.1f}m".format(sc.MAX_FORWARD_DISTANCE_M))
    print("MAX_FORWARD_SPEED_MPS  = {:.1f}m/s".format(sc.MAX_FORWARD_SPEED_MPS))
    print("=" * 56)
    for label, ok, detail in results:
        print("{}: {} | {}".format(label, "✓" if ok else "✗", detail))
    print("=" * 56)


if __name__ == "__main__":
    sys.exit(run_task(
        "stage07_fence_check",
        add_args,
        run,
        MavrosTransport(),
    ))
