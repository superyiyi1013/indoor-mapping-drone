# flight_core — X400 共享飞行核心
# 该包是 Python 包入口（__init__.py），标记 flight_core 为可导入的包
# 三层架构：
#   Transport 层 — 通信抽象（pymavlink / MAVROS 可插拔）
#   Fly 层       — 飞行原语（takeoff/hover/move/land，依赖 Transport 接口）
#   Task 层      — 任务编排（调用 Fly 层，描述"做什么"）
#
# Task 层代码不再直接调 pymavlink 或 ROS，只跟 Fly 和 Transport 接口对话。
#
# 使用示例：
#   # Linux 机载：
#   from flight_core.transport import MavrosTransport
#   from flight_core.fly import Fly
#   fly = Fly(MavrosTransport())
#   fly.takeoff(0.8)
#   fly.hover(5)
#   fly.land()
#
#   # Windows 地面站：
#   from flight_core.transport import MavlinkTransport
#   fly = Fly(MavlinkTransport("udpin:0.0.0.0:14540"))
#   fly.takeoff(1.0)
"""
X400 shared flight core — transport-agnostic flight primitives.
"""

__version__ = "0.1.0"
