"""
任务执行器 — Task 层统一入口。

每个 task 只需定义一个 run(fly, args) 函数，
task_runner 负责：参数解析、安全确认、Transport 初始化、Fly 连接、异常兜底。
"""

import argparse
import sys
import time
from typing import Callable

from .fly import Fly, FlyError
from . import safety_config as sc
from .transport import Transport


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--alt", type=float, default=sc.DEFAULT_TARGET_ALT_M)
    parser.add_argument("--hover-time", type=float, default=sc.DEFAULT_HOVER_TIME_S)


def require_ready_to_fly(task_name: str) -> bool:
    print("")
    print("=" * 50)
    print("Offboard 自动飞行任务：{}".format(task_name))
    print("=" * 50)
    print("安全要求：")
    print("  - 前置阶段已通过")
    print("  - 遥控器已开机，接管方式已验证")
    print("  - 安全员已就位，可随时接管")
    print("  - 测试场地已清空")
    print("  - 开机自启动避障链路已常驻运行并通过健康检查")
    print("=" * 50)
    print("")
    answer = input("确认安全后输入 Y 继续：").strip()
    return answer.upper() == "Y"


def run_task(
    task_name: str,
    build_parser: Callable[[argparse.ArgumentParser], None],
    run_fn: Callable[[Fly, argparse.Namespace], None],
    transport: Transport,
) -> int:
    """
    Task 层统一入口。

    task_name:   任务名称（用于打印和 ROS node 名）
    build_parser: 向 argparse 添加任务专属参数的回调
    run_fn:      任务主逻辑 (fly, args) -> None
    transport:   已配置好的 Transport 实例（未连接）
    """
    parser = argparse.ArgumentParser(description=task_name)
    add_common_args(parser)
    build_parser(parser)
    args = parser.parse_args()

    if not require_ready_to_fly(task_name):
        print("操作员取消任务。")
        return 2

    fly = Fly(transport)
    try:
        print("正在连接飞行控制器...")
        fly.connect()
        print("链路就绪。")

        run_fn(fly, args)
        return 0

    except KeyboardInterrupt:
        print("\n操作员中断任务。")
        _try_emergency_land(fly)
        return 130

    except FlyError as exc:
        print("飞行异常：{}".format(exc))
        _try_emergency_land(fly)
        return 1

    except Exception as exc:
        print("失败：{}".format(exc))
        _try_emergency_land(fly)
        return 1

    finally:
        try:
            fly.close()
        except Exception:
            pass


def _try_emergency_land(fly: Fly) -> None:
    """尝试紧急降落作为最后兜底，并打印可核验状态。"""
    print("正在请求降落作为兜底...")
    try:
        time.sleep(0.5)
        ok = fly.t.send_land()
        state = fly.t.get_state()
        print("兜底 LAND 请求：service_ok={}，mode={}，armed={}，landed={}".format(
            ok, state.mode, state.armed, fly.t.has_landed()
        ))
    except Exception as exc:
        print("紧急降落请求失败：{}，请立即人工接管！".format(exc))

