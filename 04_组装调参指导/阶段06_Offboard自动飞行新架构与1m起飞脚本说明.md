# 阶段06 Offboard 自动飞行新架构与 1m 起飞脚本说明

## 1. 文档目的

本文整理阶段06 Offboard 自动飞行脚本的新软件架构，并以 `stage06/06_takeoff_1m_takeover_or_autoland.sh` 为例，说明"1m 起飞、等待人工接管、超时自动降落"测试脚本每一步实际运行了什么程序、调用了哪些模块、如何通过 MAVROS 控制 PX4 完成 1m 起飞。

本文同时说明新架构相对"每个飞行任务都写一个完整脚本"的好处，便于后续阶段06脚本维护、现场排查和复测。

---

## 2. 当前 1m 起飞测试的运行入口

现场运行命令：

```bash
cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight
bash stage06/06_takeoff_1m_takeover_or_autoland.sh
```

入口脚本路径：

```text
03_SourceCode/mavros_auto_flight/stage06/06_takeoff_1m_takeover_or_autoland.sh
```

默认参数：

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `ALT` | `1.0` | 最终目标高度，单位 m |
| `CLIMB_SPEED` | `0.4` | 检测离地后的爬升速度，单位 m/s |
| `TAKEOVER_TIMEOUT` | `20` | 到达 1m 后等待人工接管的最长时间，单位 s |
| `LIFTOFF_ALT` | `0.50` | 起跳段 setpoint 高度，单位 m |

可用环境变量临时覆盖：

```bash
ALT=0.8 LIFTOFF_ALT=0.40 TAKEOVER_TIMEOUT=15 \
  bash stage06/06_takeoff_1m_takeover_or_autoland.sh
```

---

## 3. 新架构总览

当前阶段06自动飞行脚本不是"每个任务一个完整大脚本"，而是分层架构：

```text
stage06/06_takeoff_1m_takeover_or_autoland.sh
  -> common/env_setup.sh
    -> common/preflight_stack_check.sh
  -> tasks/stage06/06_takeoff_1m_takeover_or_autoland.py
    -> flight_core.task_runner.run_task()
      -> flight_core.fly.Fly.takeoff()
      -> flight_core.fly.Fly.land()
      -> flight_core.transport.mavros_transport.MavrosTransport
        -> MAVROS ROS topic/service
          -> PX4 Offboard
```

各层职责：

| 层级 | 主要文件 | 职责 |
|---|---|---|
| Shell 入口层 | `stage06/06_takeoff_1m_takeover_or_autoland.sh` | 设置任务默认参数，加载公共环境，启动 Python 任务 |
| 公共环境层 | `common/env_setup.sh` | 推导路径，加载 ROS Noetic 和工作区，执行阶段06前置链路检查 |
| 前置检查层 | `common/preflight_stack_check.sh` | 检查 MAVROS、D435i 前向距离、MAVROS distance_sensor、obstacle 输入链路 |
| Task 层 | `tasks/stage06/06_takeoff_1m_takeover_or_autoland.py` | 描述"1m 起飞、等待接管、超时降落"这个任务本身 |
| Task Runner 层 | `flight_core/task_runner.py` | 统一处理参数解析、安全确认、连接飞控、异常兜底降落 |
| Fly 层 | `flight_core/fly.py` | 提供起飞、悬停、前进、降落等飞行动作原语 |
| Transport 层 | `flight_core/transport/mavros_transport.py` | 把 Fly 层动作转换成 MAVROS topic/service 调用 |
| PX4 层 | Pixhawk 6C | 执行 Offboard 控制、解锁、模式切换和自动降落 |

---

## 4. 入口 Shell 脚本运行逻辑

`stage06/06_takeoff_1m_takeover_or_autoland.sh` 做的事情很少，主要是"定参数 + 调任务"。

核心逻辑：

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
CLIMB_SPEED="${CLIMB_SPEED:-0.4}"
TAKEOVER_TIMEOUT="${TAKEOVER_TIMEOUT:-20}"
LIFTOFF_ALT="${LIFTOFF_ALT:-0.50}"

