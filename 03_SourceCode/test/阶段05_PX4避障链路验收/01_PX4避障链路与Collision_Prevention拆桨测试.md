# 01_PX4避障链路与Collision Prevention 自启动链路验收

## 目标

验收机载电脑开机自启动避障链路，确认：

1. systemd 已自动启动 `bootstrap_sensing_stack.sh`。
2. MAVROS 已连接 Pixhawk。
3. D435i 前向距离可输出到 `/x400/obstacle/front_distance`。
4. 前向距离可同步到 `/mavros/distance_sensor/laser_1_sub`（`id=42`），并被 `/mavros` 订阅。
5. PX4/QGC 可见与 D435i 一致的前向 `DISTANCE_SENSOR`。

---

## 验收结果（2026-07-08）

### 1. systemd 自启动服务

```bash
systemctl list-units --type=service | grep -Ei 'x400|sensing|mavros|d435|ros'
systemctl status px4-perception.service --no-pager
```

- `px4-perception.service`：`loaded active running`
- 描述：`PX4 Perception Pipeline (MAVROS + D435i)`
- 主进程：`roslaunch x400_bringup onboard_sensing_stack.launch fcu_url:=/dev/ttyTHS0:921600 gcs_url:=udp-b://@14550 respawn_mavros:=true`

**判定：** 通过。

### 2. MAVROS 连接状态

```text
connected: True   mode: "POSCTL"   system_status: 3
```

**判定：** 通过。

### 3. D435i 前向距离输出（`/x400/obstacle/front_distance`）

```text
frame_id: "d435i_front_link"   range: 0.663m   min_range: 0.1m   max_range: 10.0m
```

**判定：** 通过。

### 4. MAVROS distance_sensor 输入链路（`/mavros/distance_sensor/laser_1_sub`）

```text
frame_id: "d435i_front_link"   range: 0.662m   频率: ~15Hz
```

Publishers: `/front_obstacle_distance`。Subscribers: `/mavros`。

**判定：** 通过。D435i 前向距离已进入 MAVROS distance_sensor 输入链路（`sensor id=42`）。

### 5. MAVROS obstacle 输入链路（`/mavros/obstacle/send`）

- 前方扇区填入 `0.663m`，其余方向为 `inf`
- 频率：~15Hz

**判定：** 通过。Collision Prevention 使用的 `OBSTACLE_DISTANCE` 输入源具备稳定前向距离数据。

### 6. PX4/QGC 侧 DISTANCE_SENSOR 可见性

MAVLink 回传解析结果：

```text
sysid=1 compid=1 sensor_id=1 orientation=0   current=66cm   # 前向，与 D435i 一致
sysid=1 compid=97 sensor_id=0 orientation=25  current=18cm   # 下视光流，非前向
```

ROS 输入链路使用 `id=42`，PX4 接收后重新发布为 `component=1 / sensor id=1`。前向距离 `66cm` 与 ROS 侧 `0.662~0.663m` 一致。

**判定：** 通过。

### 7. 未完成项

- 未移动软障碍物进行动态变化验证。仅确认固定距离下数据稳定、链路一致。

---

## 结论

**阶段05结论：** ☑ 主链路通过

自启动链路正常，MAVROS 已连接（POSCTL），D435i 前向距离在 ROS 侧约 `0.66m / 15Hz`，MAVROS distance_sensor 和 obstacle 链路均已建立，PX4/QGC 可见一致的前向 `DISTANCE_SENSOR`（`66cm`）。

**确认人/日期：** Codex / 2026-07-08
