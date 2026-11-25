#!/usr/bin/env python3
"""
阶段06：1m 起飞、悬停等待人工接管，超时自动降落。

流程：
1. 调用 flight_core 统一起飞方案到 1.0m。
2. 到达 1.0m 后持续悬停并等待人工接管。
3. 若 20s 内检测到飞控模式离开 OFFBOARD，停止发送 setpoint，交给飞手。
4. 若 20s 内未接管，自动降落。
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from flight_core import safety_config as sc
from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.set_defaults(alt=1.0, hover_time=0.0)
    parser.add_argument("--takeover-timeout", type=float, default=20.0,
                        help="到达目标高度后等待人工接管的最长时间，默认 20s")


def run(fly, args):
    if args.alt <= 0.0 or args.alt > sc.MAX_SAFE_ALT_M:
        raise ValueError("目标高度必须在 (0, {:.2f}] m 范围内".format(sc.MAX_SAFE_ALT_M))
    if args.takeover_timeout <= 0.0:
        raise ValueError("接管等待时间必须大于 0")
    print("起飞目标：{:.2f}m；统一起飞方案由 flight_core.takeoff 执行；接管等待：{:.1f}s".format(
        args.alt, args.takeover_timeout
    ))

    fly.takeoff(args.alt)
    _wait_for_takeover_or_land(fly, args.alt, args.takeover_timeout)


def _wait_for_takeover_or_land(fly, alt_m, timeout_s):
    print("")
    print("=" * 48)
    print("已到达 {:.2f}m，进入悬停并等待人工接管。".format(alt_m))
    print("接管方式：明显打摇杆，或拨模式开关离开 OFFBOARD。")
    print("若 {:.0f}s 内未检测到接管，脚本将自动降落。".format(timeout_s))
    print("=" * 48)

    deadline = time.monotonic() + timeout_s
    last_print = 0.0

    while time.monotonic() < deadline:
        s = fly.t.get_state()
        fly.t.send_setpoint_local(fly._home_x, fly._home_y, fly._home_z - alt_m)

        if s.mode != "OFFBOARD":
            print("已检测到人工接管，当前模式：{}".format(s.mode))
            print("停止发送 Offboard setpoint，由飞手继续控制并手动降落。")
            return

        now = time.monotonic()
        if now - last_print > 1.0:
            remaining = max(0, int(deadline - now))
            rel_alt = fly._home_z - s.z
            print("等待接管中：模式={}，高度≈{:.2f}m，剩余={}s".format(
                s.mode, rel_alt, remaining
            ))
            last_print = now

        time.sleep(sc.SETPOINT_DT)

    print("{:.0f}s 内未检测到人工接管，开始自动降落。".format(timeout_s))
    fly.land()
    print("通过：未接管超时后已执行自动降落。")


if __name__ == "__main__":
    sys.exit(run_task(
        "stage06_takeoff_1m_takeover_or_autoland",
        add_args,
        run,
        MavrosTransport(),
    ))
