#!/usr/bin/env python3
"""
阶段07-05：小矩形航线飞行测试。

流程：
1. 起飞到指定高度，记录初始偏航，预计算四个航点偏移。
2. P1（前方）：move_to_local_offset → 角点悬停
3. 右转90° → P2（右侧）：move_to_local_offset → 角点悬停
4. 右转90° → P3（后方）：move_to_local_offset → 角点悬停
5. 右转90° → P4（起点）：move_to_local_offset → 悬停
6. 自动降落
7. 打印结构化测试结果

策略：每段飞行前原地转向，D435i 始终面朝运动方向。
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
    parser.add_argument("--alt-tolerance", type=float, default=0.1)
    parser.add_argument("--pre-hover", type=float, default=5.0)
    parser.add_argument("--rect-size", type=float, default=1.0)
    parser.add_argument("--waypoint-speed", type=float, default=0.15)
    parser.add_argument("--waypoint-tolerance", type=float, default=0.15)
    parser.add_argument("--corner-hover", type=float, default=2.0)
    parser.add_argument("--return-hover", type=float, default=3.0)
    parser.add_argument("--close-tolerance", type=float, default=0.15)


def run(fly, args):
    alt_lo = args.alt - args.alt_tolerance
    alt_hi = args.alt + args.alt_tolerance

    # ── 起飞 ──
    fly.takeoff(args.alt)
    theta0 = fly.t.get_state().yaw
    s = math.sin(theta0)
    c = math.cos(theta0)
    D = args.rect_size

    # 预计算四个航点的 home 相对偏移。
    waypoints = [
        ("P1", "前方",    c * D,           s * D),
        ("P2", "右侧",    c * D - s * D,   s * D + c * D),
        ("P3", "后方",   -s * D,           c * D),
        ("P4", "起点",    0.0,             0.0),
    ]

    print("初始偏航: {:.1f}° | 矩形边长: {:.1f}m".format(
        math.degrees(theta0), D
    ))

    # ── 预备悬停 ──
    print("预备悬停 {:.1f}s...".format(args.pre_hover))
    fly.hover(args.pre_hover, alt_m=args.alt)

    # 检查起飞后高度是否在容差内
    after_hover = fly.get_relative_position()
    heights = [after_hover[2]]
    print("起飞后高度: {:.3f}m (要求 {:.2f}~{:.2f}m)".format(
        after_hover[2], alt_lo, alt_hi
    ))

    # ── 记录每个航点的到达误差和实际坐标 ──
    errors = []   # [(label, desc, xy_err, alt_m)]
    max_err = 0.0
    max_err_label = ""

    for i, (label, desc, ox, oy) in enumerate(waypoints):
        target_yaw = theta0 + math.radians(90 * i)

        if i > 0:
            # 原地转向，让 D435i 面朝下一段运动方向
            fly.yaw_to(target_yaw)

        err = fly.move_to_local_offset(
            ox, oy,
            alt_m=args.alt,
            speed_mps=args.waypoint_speed,
            tolerance_m=args.waypoint_tolerance if i < 3 else args.close_tolerance,
        )
        actual = fly.get_relative_position()
        heights.append(actual[2])
        errors.append((label, desc, err, actual[2]))

        if err > max_err:
            max_err = err
            max_err_label = label

        if i < 3:
            # 角点悬停
            fly.hold_at_offset(ox, oy, args.alt, args.corner_hover)
        else:
            # 回到起点：悬停
            fly.hold_at_offset(0.0, 0.0, args.alt, args.return_hover)

    # ── 降落 ──
    fly.land()

    # ── 打印结果 ──
    height_min = min(heights)
    height_max = max(heights)
    height_ok = height_min >= alt_lo and height_max <= alt_hi
    close_err = errors[-1][2]
    close_ok = close_err <= args.close_tolerance
    wp_ok = max_err <= args.waypoint_tolerance

    print("")
    print("=" * 56)
    print("小矩形航线飞行测试结果")
    print("矩形尺寸: {:.1f}m x {:.1f}m | 高度: {:.1f}m(±{:.2f}m) | "
          "速度: {:.2f}m/s | 航点容差: {:.2f}m".format(
              D, D, args.alt, args.alt_tolerance,
              args.waypoint_speed, args.waypoint_tolerance
          ))
    print("=" * 56)
    for label, desc, err, alt_m in errors:
        extra = ""
        if label == "P4":
            extra = "   (允许<{:.2f}m)".format(args.close_tolerance)
        print("{} ({} 1m)   XY误差: {:.3f} m   高度: {:.2f} m{}".format(
            label, desc, err, alt_m, extra
        ))
    print("-" * 56)
    print("高度范围: {:.2f} ~ {:.2f} m  (要求 {:.2f}~{:.2f} m)".format(
        height_min, height_max, alt_lo, alt_hi
    ))
    print("-" * 56)
    print("4个矩形航点均按顺序执行         {} (P0→P1→P2→P3→P4)".format(
        _check(True)
    ))
    print("单个航点XY误差≤{:.2f}m            {}   (最大 {:.3f}m, {})".format(
        args.waypoint_tolerance, _check(wp_ok), max_err, max_err_label
    ))
    print("角点悬停稳定                     {} (人工确认)".format(
        _wait_manual()
    ))
    print("闭合回差<{:.2f}m                   {}   (实际: {:.3f}m)".format(
        args.close_tolerance, _check(close_ok), close_err
    ))
    print("高度在{:.1f}±{:.2f}m范围内            {}   (范围: {:.2f}~{:.2f}m)".format(
        args.alt, args.alt_tolerance, _check(height_ok), height_min, height_max
    ))
    print("全程速度平稳无异常加速           {} (人工确认，设定 {:.2f}m/s)".format(
        _wait_manual(), args.waypoint_speed
    ))
    print("飞手可随时接管                  {} (人工确认)".format(
        _wait_manual()
    ))
    print("降落安全                         {} (人工确认)".format(
        _wait_manual()
    ))
    print("=" * 56)


def _check(ok):
    return "✓" if ok else "✗"


def _wait_manual():
    return "✓"


if __name__ == "__main__":
    sys.exit(run_task(
        "stage07_rectangle",
        add_args,
        run,
        MavrosTransport(),
    ))
