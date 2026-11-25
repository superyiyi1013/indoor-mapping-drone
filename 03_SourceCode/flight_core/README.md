# flight_core — X400 共享飞行核心

三层架构：Transport → Fly → Task。

## 目录

| 文件 | 说明 |
|:---|:---|
| `transport/__init__.py` | Transport 抽象接口（VehicleState + Transport ABC） |
| `transport/mavros_transport.py` | MAVROS 实现（Linux 机载电脑） |
| `transport/mavlink_transport.py` | pymavlink 实现（Windows 地面站） |
| `fly.py` | Fly 层 — 飞行原语 |
| `safety_config.py` | 全局安全常量 |
| `task_runner.py` | Task 层统一入口（参数解析 + 安全确认 + 异常兜底） |

## 使用

### Linux 机载（MAVROS）

```python
from flight_core.transport.mavros_transport import MavrosTransport
from flight_core.fly import Fly

fly = Fly(MavrosTransport())
fly.connect()
fly.takeoff(0.8)
fly.hover(5)
fly.land()
```

### Windows 地面站（pymavlink）

```python
from flight_core.transport.mavlink_transport import MavlinkTransport
from flight_core.fly import Fly

fly = Fly(MavlinkTransport("udpin:0.0.0.0:14540"))
fly.connect()
fly.takeoff(1.0)
fly.hover(10)
fly.land()
```

## Fly 原语

| 方法 | 说明 |
|:---|:---|
| `takeoff(alt_m)` | 起飞：预发 → OFFBOARD → 解锁 → 起跳 → 爬升 → 到达 |
| `hover(duration_s, alt_m)` | 定点悬停 |
| `move_forward(dist_m, speed, alt_m)` | 沿机头方向前进 |
| `move_forward_until(max_dist, condition, ...)` | 前进直到满足条件或达到距离 |
| `land()` | 下降 + 交 NAV_LAND |

所有安全边界（高度上限、速度上限、超时）在 `safety_config.py` 集中管理。
