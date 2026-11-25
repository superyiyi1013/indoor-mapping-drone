# MAVROS 自动飞行测试脚本

本目录是机载电脑侧阶段06 MAVROS 自动飞行入口。当前项目现场流程已经简化为：

```text
机载电脑上电
  -> systemd 自动启动 bootstrap_sensing_stack.sh
  -> MAVROS + D435i + 前向距离链路常驻运行
  -> 阶段06脚本只做链路健康检查
  -> 检查通过后执行 Offboard 飞行动作
```

阶段06脚本不再负责启动 MAVROS、D435i 或前向距离节点；现场只需要确认自启动链路健康。

---

## 三层架构

飞行代码采用 **Transport -> Fly -> Task** 三层架构，核心在 `03_SourceCode/flight_core/`。

| 层 | 位置 | 职责 |
|:---|:---|:---|
| Transport | `flight_core/transport/` | MAVROS / pymavlink 通信适配 |
| Fly | `flight_core/fly.py` | 起飞、悬停、前进、遇障停止、降落等飞行原语 |
| Task | `mavros_auto_flight/tasks/*.py` | 阶段06任务编排，只描述做什么 |

安全常量统一在 `flight_core/safety_config.py`。

---

## 使用前提

- 阶段03、阶段04、阶段05均已通过。
- 机载电脑已编译 `ros_catkin_ws_lite`。
- systemd 已配置并验证开机自启动 `bootstrap_sensing_stack.sh`。
- 遥控器人工接管已验证。
- QGC 可看到飞控状态、电池、模式和 D435i 前向距离。
- 安全员到位，场地满足阶段06测试要求。

阶段06脚本会在飞行前检查：

```text
/mavros/state connected: True
/x400/obstacle/front_distance 有数据
/mavros/distance_sensor/laser_1_sub 存在且被 /mavros 订阅
/mavros/obstacle/send 存在且被 /mavros 订阅
```

QGC 中观察 D435i 前向距离时，看 `DISTANCE_SENSOR id=42` / `orientation=0`；光流/下视测距通常是 `orientation=25`。
PX4 Collision Prevention 使用 `OBSTACLE_DISTANCE`；仅有 `DISTANCE_SENSOR` 不足以通过 Position 模式避障验证。

---

## 正式入口脚本

| 入口脚本 | 用途 |
|---|---|
| `stage06/01_manual_takeover_first_check.sh` | Offboard 低空悬停后验证摇杆接管和模式开关兜底 |
| `stage06/02_position_manual_cp_check.sh` | Position 模式前向手动避障辅助检查；只读、不解锁、不发飞行指令 |
| `stage06/03_low_alt_hover.sh` | Offboard 低空起飞悬停降落 |
| `stage06/04_short_forward.sh` | Offboard 短距离前进并在 QGC 观察前向距离 |
| `stage06/05_obstacle_stop.sh` | D435i 前方障碍触发停止/悬停 |
| `stage06/06_takeoff_1m_takeover_or_autoland.sh` | 起飞到 1m，0.4m/s 爬升，等待人工接管；20s 未接管自动降落 |

内部文件：

| 路径 | 作用 |
|---|---|
| `common/env_setup.sh` | 加载 ROS 工作区、执行阶段06前置链路健康检查、启动任务 |
| `common/preflight_stack_check.sh` | 检查自启动避障链路是否健康 |
| `tasks/stage06/*.py`、`tasks/stage07/*.py` | 调用 `flight_core` 的 Task 层脚本，不直接作为现场入口 |

---

## 运行方式

在机载电脑上：

```bash
cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight
bash stage06/01_manual_takeover_first_check.sh
```

如果目录布局不是项目默认布局，可手动指定 ROS 工作区：

```bash
WS_DIR=/home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite bash stage06/03_low_alt_hover.sh
```

常用保守参数覆盖：

```bash
ALT=0.8 HOVER_TIME=8 bash stage06/03_low_alt_hover.sh
FORWARD_DISTANCE=0.8 FORWARD_SPEED=0.10 bash stage06/04_short_forward.sh
OBSTACLE_STOP_DISTANCE=1.0 bash stage06/05_obstacle_stop.sh
ALT=1.0 CLIMB_SPEED=0.4 TAKEOVER_TIMEOUT=20 bash stage06/06_takeoff_1m_takeover_or_autoland.sh
```

---

## 自启动链路快速复核

阶段06前建议在机载电脑执行：

```bash
systemctl list-units --type=service | grep -Ei 'x400|sensing|mavros|d435|ros'
rostopic echo -n 1 /mavros/state
rostopic echo -n 1 /x400/obstacle/front_distance
rostopic echo -n 1 /mavros/distance_sensor/laser_1_sub
```

如果上述检查失败，先修复自启动链路，不进入阶段06飞行。

---

## 编写新 Task

新增阶段06任务时只调 `Fly` 原语，不直接操作 ROS topic/service：

```python
from flight_core.task_runner import run_task
from flight_core.transport.mavros_transport import MavrosTransport


def add_args(parser):
    parser.add_argument("--my-param", type=float, default=0.5)


def run(fly, args):
    fly.takeoff(args.alt)
    fly.hover(args.hover_time)
    fly.move_forward(args.my_param, alt_m=args.alt)
    fly.land()


if __name__ == "__main__":
    sys.exit(run_task("my_task", add_args, run, MavrosTransport()))
```
