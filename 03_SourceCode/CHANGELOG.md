# Changelog

> 记录 `03_SourceCode/` 的变更历史。**Windows 开发侧 🪟 与机载电脑侧 🚁 各维护自己的条目，只追加不修改，避免冲突。**

---
## 2026-07-08

### 🪟 Windows
- 验证 `OBSTACLE_DISTANCE` 与 `distance_sensor` 数据输出（NSH 终端记录）：
  - `obstacle_distance`：前向视场桶（约索引 28~44）填入 `66cm`，其余方向填 `65535`（无障碍物）
  - `distance_sensor` Instance 0 → `orientation=25`（下视），`current_distance=0.17m`
  - `distance_sensor` Instance 1 → `orientation=0`（前向），`current_distance=0.66m`

  ```bash
  nsh> listener obstacle_distance 1

  TOPIC: obstacle_distance
   obstacle_distance
      increment: 5.00000
      angle_offset: -180.00000
      distances: [65535, ..., 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 65535, ...]
      min_distance: 10
      max_distance: 1000
      frame: 12
      sensor_type: 0

  nsh> listener distance_sensor 5

  TOPIC: distance_sensor 2 instances

  Instance 0:  # 下视（光流/声呐）
   distance_sensor
      device_id: 9699598 (Type: 0x94, MAVLINK:1 (0x01))
      min_distance: 0.02000
      max_distance: 2.50000
      current_distance: 0.17000
      orientation: 25

  Instance 1:  # 前向（D435i）
   distance_sensor
      device_id: 9699606 (Type: 0x94, MAVLINK:2 (0x01))
      min_distance: 0.10000
      max_distance: 10.00000
      current_distance: 0.66000
      h_fov: 1.51844
      v_fov: 0.95661
      orientation: 0
  ```

---

## 2026-07-03

### 🚁 机载电脑
- 排查阶段05 PX4 避障链路验收不通过问题：
  - `px4-perception.service`、MAVROS 串口连接、D435i 深度输出和 `/x400/obstacle/front_distance` 均正常。
  - 故障点定位为 MAVROS `distance_sensor` 输入未被 `/mavros` 订阅，导致阶段05订阅检查失败。
  - 发现 D435i 从 `id=42` 改为 `id=1` 后与 MAVROS 默认 `lidarlite_pub id=1` 存在混淆风险，QGC Inspector 容易误判前向传感器。
  - 发现 MAVROS 1.20 对自定义 `d435i_front_sub` 未建立 subscriber；改用 MAVROS 默认可订阅的 `/mavros/distance_sensor/laser_1_sub` 作为 D435i 前向 Range 输入。
  - 发现 `orientation: ROTATION_NONE` 不会触发 MAVROS 建立订阅；改为 MAVROS 可识别的 `orientation: NONE`，QGC 中对应 `orientation=0`。
- 修复自启动脚本 `bootstrap_sensing_stack.sh`：
  - systemd 重启服务时，`set -u` 会导致 ROS 环境脚本因 `ROS_MASTER_URI` 未设置而退出。
  - 增加默认 `ROS_MASTER_URI=http://localhost:11311` 和 `ROS_HOSTNAME=$(hostname)` 并导出，保证服务可冷启动/重启。
- 更新 MAVROS D435i 前向测距配置：
  - `/mavros/distance_sensor/laser_1_sub`
  - `id: 42`
  - `orientation: NONE`
  - `subscriber: true`
- 更新阶段05/阶段06文档与阶段06预检脚本：
  - 检查话题统一为 `/mavros/distance_sensor/laser_1_sub`。
  - QGC Inspector 统一查看 `DISTANCE_SENSOR id=42 / orientation=0`。
  - 阶段06飞行前预检同步检查 `/mavros` 对该话题的订阅关系。
- 阶段05复测结果：
  - `px4-perception.service`: `active`
  - `/mavros/state`: `connected: True`
  - `/x400/obstacle/front_distance`: 有 `Range` 数据
  - `/mavros/distance_sensor/laser_1_sub`: 有 `Range` 数据
  - `/mavros` 已订阅 `/mavros/distance_sensor/laser_1_sub`
  - `/mavlink/from` 可见 MAVLink `DISTANCE_SENSOR` 消息 `msgid=132`