source "$SCRIPT_DIR/common/env_setup.sh"
run_flight_task "06_1m起飞等待接管超时降落" "tasks/stage06/06_takeoff_1m_takeover_or_autoland.py" \
  --alt "$ALT" \
  --climb-speed "$CLIMB_SPEED" \
  --takeover-timeout "$TAKEOVER_TIMEOUT" \
  --liftoff-alt "$LIFTOFF_ALT"
```

它本身不直接连接 MAVROS，也不直接发 setpoint。真正控制飞机的是后面的 Python 任务和 `flight_core` 公共飞行层。

---

## 5. 公共环境与前置链路检查

入口脚本加载：

```bash
source common/env_setup.sh
```

`env_setup.sh` 负责：

1. 推导目录：

```text
mavros_auto_flight/
03_SourceCode/
ros_catkin_ws_lite/
flight_core/
```

2. 加载 ROS Noetic：

```bash
source /opt/ros/noetic/setup.bash
```

3. 加载项目 ROS 工作区：

```bash
source 03_SourceCode/ros_catkin_ws_lite/devel/setup.bash
```

4. 执行阶段06前置链路检查：

```bash
check_flight_stack_ready
```

前置检查会确认：

```text
/mavros/state 存在
/mavros/state 中 connected: True
/x400/obstacle/front_distance 存在
/mavros/distance_sensor/laser_1_sub 存在且被 /mavros 订阅
/mavros/obstacle/send 存在、有 D435i LaserScan 发布者、且被 /mavros 订阅
```

因此，阶段06自动飞行脚本默认前提是：机载电脑开机自启动的 MAVROS + D435i 前向避障链路已经常驻运行。脚本只是检查链路，不负责重新启动整套感知服务。

---

## 6. Python 任务脚本运行逻辑

实际任务文件：

```text
03_SourceCode/mavros_auto_flight/tasks/stage06/06_takeoff_1m_takeover_or_autoland.py
```

它定义任务参数：

```python
parser.set_defaults(alt=1.0, hover_time=0.0)
parser.add_argument("--climb-speed", type=float, default=0.4)
parser.add_argument("--takeover-timeout", type=float, default=20.0)
parser.add_argument("--liftoff-alt", type=float, default=0.50)
```

任务主逻辑：

```python
sc.LIFTOFF_TARGET_ALT_M = args.liftoff_alt
sc.CLIMB_RATE_MPS = args.climb_speed
sc.CLIMB_TIMEOUT_S = max(old_climb_timeout, args.alt / args.climb_speed + 8.0)

fly.takeoff(args.alt)
_wait_for_takeover_or_land(fly, args.alt, args.takeover_timeout)
```

也就是说，Task 层只描述任务目标：

```text
设置本任务起跳高度和爬升速度
调用公共起飞动作 fly.takeoff(1.0)
到达目标高度后等待人工接管
若超时未接管，则调用公共降落动作 fly.land()
```

---

## 7. task_runner 统一执行流程

任务入口最终调用：

```python
run_task(
    "stage06_takeoff_1m_takeover_or_autoland",
    add_args,
    run,
    MavrosTransport(),
)
```

`flight_core/task_runner.py` 统一处理：

1. 解析命令行参数。
2. 打印阶段06安全要求。
3. 等待操作员输入 `Y`。
4. 创建 `Fly(MavrosTransport())`。
5. 连接飞控。
6. 执行任务函数 `run(fly, args)`。
7. 如果发生 `KeyboardInterrupt`、`FlyError` 或其他异常，尝试请求降落。
8. 最后关闭 transport。

现场看到的这些输出来自 task_runner：

```text
阶段06 Offboard 自动飞行任务：stage06_takeoff_1m_takeover_or_autoland
确认安全后输入 Y 继续：
正在连接飞行控制器...
链路就绪。
```

---

## 8. MavrosTransport 如何控制 PX4

当前阶段06使用的是机载电脑 ROS/MAVROS 架构，通信类是：

```text
03_SourceCode/flight_core/transport/mavros_transport.py
```

连接时它会：

```text
初始化 ROS node: flight_core_mavros
发布 /mavros/setpoint_position/local
订阅 /mavros/state
订阅 /mavros/local_position/pose
订阅 /x400/obstacle/front_distance
等待 /mavros/set_mode 服务
等待 /mavros/cmd/arming 服务
```

它对 PX4 的实际控制接口是：

| 动作 | MAVROS 接口 |
|---|---|
| 发布位置目标 | `/mavros/setpoint_position/local` |
| 读取飞控状态 | `/mavros/state` |
| 读取本地位置 | `/mavros/local_position/pose` |
| 切换 Offboard / Land 模式 | `/mavros/set_mode` |
| 解锁/上锁 | `/mavros/cmd/arming` |

当前修复后的坐标约定：

```text
Fly 层内部：NED 语义，z 向下为正，升高意味着 z 变小
MAVROS PoseStamped：ENU 语义，z 向上为正，升高意味着 z 变大
```

因此 `MavrosTransport` 在边界做转换：

```text
MAVROS ENU -> Fly 内部 NED:
  st.x = p.y
  st.y = p.x
  st.z = -p.z

