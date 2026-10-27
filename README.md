# Indoor Mapping Drone

> 室内智能建图避障无人机：基于 SLAM 的自主定位、建图、路径规划与动态避障。

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
![Status](https://img.shields.io/badge/status-initializing-orange)

> **项目状态**：初始化阶段。仓库目前只有项目说明、许可证和 <code>.gitignore</code>，感知、建图、规划、控制等模块尚未提交。下方架构、硬件和运行方式为目标方案，代码落地后会同步更新。

## 项目目标

在无 GPS 的室内环境中，让无人机具备以下能力：

1. **自主定位**：融合 IMU、视觉、LiDAR 和光流，在室内稳定估计位姿。
2. **环境建图**：构建占据栅格或点云地图，支持未知环境探索。
3. **路径规划**：根据地图生成安全、可执行的飞行路径。
4. **动态避障**：识别静态与动态障碍，实时重规划并保持安全距离。
5. **仿真到实机**：同一套算法先在 Gazebo 中验证，再迁移到实机。

## 系统架构

~~~text
┌──────────────────────────────────────────────┐
│ 传感器：深度相机 / LiDAR / IMU / 光流          │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 感知与状态估计：VIO / EKF / 点云处理            │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 建图：SLAM / 占据栅格 / 点云地图                │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 规划：全局规划 → 局部规划 → 动态避障            │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 控制：位置/速度控制器 → PX4 飞控 → 电机         │
└──────────────────────────────────────────────┘
~~~

## 硬件清单

以下为参考配置，不是最终 BOM；实际选型会按载重、续航和预算调整。

| 模块 | 参考型号 | 用途 |
| --- | --- | --- |
| 机架 | 250–450 mm 轴距，带桨罩 | 室内安全飞行 |
| 飞控 | Pixhawk 6C / CUAV V5+ | 运行 PX4 |
| 机载计算机 | Jetson Orin Nano / Raspberry Pi 5（轻量方案） | ROS 2、SLAM、规划 |
| 深度相机 | Intel RealSense D435i | 视觉 SLAM、避障 |
| LiDAR | Livox Mid-360 / RPLIDAR A2 | 建图与定位（可选） |
| IMU | ICM42688 / BMI088 | 状态估计 |
| 定高 | 下视激光测距 + 光流 | 室内悬停与定高 |
| 电源 | 4S 5000 mAh LiPo | 按机型调整 |
| 通信 | 2.4 GHz 遥控 + WiFi/数传 | 手动接管与调试 |

## 软件栈

飞控以 PX4 为参考基线，也可以替换为 ArduPilot。

| 层次 | 方案 |
| --- | --- |
| 操作系统 | Ubuntu 22.04 |
| 中间件 | ROS 2 Humble |
| 飞控 | PX4 + MAVROS / micro XRCE-DDS |
| 仿真 | Gazebo Sim / Isaac Sim |
| SLAM | ORB-SLAM3 / Cartographer / LIO-SAM |
| 感知 | OpenCV / PCL / Open3D |
| 规划 | EGO-Planner / Fast-Planner / A* / RRT* |
| 构建 | colcon / CMake / Python |
| CI | GitHub Actions（规划中） |

## 仿真运行方式

> 当前仓库还没有可执行代码，以下命令是目标流程。<code>indoor_mapping_drone</code> 为规划中的 ROS 2 包名，实际包名和 launch 文件以代码落地后的版本为准。

### 1. 准备环境

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Sim
- PX4 Autopilot（SITL）

~~~bash
# PX4 SITL + Gazebo
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
bash Tools/setup/ubuntu.sh
make px4_sitl gz_x500
~~~

### 2. 启动 ROS 2 与项目节点

~~~bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch indoor_mapping_drone simulation.launch.py
~~~

### 3. 验证

- Gazebo 中出现无人机模型和室内场景。
- 运行 <code>ros2 topic list</code> 能看到相机、LiDAR、IMU、<code>/map</code> 等话题。
- 通过 launch 参数切换「定点飞行 / 建图 / 避障」模式。

## 路线图

- [x] **M0 仓库初始化**：确定项目定位、许可证和 README。
- [ ] **M1 仿真基础**：PX4 SITL + Gazebo 室内场景 + 无人机模型。
- [ ] **M2 感知与状态估计**：相机 / LiDAR / IMU 数据接入，VIO / EKF。
- [ ] **M3 建图**：SLAM 输出占据栅格或点云地图。
- [ ] **M4 规划与避障**：全局规划、局部规划、静态/动态障碍。
- [ ] **M5 实机验证**：室内定点、建图、避障飞行。
- [ ] **M6 复现与文档**：数据集、参数、演示视频、测试报告。

## 目录结构（规划）

~~~text
indoor-mapping-drone/
├── docs/          # 设计文档、BOM、实验记录
├── perception/    # 传感器驱动、检测、点云处理
├── mapping/       # SLAM、地图维护
├── planning/      # 全局/局部规划、避障
├── control/       # 位置/速度控制、PX4 接口
├── simulation/    # Gazebo world、模型、launch
├── scripts/       # 安装、标定、运行脚本
└── README.md
~~~

## 设计原则

- **仿真优先**：新算法先在仿真中验证，再上实机。
- **安全第一**：保留手动遥控接管、电子围栏和紧急停止。
- **可复现**：固定依赖版本，保留 launch 文件、参数和 rosbag。
- **小步迭代**：每个里程碑都提交可运行的 demo，而不是一次性堆功能。

## 参与贡献

项目处于早期阶段，欢迎通过 Issue 讨论方案、报告问题或提出硬件建议。提交代码前请先开 Issue 对齐设计，避免大范围返工。

## 许可证

本项目使用 [Apache-2.0](LICENSE) 许可证。
