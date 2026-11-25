#!/usr/bin/env python3
"""
阶段07-01：定点悬停与局部坐标稳定性检查。

流程：
1. 起飞到指定高度
2. 记录悬停起始局部坐标
3. 定点悬停，全程采样位置数据，计算平均偏移和最大偏移
4. 记录结束局部坐标
5. 自动降落（降落目标锁定起飞点 home XY）
6. 落地后计算降落偏移

输出摘要包含：
  起始坐标、悬停起止偏移、悬停平均偏移、悬停最大偏移、降落偏移、评估等级
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core import safety_config as sc
from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.set_defaults(alt=1.0, hover_time=20.0)
    parser.add_argument("--drift-pass", type=float, default=0.20,
                        help="XY 漂移通过线，默认 0.20m")
    parser.add_argument("--drift-warn", type=float, default=0.30,
                        help="XY 漂移警戒线，默认 0.30m")


def run(fly, args):
    if args.drift_pass <= 0.0 or args.drift_warn <= args.drift_pass:
        raise ValueError("漂移阈值必须满足 0 < drift-pass < drift-warn")

    fly.takeoff(args.alt)
    start = fly.get_relative_position()
    print("悬停起始坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*start))

    # ── 自定义悬停采样循环 ────────────────────────────
    print("开始定点悬停 {:.1f}s，全程采样位置数据...".format(args.hover_time))
    target_z = fly._home_z - args.alt
    deadline = time.monotonic() + args.hover_time
    samples = []
    last_print = 0.0

    while time.monotonic() < deadline:
        fly.t.send_setpoint_local(fly._home_x, fly._home_y, target_z)
        now = time.monotonic()
        # 每秒打印一次进度
        if now - last_print > 1.0:
            s = fly.t.get_state()
            rel_alt = fly._home_z - s.z
            remaining = max(0, int(deadline - now))
            print("悬停中：高度≈{:.2f}m，剩余 {}s".format(rel_alt, remaining))
            last_print = now
        # 每个控制周期采样一次位置
        s = fly.t.get_state()
        dx = s.x - fly._home_x
        dy = s.y - fly._home_y
        samples.append((dx, dy))
        time.sleep(sc.SETPOINT_DT)

    # ── 计算悬停偏移统计 ──────────────────────────────
    end = fly.get_relative_position()
    drift_start_end = math.hypot(end[0] - start[0], end[1] - start[1])

    if samples:
        # 平均偏移：所有采样点位置的平均值
        avg_dx = sum(s[0] for s in samples) / len(samples)
        avg_dy = sum(s[1] for s in samples) / len(samples)
        avg_drift = math.hypot(avg_dx, avg_dy)
        # 最大偏移：所有采样点中的最大水平距离
        max_drift = max(math.hypot(s[0], s[1]) for s in samples)
    else:
        avg_dx = 0.0
        avg_dy = 0.0
        avg_drift = 0.0
        max_drift = 0.0

    print("悬停结束坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*end))
    print("悬停起止偏移：{:.3f} m".format(drift_start_end))
    print("悬停平均偏移：{:.3f} m（采样 {} 次）".format(avg_drift, len(samples)))
    print("悬停最大偏移：{:.3f} m".format(max_drift))

    if drift_start_end < args.drift_pass and max_drift < args.drift_warn:
        print("评估：通过，可进入后续路线飞行。")
    elif drift_start_end <= args.drift_warn:
        print("评估：警戒，建议复测一次，不建议直接飞更复杂路线。")
    else:
        print("评估：未通过，禁止进入路线飞行，请排查光流、测距、地面纹理、震动和参数。")

    fly.land()
    final = fly.get_relative_position()
    land_drift = math.hypot(final[0], final[1])

    print("")
    print("=" * 50)
    print("阶段07-01 完成，结果摘要")
    print("=" * 50)
    print("起始坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*start))
    print("悬停结束：x={:.3f}, y={:.3f}, alt={:.3f}".format(*end))
    print("落点坐标：x={:.3f}, y={:.3f}, alt={:.3f}".format(*final))
    print("")
    print("悬停起止偏移：{:.3f} m".format(drift_start_end))
    print("悬停平均偏移：{:.3f} m".format(avg_drift))
    print("悬停最大偏移：{:.3f} m".format(max_drift))
    print("降落偏移：{:.3f} m".format(land_drift))
    print("")
    if drift_start_end < args.drift_pass and max_drift < args.drift_warn:
        print("评估等级：通过")
    elif drift_start_end <= args.drift_warn:
        print("评估等级：警戒")
    else:
        print("评估等级：未通过")
    print("")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage07_local_hover_stability",
        add_args,
        run,
        MavrosTransport(),
    ))
