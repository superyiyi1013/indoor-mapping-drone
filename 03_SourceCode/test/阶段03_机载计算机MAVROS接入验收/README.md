# 阶段03 — 机载计算机 MAVROS 接入验收

## 阶段目标

验证机载计算机（Allspark2 / Jetson）与 Pixhawk 6C 之间的 MAVROS 通信链路完整可用，包括：

- 机载电脑系统稳定性与 ROS 基础环境
- Pixhawk T3（TELEM3）串口硬件链路
- MAVROS 只读遥测数据读取
- MAVROS Offboard 接管与遥控器人工接管

> 本阶段只验证机载电脑与 Pixhawk 的 MAVROS 链路，**不涉及 D435i 感知和 PX4 避障**。

---

## 测试清单

按顺序执行，每一项通过后方可进入下一项。

| # | 文档 | 内容 | 安全要求 |
|---|---|---|---|
| 0 | [00_链路手动启动与开机自启动配置教程](00_链路手动启动与开机自启动配置教程.md) | 新电脑上如何手动拉起 `MAVROS`，以及如何配置 `systemd` 开机自启动 | 不解锁、不起飞 |
| 1 | [01_机载电脑系统与串口链路检查](01_机载电脑系统与串口链路检查.md) | 系统供电检查、SSH 登录、ROS 环境、串口硬件与 PX4 参数确认、MAVROS 只读遥测连接验证 | 不接桨，不上电；MAVROS 测试不解锁、不起飞 |
| 2 | [02_MAVROS拆桨Offboard接管测试](02_MAVROS拆桨Offboard接管测试.md) | Offboard 模式切换、setpoint 发送、遥控器接管验证 | **必须拆桨** |

---

## 前置依赖

- 机载电脑已安装 ROS Noetic 和 MAVROS
- ROS 工作区已编译（`ros_catkin_ws_lite`）
- Pixhawk 6C 已刷写 PX4，T3/TELEM3 串口 MAVLink 已配置
- 遥控器接收机已对频，PX4 遥控器校准已完成

---

## 硬件连接示意

```
                   串口1 (TX/RX/GND)
  机载电脑 ──────────────────────── Pixhawk 6C
(Jetson/Orin)       /dev/ttyTHS0       T3/TELEM3
                                        │
                                    数传电台 ─── QGC (地面站)
```

- 波特率：921600
- MAVLink 协议：v2
- 共地要求：GND 必须连通

---

## 退出条件 / 通过标准

- 全部 2 项测试均为"通过"。
- 任何一项"未通过"时，记录问题并修复后重新执行该单项。
