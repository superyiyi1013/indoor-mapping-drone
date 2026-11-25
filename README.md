# Indoor Mapping Drone

> 室内无 GPS 环境下的 PX4 无人机自主飞行与前向避障基线：光流定位、MAVROS / Offboard、D435i 深度感知。

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
![Status](https://img.shields.io/badge/status-stage--06-blue)
![ROS](https://img.shields.io/badge/ROS-Noetic-22314E)
![PX4](https://img.shields.io/badge/PX4-v1.16.2-6A5ACD)

> **定位说明**：仓库名保留了 `indoor-mapping-drone`，但当前实现是“室内自主飞行 + 前向避障”基线，**SLAM / 建图尚未实现**，列在路线图 M4。当前只做前向 D435i 避障，不具备全向避障能力。

## 项目概览

| 项目 | 内容 |
| --- | --- |
| 目标 | 室内无 GPS 环境下完成稳定起飞、悬停、Offboard 自动飞行和前向避障 |
| 飞控 | Pixhawk 6C，PX4 v1.16.2 |
| 机架 | X400 四旋翼，400 mm 轴距 |
| 机载电脑 | Allspark2 / Jetson Orin NX，Ubuntu 20.04 |
| 定位 | MTF-02 光流 + 下视测距，PX4 EKF2 |
| 感知 | Intel RealSense D435i，前向深度 |
| 中间件 | ROS Noetic + MAVROS |
| 当前阶段 | 阶段 06：Offboard 短距离避障实飞（进行中） |

## 当前进度

| 阶段 | 能力 | 状态 |
| --- | --- | --- |
| 01 | 基础飞行基线（上电 / 遥控 / 光流 / 悬停 / 续航） | ✅ 2026-06-01 |
| 02 | MAVLink 数传自动飞行 | ✅ 2026-06-05 |
| 03 | 机载计算机 MAVROS 接入 | ✅ 2026-06-07 |
| 04 | D435i 前向感知（深度图 + 前向距离） | ✅ 2026-06-10 |
| 05 | PX4 避障链路（Collision Prevention 拆桨测试） | ✅ 2026-06-11 |
| 06 | Offboard 短距离避障飞行（上桨实飞） | 🔵 进行中 |
| 07 | 光流方案局部航点 / 矩形 / 圆形近似 | ⏳ 脚本与文档已准备，未验收 |

## 系统架构

### 感知与避障链路

```text
D435i
  -> /camera/depth/image_rect_raw
  -> x400_perception/front_obstacle_distance_node.py
  -> /x400/obstacle/front_distance
  -> /mavros/distance_sensor/laser_1_sub + /mavros/obstacle/send
  -> PX4 Collision Prevention
  -> QGC MAVLink Inspector (DISTANCE_SENSOR id=42, orientation=0)
```

### 飞行控制架构

```text
Task 层  mavros_auto_flight/tasks/*.py
   只描述“做什么”：起飞、悬停、前进、遇障停止、航点、降落
        ↓
Fly 层   flight_core/fly.py
   飞行原语：takeoff / hover / move_forward_until / move_to_local_offset / land
        ↓
Transport 层  flight_core/transport/*.py
   MAVROS（机载 Linux）/ pymavlink（Windows 地面站）
        ↓
PX4 / Pixhawk 6C
```

## 硬件清单

| 模块 | 型号 | 说明 |
| --- | --- | --- |
| 机架 | X400（400 mm，X 型） | 8 寸桨，室内低速飞行 |
| 飞控 | Pixhawk 6C | PX4 v1.16.2 |
| 机载电脑 | Allspark2 / Orin NX | Ubuntu 20.04，ROS Noetic |
| 定位 | MTF-02 光流 + 测距 | 室内无 GPS 定点 / 定高 |
| 感知 | Intel RealSense D435i | 前向深度，USB 3.0 |
| 电池 | 4S 3000 mAh | XT60 |
| 遥测 | LQ 2.4G 数传 | QGC 监控 |
| 遥控 | 2.4G 遥控器 | 人工接管 |

## 软件栈

| 层次 | 方案 |
| --- | --- |
| 飞控固件 | PX4 v1.16.2 |
| 机载系统 | Ubuntu 20.04 |
| 中间件 | ROS Noetic、MAVROS |
| 感知 | RealSense ROS、OpenCV / NumPy |
| 飞行逻辑 | Python 3、`flight_core` 三层架构 |
| 自启动 | systemd + `bootstrap_sensing_stack.sh` |
| 日志 | PX4 ULog（`.ulg`）、ROS topic 检查 |

## 目录结构

```text
indoor-mapping-drone/
├── 01_项目文档/                 # 项目指南、架构、硬件、进度
├── 02_固件与配置/参数配置/       # PX4 参数基线与 diff 工具
├── 03_SourceCode/               # 机载代码
│   ├── flight_core/             # Transport → Fly → Task 核心
│   ├── mavros_auto_flight/      # 阶段 06/07 任务与入口脚本
│   ├── ros_catkin_ws_lite/      # x400_bringup / x400_perception / realsense-ros
│   └── test/                    # 阶段验收文档
├── 04_组装调参指导/              # 装机、调参、现场速查
├── 05_硬件资料/                  # 模块说明与接线
└── 06_飞行日志分析/              # 日志分析脚本与问题记录（不含 .ulg）
```

## 快速开始

### 机载电脑（实机）

1. 上电，确认 systemd 已启动感知链路（服务名以机载电脑实际配置为准）：
   ```bash
   systemctl status <x400-sensing-service>
   ```
2. 确认 MAVROS 与前向距离：
   ```bash
   rostopic echo -n 1 /mavros/state
   rostopic echo -n 1 /x400/obstacle/front_distance
   ```
3. 运行阶段 06 任务（示例）：
   ```bash
   cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight
   bash stage06/05_obstacle_stop.sh
   ```
4. 按脚本提示完成安全确认，遥控器保持可接管。

> 文档中的 `<user>`、`<onboard-ip>` 为占位符，请替换为实际值。

### 地面站 / 开发机

当前仓库还没有自动化测试和 SITL 仿真；相关命令会在对应模块落地后补充。

## 安全说明

- 首次测试必须拆桨；上桨测试需要安全员、空旷场地和可随时接管。
- 只做前向 D435i 避障，侧向、后向没有避障保护，禁止把侧飞 / 倒飞当作受保护动作。
- 飞行前确认 PX4 参数、光流 / 测距、MAVROS 链路和 QGC 状态。
- 任何异常优先切出 OFFBOARD，由飞手接管。
- 详细检查表见 `03_SourceCode/test/` 各阶段文档。

## 路线图

- [x] **M1 感知与安全基线**：阶段 01–05，光流定位 + D435i 前向距离 + PX4 Collision Prevention。
- [ ] **M2 Offboard 自动飞行**：阶段 06，短距离前进、遇障停止、人工接管。
- [ ] **M3 局部航点**：阶段 07，单边、往返、矩形、圆形近似。
- [ ] **M4 建图与定位**：D435i + RTAB-Map / ORB-SLAM3，输出占据栅格或点云。
- [ ] **M5 规划与动态避障**：全局 / 局部规划，动态障碍重规划。
- [ ] **M6 仿真与复现**：PX4 SITL + Gazebo + MAVROS，自动化测试与演示。

## 文档索引

- 项目总指南：`01_项目文档/X400 避障无人机项目指南.md`
- 飞行软件架构：`01_项目文档/飞行软件架构说明.md`
- 硬件与端口：`01_项目文档/硬件框架与端口分配.md`
- 阶段验收：`03_SourceCode/test/`
- 变更记录：`03_SourceCode/CHANGELOG.md`
- 机载同步说明：`03_SourceCode/README-onboard.md`

## 许可证

本项目使用 [Apache-2.0](LICENSE)。`03_SourceCode/ros_catkin_ws_lite/src/realsense-ros/` 为 Intel RealSense ROS 的第三方代码，遵循其原始 Apache-2.0 许可证。
