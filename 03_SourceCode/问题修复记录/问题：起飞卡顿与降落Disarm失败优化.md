# 问题：起飞卡顿与降落 Disarm 失败优化

## 背景

阶段07-01（定点悬停与局部坐标稳定性检查）测试中，启用地面基准采样+三层触地判定后的近两次飞行（2026-07-09 11:20 / 11:34）暴露出两个问题：

1. **起飞阶段**：离地检测（0.23m）后进入 0.8s 保持，期间高度无增长，产生视觉"卡顿"
2. **降落阶段**：三层判定机制存在内部竞争，最终 disarm 被飞控拒绝

本报告基于前两次整改报告：
- [问题：起飞不够果断和降落硬着陆弹跳.md](file:///d:/TRAE_Project/AI_p_airplean/Pixhawk%206C_X400_workspeace/06_飞行日志分析/分析报告/问题：起飞不够果断和降落硬着陆弹跳.md)
- [问题：自动起飞和降落判定整改.md](file:///d:/TRAE_Project/AI_p_airplean/Pixhawk%206C_X400_workspeace/06_飞行日志分析/分析报告/问题：自动起飞和降落判定整改.md)

---

## 根因分析

### 1. 起飞 0.8s 卡顿 ✅ 已修复

**代码位置**：[fly.py#L518-L531](file:///d:/TRAE_Project/AI_p_airplean/Pixhawk%206C_X400_workspeace/03_SourceCode/flight_core/fly.py#L518-L531)

**根因**：检测到 `rel_alt ≥ 0.20m` 后进入 0.8s 保持，但保持期内 setpoint 与爬升段首帧相同（都是 0.60m），保持段没有实际作用。

- 0.8s 保持来源于旧代码中回缩 bug 的规避措施，回缩 bug 已修复，0.8s 不再必要
- 飞机在 0.23m 处高度不涨是因为地面效应（0.2~0.5m 区间升力效率低），不是 setpoint 问题

**修复**：`LIFTOFF_HOLD_AFTER_DETECTED_S` 从 0.8s 缩短到 0.15s，仅保留 1~2 控制周期的防抖，不再产生肉眼可见停顿。

**二次优化（2026-07-09 第二轮）**：检测阈值从 0.20m 提高到 0.40m，台阶目标从 0.60m 提高到 0.70m。飞机在 0.40m 时才判定"已离地"，此时已明显脱离地面效应区，加上更高的台阶目标使油门响应更积极，起飞外观更果断。

### 2. 降落三层判定内部竞争 ⚠️ 问题仍然存在

降落逻辑仍为修改前的三层并行判定：

| 层级 | 条件 | 问题 |
|---|---|---|
| **硬触地** | `rel_alt < 0.15m` 持续 2.0s | EKF 偏移下落地后高度稳定在 0.14~0.17m，刚好在阈值临界区，确认被重置 |
| **低空停滞** | `commanded_alt ≤ 0.25m` 且 `rel_alt ≤ 0.30m`，2.0s 内高度变化 ≤ 0.05m | 启动时机过早，飞机还在 0.25→0.16m 自然下降中，变化 Δ=0.09~0.11m > 0.05m，反复重置 |
| **到底兜底** | `commanded_alt ≤ 0.001` 且 `rel_alt ≤ 0.35m`，等待 3.0s | 正确触发，但 3.0s 偏长 |

### 3. Disarm 被飞控拒绝 ❌ 未修复

标准 MAVROS disarm 发送 `MAV_CMD_COMPONENT_ARM_DISARM`（`param2=0`），PX4 检查 `vehicle_land_detected.landed` 状态。

由于 EKF local_position 的相对高度在物理触地后稳定在 0.14~0.17m，PX4 的着陆检测器认为飞机尚未落地，拒绝 MAVLink disarm。

**遥控器能正常 disarm** 说明飞控侧 ARMING_CHECK 正常，仅 MAVLink 权限等级的问题。

**本轮的强制 disarm 方案被还原**：尝试通过 `/mavros/cmd/command_long` 发送 `param2=21196`（PX4 强制标志），但 Jetson 上的 MAVROS 版本没有暴露 `CommandLong` 服务，导入即报错，阻塞了整个飞行初始化。已安全回退，等后续找到兼容方案再处理。

---

## 本轮实际修改内容

| 文件 | 改动 | 状态 |
|---|---|---|
| `safety_config.py` | `LIFTOFF_HOLD_AFTER_DETECTED_S`: 0.8 → **0.15** | ✅ 已保留 |
| `safety_config.py` | `LIFTOFF_DETECTED_ALT_M`: 0.20 → **0.40** | ✅ 二次优化 |
| `safety_config.py` | `LIFTOFF_TARGET_ALT_M`: 0.60 → **0.70** | ✅ 二次优化 |
| `safety_config.py` | `TOUCHDOWN_BOTTOM_HOLD_S`: 3.0 → **1.5** → 恢复 **3.0** | ↩️ 已回退 |
| `fly.py` | `land()` 从 3 层简化到单层 → 恢复为 3 层 | ↩️ 已回退 |
| `fly.py` | `_disarm_after_touchdown()` 三级降级链 → 恢复为简单 disarm | ↩️ 已回退 |
| `mavros_transport.py` | 新增 `disarm_force()` 及 `CommandLong` 导入 → 全部移除 | ↩️ 已回退 |

**最终保留了三个改动**：起飞保持时间 0.8→0.15s、离地检测阈值 0.20→0.40m、台阶目标 0.60→0.70m。

## 遗留问题

1. **降落 disarm 仍会被飞控拒绝**：bottom 层 3.0s 触发 disarm 后，标准 MAVROS disarm 因 land_detected 不成立被拒。需要找到 Jetson MAVROS 兼容的强制 disarm 方案。
2. **三层判定中 stall 层启动时机问题**：0.25m 启动过早，在 0.25→0.16m 下降过程中反复重置。理论上不是阻塞问题（bottom 层 3.0s 必定兜底），但日志混乱，后续可优化。

## 后续验证要点

1. 运行阶段07-01 脚本，起飞段日志不应再出现"继续保持台阶目标 0.8s"字样
2. 降落段日志仍为三层交错输出（原逻辑未改），但 bottom 层 3.0s 兜底应正常触发
3. 触地后 disarm 被拒的问题仍然存在，需要飞手在落地后通过遥控器上锁