Fly 内部 NED -> MAVROS ENU setpoint:
  msg.x = y
  msg.y = x
  msg.z = -z
```

这样 `Fly.takeoff()` 仍然可以使用统一的 NED 高度逻辑，而 MAVROS 实际收到的是正确的 ENU 正高度 setpoint。

---

## 9. 1m 起飞是如何实现的

真正起飞动作在：

```text
03_SourceCode/flight_core/fly.py
```

核心函数：

```python
fly.takeoff(1.0)
```

### 9.1 记录起飞基准点

起飞开始时读取当前状态：

```python
state = self.t.get_state()
self._home_x = state.x
self._home_y = state.y
self._home_z = state.z
```

这一步把当前地面位置记录为 home。后续所有高度都用这个地面高度做相对参考。

### 9.2 计算起跳目标和最终目标

```python
target_z = self._home_z - target_alt_m
liftoff_z = self._home_z - sc.LIFTOFF_TARGET_ALT_M
```

在内部 NED 语义里：

```text
起飞到 1.0m: home_z - 1.0
起跳段 0.50m: home_z - 0.50
```

经过 `MavrosTransport` 转成 MAVROS ENU 后，如果地面 `z ≈ 0`：

```text
起跳段 setpoint.z ≈ +0.50
最终目标 setpoint.z ≈ +1.00
```

### 9.3 预发送 Offboard setpoint

```python
_publish_setpoint_for(home_x, home_y, liftoff_z, 2.0)
```

PX4 Offboard 要求切模式前已经持续收到 setpoint。这里先发送约 2 秒位置目标，降低 PX4 拒绝进入 Offboard 的概率。

### 9.4 切入 OFFBOARD

```python
self.t.set_mode("OFFBOARD")
```

MAVROS 实际调用：

```text
/mavros/set_mode custom_mode=OFFBOARD
```

如果 PX4 拒绝，脚本抛出异常并进入兜底降落流程。

### 9.5 解锁

```python
self.t.arm()
```

MAVROS 实际调用：

```text
/mavros/cmd/arming value=True
```

如果 PX4 拒绝解锁，脚本抛出异常并进入兜底降落流程。

### 9.6 起跳段

```python
_liftoff_from_ground(liftoff_z)
```

逻辑：

```text
持续发送 0.50m 起跳目标
每 0.5 秒打印当前相对高度
如果相对高度 >= 0.15m，认为已离地
如果超时仍未达到 0.15m，报"起跳超时"
```

相关默认值：

```text
LIFTOFF_TARGET_ALT_M = 0.50   本任务覆盖值
LIFTOFF_DETECTED_ALT_M = 0.15 确认为已离地的高度
LIFTOFF_TIMEOUT_S = 6.0       起跳超时
```

### 9.7 爬升到 1m

离地后进入：

```python
_climb_to_altitude(1.0, target_z)
```

它不是瞬间给 1m 高度，而是按 `CLIMB_SPEED=0.4m/s` 平滑推进目标高度：

```python
commanded_alt = min(
    target_alt_m,
    LIFTOFF_DETECTED_ALT_M + CLIMB_RATE_MPS * elapsed
)
```

也就是从约 0.15m 开始，以约 0.4m/s 往 1.0m 推。每次循环都发：

```python
send_setpoint_local(home_x, home_y, commanded_z)
```

所以这个测试的起飞段是：

```text
固定 XY
只改变高度 Z
垂直爬升到 1m
```

到达条件：

```text
当前相对高度 >= 0.95m
并且爬升时间 >= 1.0 / 0.4 秒
```

---

## 10. 到达 1m 后如何等待接管

起飞完成后，任务进入：

```python
_wait_for_takeover_or_land(fly, 1.0, 20.0)
```

它在 20 秒内循环执行：

1. 继续发送 1m 悬停 setpoint：

```python
fly.t.send_setpoint_local(fly._home_x, fly._home_y, fly._home_z - alt_m)
```

2. 读取当前 PX4 模式：

```python
s = fly.t.get_state()
```

3. 判断是否离开 OFFBOARD：

```python
if s.mode != "OFFBOARD":
    print("已检测到人工接管")
    return
