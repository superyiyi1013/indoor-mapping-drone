# 问题：降落触地后 OFFBOARD 模式下无法 Disarm

## 背景

阶段07 自动降落测试中，脚本检测到触地后调用 MAVLink disarm，被 PX4 拒绝。飞机已物理触地，但 3 次 disarm 全部返回 `service_ok=False`。

先后尝试了两种方案均未成功：

| 尝试 | 结果 | 原因 |
|---|---|---|
| 触地后继续发地面 setpoint，等 PX4 自然检测着陆再 disarm（8s 超时降级） | ❌ 失败 | OFFBOARD 模式下活跃的位置控制器阻塞了着陆检测，has_landed() 始终 false |
| 修复 setpoint 高度错误后再次测试 | ❌ 同样失败 | 根因相同——OFFBOARD 模式下着陆检测无法触发 |

---

## 根因

PX4 的 MAVLink disarm 命令（`MAV_CMD_COMPONENT_ARM_DISARM`）在 `param2=0`（正常模式）时会检查 `vehicle_land_detected.landed` 状态，只有 `landed=true` 时才允许 disarm。

但在 OFFBOARD 模式下，即使脚本发送的是地面高度 setpoint，PX4 的位置控制器仍在活跃工作：

```
触地后 setpoint = (land_x, land_y, home_z)    ✅ 正确的地面坐标
       ↓
PX4 位置控制器检测到：位置误差 ≈ 0，速度误差 ≈ 0
       ↓
控制器输出维持性推力（悬停推力水平 ≈ 0.6）
       ↓
着陆检测器需求：指令推力必须明显超过实际推力（地面支撑了机体重量）
但由于飞机已在地面且位置误差为零，差异不够显著
       ↓
ground_contact 无法触发 → has_landed() 始终 false
       ↓
MAVLink disarm 被拒绝
```

**关键认知**：在 OFFBOARD 模式下，持续发地面 setpoint 反而让 PX4 着陆检测器无法判断飞机已经着陆——因为"位置已到、速度为零"被解释为"位置控制正常收敛"，而不是"飞机触地了"。

---

## 最终方案：触地后切入 AUTO.LAND

### 思路

参考 PX4 官方 Land Mode 文档——AUTO.LAND 模式下 PX4 的着陆检测器能正常工作，检测到触地后 `COM_DISARM_LAND` 自动触发上锁。OFFBOARD 负责稳定的慢速下降到地面，触地后交给 AUTO.LAND 处理收尾。

```
OFFBOARD 下降段                          AUTO.LAND 收尾段
高空：0.20m/s 下降                       触地确认后 send_land()
低空：0.12m/s 接地                       PX4 着陆检测器触发
触地检测：高度≤0.18m + 1.0s              COM_DISARM_LAND=1.0s → 自动上锁 ✅
```

### 改动

只改 `_disarm_after_touchdown()` 一处——从"等待 PX4 检测"改为"切入 AUTO.LAND"：

```python
def _disarm_after_touchdown(self, reason: str, rel_alt: float) -> None:
    print("{}完成，切入 AUTO.LAND 完成着陆上锁。".format(reason))
    self.t.send_land()

    # 等待自动上锁（COM_DISARM_LAND=1.0s + 着陆检测余量）
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        s = self.t.get_state()
        if not s.armed:
            print("已上锁，降落完成。")
            return
        time.sleep(sc.SETPOINT_DT)

    # 5s 超时降级
    print("AUTO.LAND 上锁超时，尝试直接 disarm...")
    for attempt in range(1, 4):
        ...
    raise FlyError(...)
```

### 安全性

| 风险 | 评估 |
|---|---|
| 飞机已触地，AUTO.LAND 会不会导致 MPC_LAND_SPEED=0.6 造成弹跳？ | 不会。飞机已在地面，速度参数影响的是下降过程，不影响地面行为 |
| AUTO.LAND 会不会重新起飞？ | 不会。AUTO.LAND 进入后检测到已近地，直接进入着陆检测 |
| send_land() 是否可用？ | 已在 mavros_transport.py 中实现，直接可用 |

### 涉及文件

| 文件 | 改动 |
|---|---|
| `03_SourceCode/flight_core/fly.py` | `_disarm_after_touchdown()` 从 8s 等待改为切入 AUTO.LAND |

---

## 修改前后行为对比

| 环节 | 修改前（8s 等待方案） | 修改后（AUTO.LAND 收尾） |
|---|---|---|
| 触地后做什么 | 继续发地面 setpoint 等 8s | 切 AUTO.LAND，交给 PX4 |
| 着陆检测 | OFFBOARD 下不触发 | AUTO 模式下正常触发 |
| disarm 方式 | 脚本调 MAVLink disarm（被拒） | COM_DISARM_LAND 自动上锁 |
| 预期等待时间 | 8s 超时 → 降级 → 抛异常 | ~2s（PX4 检测 + COM_DISARM_LAND） |
| 可靠性 | ❌ 从未成功 | ✅ PX4 官方流程 |

---

## 验证要点

1. 运行 `stage07/00_takeoff_hover_land.sh`，降落段日志应出现：
   - `"触地确认完成，切入 AUTO.LAND 完成着陆上锁。"`
   - `"已上锁，降落完成。"`（~2s 内出现）
   - 不应出现电机顶地导致的横向漂移

2. 若出现 `"AUTO.LAND 上锁超时"` 降级日志，说明 `send_land()` 模式切换有问题，需排查 MAVROS 服务状态。

3. 机载电脑端可观察模式切换：
   ```bash
   rostopic echo /mavros/state   # mode 应从 OFFBOARD 变为 AUTO.LAND
   ```
