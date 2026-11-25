# MAVLink Console 监听命令参考

> 用途：供项目成员快速查阅各 listener 命令的作用和判断方法。
> 使用场景：拆桨调试、起飞前检查、落地后复查。

---

## 1. 光流数据

```sh
listener vehicle_optical_flow 1
```

| 关键字段 | 正常值 | 异常值 |
|---|---|---|
| `pixel_flow[0]` | 前移时 < 0，后移时 > 0 | 始终为 0 |
| `pixel_flow[1]` | 右移时 < 0，左移时 > 0 | 始终为 0 |
| `quality` | > 80 | 0 或持续偏低 |
| `distance_m` | 与实际离地高度一致 | 0 或恒定不变 |

用途：确认 MTF-02 是否正在输出光流和测距数据。

---

## 2. 原始传感器光流（EKF2 实际读取源）

```sh
listener sensor_optical_flow 1
```

| 关键字段 | 正常值 | 异常值 |
|---|---|---|
| `pixel_flow` | 移动时有变化 | `[0, 0]` |
| `distance_available` | `True` | `False` |
| `delta_angle_available` | `True` | `False` |
| `distance_m` | 与实际高度一致 | 0.0 |

**重点**：EKF2 读的是这个 topic，不是 `vehicle_optical_flow`。如果这里数据为空，EKF2 永远不会融合光流。

用途：排查 MAVLink → uORB 链路是否断裂。

---

## 3. 距离传感器数据

```sh
listener distance_sensor 1
```

| 关键字段 | 正常值 | 异常值 |
|---|---|---|
| `current_distance` | 随高度变化 | 恒定不变 |
| `min_distance` | 0.02 | — |
| `max_distance` | 2.5 | — |

用途：确认测距仪数据稳定、量程正确。

---

## 4. EKF2 估计器状态

```sh
listener estimator_status_flags 2
```

| 标志位 | True 含义 | False 含义 |
|---|---|---|
| `cs_opt_flow` | 光流正在被 EKF2 融合 | 未融合 |
| `cs_rng_hgt` | 测距仪用于高度 | 未用于高度 |
| `cs_baro_hgt` | 气压计用于高度 | 未用于高度 |
| `cs_mag_hdg` | 磁航向可用 | 不可用 |
| `cs_in_air` | 检测到飞行 | 在地面 |
| `cs_vehicle_at_rest` | 检测到静止 | 运动中 |
| `cs_tilt_align` | 姿态对准完成 | 未完成 |
| `cs_yaw_align` | 航向对准完成 | 未完成 |
| `cs_inertial_dead_reckoning` | EKF 进入纯惯性推算（**失联**） | 正常状态 |
| `cs_gnd_effect` | 检测到地面效应 | — |

异常标志位：

| 标志位 | True 含义 |
|---|---|
| `fs_bad_optflow_x` | 光流 X 轴故障 |
| `fs_bad_optflow_y` | 光流 Y 轴故障 |
| `reject_optflow_x` | 光流 X 轴被拒 |
| `reject_optflow_y` | 光流 Y 轴被拒 |
| `fs_bad_hdg` | 航向异常 |

用途：综合判断 EKF2 状态和融合情况。

---

## 5. 本地位置估计

```sh
listener vehicle_local_position 1
```

| 关键字段 | 正常值 | 异常值 |
|---|---|---|
| `xy_valid` | `True` | `False` |
| `v_xy_valid` | `True` | `False` |
| `z_valid` | `True` | `False` |
| `v_z_valid` | `True` | `False` |
| `dead_reckoning` | `False` | `True`（纯推算，不可控）|
| `dist_bottom_valid` | `True` | `False` |
| `x, y` | 接近 0（静止时） | 持续增大或跳动 |
| `vx, vy` | 接近 0（静止时） | 非零（静止时估算错误）|
| `eph` | 越小越好 | 持续增长 |

用途：确认位置和速度估计是否有效。

---

## 6. 飞行模式状态

```sh
listener vehicle_status 5
```

用途：确认当前飞行模式（Stabilized / Altitude / Position）和导航状态。

---

## 7. 电池状态

```sh
listener battery_status 5
```

用途：确认电池电压、电流、剩余容量。

---

## 8. 查看参数当前值

```sh
param show <参数名>
```

示例：

```
param show EKF2_OF_QMIN
param show EKF2_OF_GYR_SRC
param show SENS_FLOW_ROT
param show MAV_1_MODE
```

用途：确认参数实际生效的值（不是 param 文件里的值）。

---

## 阶段验证建议

| 阶段 | 必查命令 |
|---|---|
| 装桨前 | `vehicle_optical_flow`, `distance_sensor`, `estimator_status_flags` |
| Stabilized 首飞 | `vehicle_status`, `battery_status` |
| Altitude 定高 | `vehicle_local_position`, `distance_sensor` |
| Position 悬停 | `estimator_status_flags`, `vehicle_local_position` |