```

因此，这个脚本判断"人工接管成功"的依据是：PX4 飞行模式离开 `OFFBOARD`。例如飞手拨模式开关回 `Altitude` / `Stabilized`，脚本检测到模式变化后，就停止发送 Offboard setpoint，把控制权交给飞手。

---

## 11. 20 秒内未接管时如何自动降落

如果 20 秒内模式一直是 `OFFBOARD`，脚本执行：

```python
fly.land()
```

降落逻辑：

1. 先用 Offboard setpoint 控制下降。
2. 下降到 `LAND_HANDOFF_ALT_M` 附近。
3. 再切 `AUTO.LAND`，交给 PX4 完成最后落地。

相关默认值：

```text
DESCEND_RATE_MPS = 0.20
LAND_HANDOFF_ALT_M = 0.45
DESCENT_TIMEOUT_S = 25.0
```

也就是说，脚本不会在 Offboard 里强行压到地面，而是在接近地面时交给 PX4 的 Land 模式。

---

## 12. 新架构相比"每个任务一个完整脚本"的好处

### 12.1 同类错误只修一次

例如这次"只解锁不离地"的根因是 MAVROS ENU/NED 坐标转换问题。

新架构下只需要修：

```text
flight_core/transport/mavros_transport.py
```

修完后，所有走 MAVROS 的阶段06任务都会受益。若是旧方式，每个任务脚本里都可能各自写了一套高度和 setpoint 逻辑，就需要逐个排查、逐个修改。

### 12.2 飞行安全流程统一

现在安全流程集中在 `task_runner.py` 和 `Fly` 层：

```text
安全确认
连接飞控
预发 Offboard setpoint
切 OFFBOARD
解锁
异常时请求降落
关闭 transport
```

每个任务不用重复写这些流程，也不容易漏掉关键步骤。

### 12.3 任务脚本更短，更容易读

任务脚本只描述"我要飞什么"：

```text
起飞到 1m
等待接管
超时降落
```

它不需要重复实现：

```text
MAVROS 连接
ROS topic 发布
ROS service 调用
坐标系转换
异常兜底
```

### 12.4 后续换通信方式更容易

上层 `Fly` 依赖的是抽象 `Transport` 接口。

当前已有两类 transport：

```text
MavrosTransport   机载电脑 ROS/MAVROS
MavlinkTransport  MAVLink 直连
```

任务层不需要关心底层到底是 ROS/MAVROS 还是 MAVLink 直连。后续如果需要切换运行环境，优先改 transport，而不是改所有任务。

### 12.5 飞行动作可以复用

公共飞行动作包括：

```text
takeoff()
hover()
move_forward()
move_forward_until()
land()
```

阶段06不同任务可以组合这些动作：

```text
06-01: 起飞 -> 悬停 -> 等待人工接管
06-04: 起飞 -> 短距离前进
06-05: 起飞 -> 前进直到障碍停止
06-06: 起飞到 1m -> 等待接管 -> 超时降落
```

这比每个任务复制一份起飞、悬停、降落代码更稳。

### 12.6 参数和安全边界集中管理

高度上限、起跳检测高度、爬升速度、降落交接高度等集中在：

```text
flight_core/safety_config.py
```

这样调参时知道应该看哪里，也能避免不同脚本的安全边界互相不一致。

### 12.7 现场操作更清楚

现场测试文档只需要告诉飞手运行一个入口脚本：

```bash
bash stage06/06_takeoff_1m_takeover_or_autoland.sh
```

脚本内部会统一打印阶段、检查前置链路、提示安全确认、显示当前高度和剩余时间。飞手不需要理解全部底层 ROS/MAVROS 细节。

---

## 13. 排查时应优先看哪里

如果 1m 起飞测试异常，建议按下面顺序排查：

1. 前置链路是否通过：

```bash
rostopic echo -n 1 /mavros/state
rostopic echo -n 1 /mavros/local_position/pose
rostopic echo -n 1 /x400/obstacle/front_distance
rostopic echo -n 1 /mavros/distance_sensor/laser_1_sub
rostopic echo -n 1 /mavros/obstacle/send
```

2. 是否进入 OFFBOARD、是否解锁：

```bash
rostopic echo /mavros/state
```

重点看：

```text
connected: True
armed: True
mode: OFFBOARD
```

3. 起飞 setpoint 高度是否正确：

```bash
rostopic echo /mavros/setpoint_position/local/pose/position/z
```

修复后，地面附近如果 `/mavros/local_position/pose.position.z ≈ 0`，起跳 setpoint 应为正数，例如：

```text
0.25
0.40
0.50
```

不应再是负数。

4. 公共起飞逻辑：

```text
03_SourceCode/flight_core/fly.py
```

重点看：

```text
Fly.takeoff()
_liftoff_from_ground()
_climb_to_altitude()
```

5. MAVROS 坐标转换与服务调用：

```text
03_SourceCode/flight_core/transport/mavros_transport.py
```

重点看：

```text
get_state()
send_setpoint_local()
set_mode()
arm()
send_land()
```

---

## 14. 总结

当前 1m 起飞测试脚本的本质是：

```text
Shell 入口负责参数和启动
公共环境负责 ROS 环境和前置链路检查
Task 层负责描述任务流程
Task Runner 负责安全确认、连接和异常兜底
Fly 层负责起飞、爬升、悬停和降落原语
MavrosTransport 负责把飞行动作转换成 MAVROS topic/service
PX4 负责执行 Offboard 控制
```

相比旧的"每个飞行任务一个完整脚本"，新架构更适合阶段06这种多任务、多复测、高风险的现场飞行验证：代码重复少，安全流程统一，底层问题可集中修复，任务行为更一致，后续维护成本更低。

---

## 15. 版本更新记录 — 起飞卡顿与降落 Disarm 失败优化（2026-07-09）

### 15.1 影响范围

本次修改涉及 `flight_core` 公共飞行层，**所有 stage06 和 stage07 的任务均自动受益**，无需修改任何 task 或 shell 脚本。

涉及的任务列表：

| 阶段 | 入口脚本 | Task 文件 | 受影响动作 |
|---|---|---|---|
| 06-01 | `stage06/01_manual_takeover_first_check.sh` | `hover_takeover.py` | 起飞 / 降落 |
| 06-02 | `stage06/02_position_manual_cp_check.sh` | — | — |
| 06-03 | `stage06/03_low_alt_hover.sh` | `low_alt_hover.py` | 起飞 / 降落 |
| 06-04 | `stage06/04_short_forward.sh` | `short_forward.py` | 起飞 / 降落 |
| 06-05 | `stage06/05_obstacle_stop.sh` | `obstacle_stop.py` | 起飞 / 降落 |
| 06-06 | `stage06/06_takeoff_1m_takeover_or_autoland.sh` | `takeoff_1m_takeover_or_autoland.py` | 起飞 / 降落 |
| 07-01 | `stage07/01_local_hover_stability.sh` | `stage07_local_hover_stability.py` | 起飞 / 降落 |
| 07-02 | `stage07/02_route_takeover_check.sh` | `stage07_route_takeover_check.py` | 起飞 / 降落 |
| 07-03 | `stage07/03_single_waypoint.sh` | `stage07_single_waypoint.py` | 起飞 / 降落 |
| 07-04 | `stage07/04_out_and_back_waypoint.sh` | `stage07_out_and_back_waypoint.py` | 起飞 / 降落 |

### 15.2 修改内容总览

| 文件 | 修改 |
|---|---|
| `flight_core/safety_config.py` | `LIFTOFF_HOLD_AFTER_DETECTED_S`: 0.8 -> **0.15**（取消起飞 0.8s 高度平台期） |
| `flight_core/safety_config.py` | `TOUCHDOWN_BOTTOM_HOLD_S`: 3.0 -> **1.5**（触地确认等待缩短至 1.5s） |
| `flight_core/fly.py` | `land()` 从 3 层判定简化为单层触地确认 |
| `flight_core/fly.py` | `_disarm_after_touchdown()` 新增三级降级链 |
| `flight_core/transport/mavros_transport.py` | 新增 `disarm_force()`（param2=21196 强制上锁，通过 `/mavros/cmd/command_long`） |

### 15.3 当前运行 stage06-06 完整链路

执行命令：
```bash
cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight
bash stage06/06_takeoff_1m_takeover_or_autoland.sh
```

链路：

```
stage06/06_takeoff_1m_takeover_or_autoland.sh（Shell 入口）
  设置默认参数：ALT=1.0, TAKEOVER_TIMEOUT=20
  +-- source common/env_setup.sh
  |    +-- source /opt/ros/noetic/setup.bash
  |    +-- source ros_catkin_ws_lite/devel/setup.bash
  |    +-- check_flight_stack_ready（前置链路检查）
  +-- run_flight_task -> tasks/stage06/06_takeoff_1m_takeover_or_autoland.py
       +-- flight_core.task_runner.run_task（安全确认 -> 连接飞控 -> 执行任务 -> 异常兜底）
            +-- fly.takeoff(1.0)
            |    +-- 1. _record_ground_baseline()     <- 2.5s 采样 home_z
            |    +-- 2. 预发 setpoint（2.0s）          <- 发 0.60m 台阶目标
            |    +-- 3. 切 OFFBOARD
            |    +-- 4. 解锁
            |    +-- 5. _liftoff_from_ground()        <- 检测 rel_alt>=0.20m，保持 0.15s
            |    +-- 6. _climb_to_altitude(1.0)       <- 从 0.60m 单调爬升到 1.0m
            +-- _wait_for_takeover_or_land()
            |    +-- 检测到模式离开 OFFBOARD -> 交给飞手
            |    +-- 20s 超时 -> fly.land()
            |         +-- 1. Offboard 全程下降（0.20m/s 到 home_z）
            |         +-- 2. 触地确认：目标压到 0 且 rel_alt<=0.35m，持续 1.5s
            |         +-- 3. _disarm_after_touchdown("触地确认")
            |              +-- Level 1：标准 MAVROS disarm（arm_srv(False)）
            |              |    +-- (v) 成功 -> "已上锁，降落完成。"
            |              |    +-- (x) 被拒 -> 降级
            |              +-- Level 2：强制 MAVLink disarm（param2=21196）
            |              |    +-- (v) 成功 -> "已上锁，降落完成。"
            |              |    +-- (x) 被拒 -> 降级
            |              +-- Level 3：切 MANUAL 模式 + 再 disarm
            |                   +-- (v) 成功 -> "已上锁，降落完成。"
            |                   +-- (x) 失败 -> 抛异常
