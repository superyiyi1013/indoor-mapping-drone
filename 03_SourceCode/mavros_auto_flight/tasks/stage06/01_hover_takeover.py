#!/usr/bin/env python3
"""
阶段06-01：Offboard低空悬停与人工接管测试。

流程：
1. 起飞至 0.8m
2. 悬停 6s
3. 提示飞手接管（摇杆或模式开关）
4. 检测模式是否离开 OFFBOARD
5. 接管成功 → 停止 setpoint，飞手手动降落
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.add_argument("--takeover-timeout", type=float, default=15.0)


def run(fly, args):
    fly.takeoff(args.alt)
    print("将在 {:.2f}m 高度悬停 {:.1f}秒，然后开始接管测试...".format(
        args.alt, args.hover_time
    ))
    fly.hover(args.hover_time)

    print("")
    print("=" * 40)
    print("现在开始人工接管测试")
    print("1) 先明显打摇杆，输入幅度要超过 COM_RC_STICK_OV 阈值。")
    print("2) 如果 0.5秒内没有离开 OFFBOARD，立即拨模式开关切回 Stabilized/Altitude。")
    print("3) 接管后保持人工控制，手动降落。")
    print("=" * 40)
    print("")
    input("安全员准备好执行接管后，按回车继续...")

    # 接管检测：只要模式不是 OFFBOARD 就算接管。
    # 直接用 state.mode != "OFFBOARD"，不比较 start_mode，
    # 避免 start_mode 本身不是 OFFBOARD 时检测失效。
    deadline = time.time() + args.takeover_timeout
    while time.time() < deadline:
        s = fly.t.get_state()
        # 继续发送悬停 setpoint（home XY + 目标高度）
        fly.t.send_setpoint_local(fly._home_x, fly._home_y,
                                   fly._home_z - args.alt)
        if s.mode != "OFFBOARD":
            print("已检测到接管。当前模式：{}".format(s.mode))
            print("现在停止发送 Offboard setpoint。")
            print("通过：阶段06悬停接管测试完成。")
            return
        time.sleep(0.05)

    print("警告：脚本未检测到模式离开 OFFBOARD。")
    answer = input("QGC 是否显示已接管且人工控制有效？[y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        raise RuntimeError("未确认遥控器接管")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage06_hover_takeover",
        add_args,
        run,
        MavrosTransport(),
    ))
