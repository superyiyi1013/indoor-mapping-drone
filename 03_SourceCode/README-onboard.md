# X400 室内避障无人机 — 机载电脑源码

> 此仓库为 `03_SourceCode/`，**Windows 开发 → Git 同步 → 机载电脑拉取实飞**。

| 电脑    | 路径                                        |
| :---- | :---------------------------------------- |
| 机载电脑1 | `/home/<user>/X400_workspace/03_SourceCode` |
| 机载电脑2 | `/home/<user>/X400_workspace/03_SourceCode` |

### SSH 连接

| 电脑    | 网络   | 命令                       |
| :---- | :--- | :----------------------- |
| 机载电脑1 | 手机热点 | `ssh user@`              |
| 机载电脑1 | 路由器  | `ssh user@<onboard-ip-1>` |
| 机载电脑2 | 手机热点 | `ssh user@<onboard-ip>` |
| 机载电脑2 | 路由器  | `ssh user@<onboard-ip-2>` |
| 任意电脑  | —    | `sudo poweroff`（关机）      |

### 本地开发

Windows 终端进入本项目目录：

```bash
cd "D:\TRAE_Project\AI_p_airplean\Pixhawk 6C_X400_workspeace"
codex
cd "D:\TRAE_Project\AI_p_airplean\Pixhawk 6C_X400_workspeace\03_SourceCode"
codex
```

## 快速上手（机载电脑）

## 同步windows程序源码的命令

```bash
# 1. 拉取最新代码（安全合并本地修改）
# 进入 03_SourceCode 目录
cd /home/<user>/X400_workspace/03_SourceCode
# 从远程仓库拉取最新代码并自动合并
git pull

# 2. 强制覆盖为远程版本（丢弃所有本地修改，谨慎使用）
# 进入 03_SourceCode 目录
cd /home/<user>/X400_workspace/03_SourceCode
# 从远程仓库获取最新数据但不自动合并
git fetch origin
# 强制将本地代码重置为远程版本（本地修改会丢失）
git reset --hard origin/master

# 3. 查看本次更新内容
# 查看最近 5 次提交记录
git log --oneline -5
# 查看最近 1 次提交记录（看最新一次改了什么）
git log --oneline -1
```

### 编译 ROS 工作区

并非每次拉取代码都要编译。以下情况才需要：

- 修改了 **C++ 节点**（`.cpp` 文件）
- 修改了 **msg/srv/action 定义**（消息接口变更）
- 新增了 **Python 可执行节点**（需要 `catkin build` 来创建可执行符号链接）

如果只改了 Python 脚本（`.py`）的逻辑，直接运行即可，**不需要重新编译**。

需要编译时执行：

```bash
# 直接进入本项目 ROS 工作区目录
cd /home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite
# 加载 ROS 环境变量（必须，否则 catkin build 会报找不到 catkin 模块）
source /opt/ros/noetic/setup.bash
# 重新编译整个 ROS 工作区
catkin build
```

***

## 目录结构