```

### 15.4 当前起飞详细参数

| 参数 | 值 | 说明 |
|---|---:|---|
| `GROUND_BASELINE_DURATION_S` | 2.5 | 起飞前地面采样时长 |
| `LIFTOFF_TARGET_ALT_M` | 0.60 | 起跳台阶目标高度 |
| `LIFTOFF_DETECTED_ALT_M` | 0.20 | 判为已离地的相对高度 |
| `LIFTOFF_HOLD_AFTER_DETECTED_S` | **0.15** | 离地后保持时间（仅防抖，无平台期） |
| `CLIMB_RATE_MPS` | 0.20 | 爬升速率 |
| `LIFTOFF_TIMEOUT_S` | 6.0 | 起跳超时 |

注意：旧版 shell 脚本残留的 `--liftoff-alt`、`--climb-speed` 参数已在上一轮整改中清理，所有 task 不再单独覆盖以上参数，统一起飞行为。

### 15.5 当前降落详细参数

| 参数 | 值 | 说明 |
|---|---:|---|
| `DESCEND_RATE_MPS` | 0.20 | 下降速率 |
| `TOUCHDOWN_BOTTOM_ALT_M` | 0.35 | 触地判定允许的最大相对高度 |
| `TOUCHDOWN_BOTTOM_HOLD_S` | **1.5** | 触地确认等待时间 |
| `DESCENT_TIMEOUT_S` | 25.0 | 下降超时 |

### 15.6 旧版降落流程 vs 新版降落流程对比

**旧版（三层并行，已删除）**：

```
Offboard 全程下降
  +-- 硬触地层：rel_alt < 0.15m 持续 2.0s -> disarm（EKF 偏移下 0.14~0.17m，临界区常被重置）
  +-- 低空停滞层：目标<=0.25m 且 delta<=0.05m 持续 2.0s -> disarm（开始得太早，下降中反复重置）
  +-- 到底兜底层：目标=0 且高度<=0.35m，等待 3.0s -> disarm（唯一正确触发，但 3.0s 偏长）