- 排查阶段06 Position 模式日志 `[CollisionPrevention] No obstacle data, not moving...`：
  - 确认 `DISTANCE_SENSOR` 只满足 QGC 前向距离显示，不等同于 PX4 Collision Prevention 可用的 obstacle data。
  - 为 `front_obstacle_distance_node.py` 增加 `/mavros/obstacle/send` 的 `sensor_msgs/LaserScan` 输出，由 MAVROS obstacle 插件转换为 `OBSTACLE_DISTANCE`。
  - LaserScan 使用 360 度 72 桶格式，仅前向 D435i 视场内填入距离，其余方向填 `inf`。
  - MAVROS obstacle 插件显式配置 `obstacle/mav_frame=BODY_FRD`，避免默认 `GLOBAL` frame 不能作为机体系前向障碍数据使用。
  - 阶段06预检脚本新增 `/mavros/obstacle/send` 发布者和 `/mavros` 订阅关系检查。


“只读排查完成，结论如下。

**A. component 240 / sensor id 42 来源**

`component 240 / sensor id 42` 是 MAVROS 发送出来的前向 D435i `DISTANCE_SENSOR`。

ROS 侧证据：

```text
/mavros/distance_sensor/laser_1_sub
Publishers:
 * /front_obstacle_distance

Subscribers:
 * /mavros

hz: ~15Hz
range: 1.68m
```

参数证据：

```yaml
/mavros/distance_sensor/laser_1_sub:
  id: 42
  orientation: NONE
  subscriber: true
```

所以链路是：

```text
/front_obstacle_distance
  -> /mavros/distance_sensor/laser_1_sub
  -> /mavros
  -> MAVLink DISTANCE_SENSOR component 240, id 42, orientation 0
```

**B. component 1 / sensor id 1 来源**

`component 1 / sensor id 1` 是飞控 PX4 自己发回来的，不是当前 ROS 节点直接发布的。

解码 `/mavlink/from` 得到：

```text
sysid=1 compid=1 sensor_id=1 orientation=0 count=4 hz=0.50
sample current=168cm min=9cm max=1000cm
```

ROS 侧没有对应的高频发布者：

```text
/mavros/distance_sensor/lidarlite_pub
Publishers:
 * /mavros
Subscribers: None
hz: no new messages
```

因此它不是 `/front_obstacle_distance` 直接发的，也不是当前 `/mavros/distance_sensor/laser_1_sub`。它更像是 PX4 在接收到前向距离后，通过自身 component 1 低频重新发布/转发出来的 `DISTANCE_SENSOR`。因为它的距离值和 D435i 当前 168cm 一致。

**C. /mavros/obstacle/send 是否使用 id42 对应 D435i 数据**

是。同一个 ROS 节点 `/front_obstacle_distance` 同时发布：

```text
/mavros/distance_sensor/laser_1_sub
/mavros/obstacle/send
/x400/obstacle/front_distance
```

`/mavros/obstacle/send` 样例：

```text
Publishers:
 * /front_obstacle_distance
Subscribers:
 * /mavros

hz: ~15Hz
ranges 前向桶: 1.686m
```

所以它不携带 sensor id 42 这个字段，但数据源和 `component 240 / id42` 是同一个 D435i 前向距离节点。

**D. PX4 obstacle_distance 前方扇区是否来自 168cm**

是。解码 `OBSTACLE_DISTANCE msgid=330`：

```text
counts {(1, 1): 8}
frame: 12   # BODY_FRD
increment_f: 5.0
finite bins: 0-9, 63-71
distance: 166-168cm
```

这说明 PX4 回传的 `OBSTACLE_DISTANCE` 前向扇区已经是 166-168cm，和 D435i 当前距离一致。

**E. 旧 sensor id 1 是否干扰 CP**

目前看，它主要是 QGC 显示上的低频残留/转发项，不是当前 ROS 主链路。

当前 CP 更应该认定的链路是：

```text
D435i -> /mavros/obstacle/send -> MAVROS obstacle plugin -> OBSTACLE_DISTANCE frame BODY_FRD
```

`component 1 / id1` 可能造成测试记录混乱，因为它也是 `orientation=0`、距离也类似，但频率低、来源是 PX4 回传，不是机载电脑主发布。建议后续清理或至少在测试文档里明确忽略它。

当前判断：

```text
主前向 D435i: component 240 / sensor id 42 / orientation 0
下视高度: component 97 / sensor id 0 / orientation 25
旧/回传前向: component 1 / sensor id 1 / orientation 0，低频，建议后续清理
```

对于 Collision Prevention，重点看 `OBSTACLE_DISTANCE` 是否存在、frame 是否为 `BODY_FRD`、前向扇区是否是 D435i 距离。当前这部分是对的。”
---

## 2026-07-02

### 🚁 机载电脑
- 初始化项目

### 🪟 Windows
- 初始化项目

---

> 查看详细提交记录：`git log --oneline -10`