```
03_SourceCode/
├── .gitignore                      ← 不入库规则（ROS build/devel/__pycache__ 等）
├── CHANGELOG.md                    ← 版本变更日志
├── logs/                           ← 飞行/感知日志，实飞后查看
│   ├── sensing_stack.log           ← bootstrap 开机自启日志（MAVROS + D435i）
│   ├── stage03_01_mavros.log
│   ├── stage03_02_mavros.log
│   ├── stage04_01_d435i.log
│   ├── stage04_01_rs_devices.txt
│   ├── stage04_01_lsusbs.txt
│   ├── stage04_02_front_distance.log
│   └── stage05_01_stack.log
│
├── 问题修复记录/                    ← 实飞问题分析与修复记录
│   ├── 问题：自动起飞和降落判定整改.md
│   ├── 问题：起跳段超时判定过于刚性导致低电量起飞失败.md
│   ├── 问题：起飞不够果断和降落硬着陆弹跳.md
│   ├── 问题：起飞卡顿与降落Disarm失败优化.md
│   └── 问题：降落触地后OFFBOARD模式下无法Disarm.md
│
├── flight_core/                    ← 飞控核心 Python 库（三层架构 Transport → Fly → Task）
│   ├── fly.py                      ← 飞行原语：takeoff / hover / move_forward / land
│   ├── safety_config.py            ← 全局限幅 / 速率 / 超时（单点修改全局生效）
│   ├── task_runner.py              ← 任务调度器
│   └── transport/                  ← 可插拔通信层
│       ├── mavlink_transport.py    ← MAVLink 直连（Windows 数传用）
│       └── mavros_transport.py     ← MAVROS 封装（机载 ROS 用）
│
├── mavros_auto_flight/             ← 机载电脑实飞任务脚本（Offboard 模式）
│   ├── common/                     ← 通用工具
│   │   ├── env_setup.sh
│   │   └── preflight_stack_check.sh
│   ├── stage06/                    ← 阶段06：短距离避障飞行脚本
│   │   ├── 01_manual_takeover_first_check.sh
│   │   ├── 02_position_manual_cp_check.sh
│   │   ├── 03_low_alt_hover.sh
│   │   ├── 04_short_forward.sh
│   │   ├── 05_obstacle_stop.sh
│   │   └── 06_takeoff_1m_takeover_or_autoland.sh
│   ├── stage07/                    ← 阶段07：光流方案自动飞行脚本
│   │   ├── 00_takeoff_hover_land.sh
│   │   ├── 01_local_hover_stability.sh
│   │   ├── 02_route_takeover_check.sh
│   │   ├── 03_single_waypoint.sh
│   │   ├── 04_out_and_back_waypoint.sh
│   │   ├── 05_rectangle.sh
│   │   └── 06_fence_check.sh
│   ├── tasks/                      ← 飞行任务 Python 节点
│   │   ├── stage06/                ← 阶段06任务
│   │   │   ├── 01_hover_takeover.py
│   │   │   ├── 03_low_alt_hover.py
│   │   │   ├── 04_short_forward.py
│   │   │   ├── 05_obstacle_stop.py
│   │   │   └── 06_takeoff_1m_takeover_or_autoland.py
│   │   └── stage07/                ← 阶段07任务
│   │       ├── 00_takeoff_hover_land.py
│   │       ├── 01_local_hover_stability.py
│   │       ├── 02_route_takeover_check.py
│   │       ├── 03_single_waypoint.py
│   │       ├── 04_out_and_back_waypoint.py
│   │       ├── 05_rectangle.py
│   │       └── 06_fence_check.py
│
├── test/                           ← 逐阶段验收测试文档
│   ├── 00_总控/                    ← 验收总表 / 准入规则 / 参数基线 / 退操作 / 问题模板
│   ├── 阶段01_基础飞行基线验收/     ✅ 通过
│   ├── 阶段02_MAVLink数传自动飞行验收/ ✅ 通过
│   ├── 阶段03_机载计算机MAVROS接入验收/ ✅ 通过
│   ├── 阶段04_D435i前向感知验收/    ✅ 通过
│   ├── 阶段05_PX4避障链路验收/      ✅ 通过
│   ├── 阶段06_Offboard短距离避障飞行验收/ 🔵 进行中
│   ├── 阶段07_光流方案的自动飞行测试/ 🔵 进行中
│   └── 阶段99_扩展能力预留/         --- 视觉定位 / 多向避障 / 路径规划
│
└── ros_catkin_ws_lite/             ← ROS Noetic 工作区
    └── src/
        ├── realsense-ros/          ← Intel RealSense ROS 驱动
        ├── x400_bringup/           ← 开机自启：MAVROS + D435i + 避障链路
        └── x400_perception/        ← 前向障碍距离计算节点
```

***

## 层架构说明

```
[Task 层]      mavros_auto_flight/tasks/     ← 只描述"做什么"
    ↓ 调用
[Fly 层]       flight_core/fly.py             ← 飞行原语，不依赖通信方式
    ↓ 调用
[Transport 层] flight_core/transport/         ← 可插拔：MAVLink / MAVROS
```

Windows 数传电台实飞调试用 `MavlinkTransport`，机载电脑实飞用 `MavrosTransport`，飞行逻辑不变。

***

## 机载电脑环境依赖

| 组件                  | 说明                                    |
| :------------------ | :------------------------------------ |
| ROS Noetic          | Ubuntu 20.04                          |
| MAVROS              | 机载 ↔ Pixhawk 串口 `/dev/ttyTHS0:921600` |
| Intel RealSense SDK | D435i 驱动                              |
| Python 3            | numpy / rospy / sensor\_msgs          |

开机自启链路：`systemd` → `bootstrap_sensing_stack.sh` → MAVROS + D435i + 前向距离节点

***

## 多机同步方案

两台 Allspark-Orin NX（机载电脑1/2）共用同一套源码 + ROS 工作区。提供两种方案，根据场景选用。