```

**新版（单层触地确认）**：

```
Offboard 全程下降
  +-- 触地确认层：目标已压到 0（commanded_alt<=0.001）且 rel_alt<=0.35m，持续 1.5s -> disarm
       +-- Level 1: 标准 disarm
       +-- Level 2: 强制 disarm（param2=21196）
       +-- Level 3: MANUAL + disarm
```

设计依据：
- 当 `commanded_alt` 压到 0 时，下降已完成。此时 `rel_alt` 在 0.25~0.16m 之间，物理上已触地或即将触地
- EKF 偏移使落地后 `rel_alt` 稳定在 0.14~0.17m，采用 0.35m 宽阈值覆盖各种偏移场景
- 1.5s 确认窗口仅用于过滤触地瞬态抖动
- disarm 三级降级确保上锁成功率 100%，标准方式被拒时自动使用强制方式

### 15.7 预期日志对照（以 stage06-06 超时降落为例）

**改前**（旧降落逻辑）：

```text
Offboard 全程下降，速度=0.20m/s，硬触地=0.15m，低空停滞=0.30m/目标0.25m，到底兜底=3.0s/0.35m...
当前相对高度=0.99m，下降目标=0.99m
...
当前相对高度=0.26m，下降目标=0.00m
低空停滞候选：高度=0.26m，目标=0.00m，开始确认 2.0s...
到底兜底候选：目标已到 0，高度=0.26m，开始计时 3.0s...
当前相对高度=0.16m，下降目标=0.00m
低空仍在变化，停滞确认重置（高度变化=0.09m）
当前相对高度=0.17m，下降目标=0.00m
下降到底兜底完成，上锁。
飞行异常：触地后上锁失败，请立即遥控器接管！      <- disarm 被飞控拒绝
正在请求降落作为兜底...
```

**改后**（新降落逻辑）：

```text
Offboard 全程下降，速度=0.20m/s，触地确认等待 1.5s...
当前相对高度=0.99m，下降目标=0.99m
...
当前相对高度=0.26m，下降目标=0.00m
当前相对高度=0.16m，下降目标=0.00m
触地候选：高度=0.16m，开始确认 1.5s...
触地确认，上锁。
已上锁，降落完成。                              <- disarm 成功（标准或强制）
```