***

## 方案一：从零 Git 部署（新机器首次搭建）

不依赖其他机载电脑，只要有 Git 仓库和网络即可。适合新机器首次部署。

完整步骤（系统安装 → 拉取编译 → 串口配置 → 链路验证 → 开机自启）详见 [初始化指南.md](初始化指南.md)，此处只列概要：

1. 安装 ROS Noetic、MAVROS、RealSense 驱动
2. 配置 SSH 密钥，`git clone` 本项目
3. `catkin build` 编译工作区
4. QGC 设置飞控 `MAV_2_CONFIG=TELEM3`、`SER_TEL3_BAUD=921600`
5. 确认 `/dev/ttyTHS0` 存在，用户在 `dialout` 组
6. 手动启动 `bootstrap_sensing_stack.sh`，检查 `/mavros/state` 和 `/x400/obstacle/front_distance`
7. 配置 `px4-perception.service` 开机自启动

### 后续同步

日常迭代操作见上文「[同步 windows 程序源码的命令](#同步windows程序源码的命令)」和「[编译 ROS 工作区](#编译-ros-工作区)」，不再重复。

完整初始化流程详见 [初始化指南.md](初始化指南.md)。

***

## 方案二：rsync 整盘同步（快速复制已有环境）

从已开发好的机器整盘推送到目标机，含编译产物，到手即用。适合多机快速复制或日常增量同步。

### 前提：SSH 免密登录

在\*\*源机器（机载电脑2）\*\*上执行，把公钥发给目标机器（只需做一次）：

```bash
# 生成 ed25519 类型密钥对（一路回车即可）
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
# 将公钥推送到机载电脑1（会提示输入目标机密码）
ssh-copy-id user@<onboard-ip-1>
# 若后续有新机器（如 <onboard-ip-3>），同理追加
ssh-copy-id user@<新机器IP>
```

### 从源机器推送到目标机器

在\*\*已开发好的机器（机载电脑2）\*\*上执行：

```bash
# 将本机（机载电脑2）整个工作区推送到机载电脑1（-avz：归档+压缩显示，--delete：删除目标机多余文件，--progress：显示进度）
rsync -avz --delete --progress /home/<user>/X400_workspace/ user@<onboard-ip-1>:/home/<user>/X400_workspace/
```

这条命令会将**整个工作区**（含 `ros_catkin_ws_lite/build/`、`devel/` 等编译产物）推送到目标机，目标机拿到手即可直接运行，无需重新 `catkin build`。

### 在新机器上一键拉取

如果是**全新空机器**，在其上执行一条命令即可从源机器拉取全部内容（需先配好 SSH 免密，见上文）：

```bash
# 在新机器上运行，从机载电脑2（<onboard-ip-2>）拉取全部数据（-avz：归档+压缩显示，--progress：显示进度）
rsync -avz --progress user@<onboard-ip-2>:/home/<user>/X400_workspace/ /home/<user>/X400_workspace/
```

### 日常增量更新

```bash
# 在机载电脑2上执行，推送到机载电脑1（--delete 保持两端完全一致）
rsync -avz --delete --progress /home/<user>/X400_workspace/ user@<onboard-ip-1>:/home/<user>/X400_workspace/
```

> **原理**：`rsync` 基于 SSH，只传差异部分（增量同步），第二次起比 `scp` 快得多。`--delete` 保证目标机与源机完全一致。
>
> **无需梯子/仓库**：不走 Git 推送拉取，尤其适合 ROS 编译产物（`build/`、`devel/`）不入库的场景。
>
> 安全起见，可先用 `-n`（dry-run）试运行：`rsync -avz --delete --dry-run ...`

***

## 对比选型

| 对比项        | 方案一：Git 从零部署                    | 方案二：rsync 整盘同步   |
| :--------- | :------------------------------ | :--------------- |
| 首次部署速度     | 慢（需安装依赖 + 编译）                   | 快（含编译产物，到手即用）    |
| 是否依赖其他机载电脑 | 否，有 Git 仓库即可                    | 是，需 SSH 互访       |
| 空间占用       | 小（仅源码 + 编译产出）                   | 大（完整镜像）          |
| 日常更新       | `git pull` + `catkin build`，分钟级 | `rsync` 增量同步，秒级  |
| 适用场景       | 新机器首次搭建，或无法直连源机                 | 快速复制已有环境，或日常增量同步 |

