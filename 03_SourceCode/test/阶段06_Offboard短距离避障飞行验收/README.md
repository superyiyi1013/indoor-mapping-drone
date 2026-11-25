# 阶段06 — Offboard短距离避障飞行验收

## 阶段目标

验证机载电脑在自启动避障链路常驻运行的前提下，可通过 MAVROS 执行低空、低速、短距离 Offboard 飞行，并在前方障碍出现时停止或悬停。

本阶段是上桨自动飞行阶段，必须严格按顺序执行，禁止跳项。

---

## 测试顺序

| # | 文档 | 内容 |
|---|---|---|
| 1 | 01_Offboard低空悬停与人工接管测试 | Offboard 起飞悬停 + 摇杆/模式开关接管验证 |
| 2 | 02_Position模式前向手动避障测试 | Position 模式下手动验证 PX4 CP 前向障碍限制 |
| 3 | 03_Offboard短距离前进与地面站前向距离观察测试 | Offboard 前进 1 m，观察 QGC 前向距离 |
| 4 | 04_Offboard前方障碍停止或悬停测试 | 软障碍触发停止/悬停 |
| 5 | 05_1m起飞等待接管超时降落测试 | 起飞到 1 m，20 s 未接管自动降落 |

---

## 运行方式

```bash
cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight/stage06
bash 01_manual_takeover_first_check.sh
bash 02_position_manual_cp_check.sh
bash 03_low_alt_hover.sh
bash 04_short_forward.sh
bash 05_obstacle_stop.sh
bash 06_takeoff_1m_takeover_or_autoland.sh
```

脚本会自动检查 MAVROS、D435i 前向距离链路是否就绪，检查不通过时拒绝进入飞行任务。

---

## 新电脑更换后的自启动链路配置

阶段 06 默认前提是：机载电脑上电后，`MAVROS + D435i 前向距离 + MAVROS obstacle/distance_sensor` 已由 `systemd` 自动拉起并常驻运行。新电脑替换后，至少要把这条链路重新配置一遍。

### 1. 确认基础前提

- ROS Noetic 已安装。
- 工作区已存在并成功编译：`/home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite`
- 飞控串口仍为 `/dev/ttyTHS0`，波特率仍为 `921600`
- 当前用户可访问串口，通常需要在 `dialout` 组

复核命令：

```bash
ls -l /dev/ttyTHS0
groups
```

### 2. 确认自启动入口脚本

本项目当前的自启动入口脚本是：

```bash
/home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite/src/x400_bringup/scripts/bootstrap_sensing_stack.sh
```

它实际启动的是：

```bash
roslaunch x400_bringup onboard_sensing_stack.launch \
  fcu_url:=/dev/ttyTHS0:921600 \
  gcs_url:=udp-b://@14550 \
  respawn_mavros:=true
```

### 3. 新建 systemd 服务

在新电脑上创建 `/etc/systemd/system/px4-perception.service`：

```ini
[Unit]
Description=PX4 Perception Pipeline (MAVROS + D435i)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<user>
WorkingDirectory=/home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite
Environment=FCU_URL=/dev/ttyTHS0:921600
Environment=GCS_URL=udp-b://@14550
ExecStart=/home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite/src/x400_bringup/scripts/bootstrap_sensing_stack.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

写入后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable px4-perception.service
sudo systemctl start px4-perception.service
```

### 4. 检查服务是否已正常拉起

```bash
systemctl status px4-perception.service --no-pager
systemctl list-units --type=service | grep -Ei 'px4-perception|mavros|ros'
```

通过标准：

- `px4-perception.service` 状态为 `loaded active running`
- 主进程已执行 `bootstrap_sensing_stack.sh`

### 5. 检查 ROS / MAVROS / 避障链路

```bash
source /opt/ros/noetic/setup.bash
source /home/<user>/X400_workspace/03_SourceCode/ros_catkin_ws_lite/devel/setup.bash
rostopic echo -n 1 /mavros/state
rostopic echo -n 1 /mavros/local_position/pose
rostopic echo -n 1 /x400/obstacle/front_distance
rostopic hz /mavros/distance_sensor/laser_1_sub
```

通过标准：

- `/mavros/state` 中 `connected: True`
- `/mavros/local_position/pose` 有连续位置数据
- `/x400/obstacle/front_distance` 有实时前向距离
- `/mavros/distance_sensor/laser_1_sub` 有稳定频率输出

### 6. 常见更换电脑后问题

- `Unable to communicate with master!`
  说明 `roscore` / `roslaunch` 没被 `systemd` 拉起，先看 `systemctl status px4-perception.service`
- `serial0: device: /dev/ttyTHS0 @ 921600 bps` 有日志，但 `/mavros/state` 仍不连通
  先检查 Pixhawk 是否上电、T3/TELEM3 接线和 GND 共地是否正确
- 能看到 `/dev/ttyTHS0`，但服务起不来
  常见原因是当前用户不在 `dialout` 组，或工作区没有重新编译

---

## 准入规则

- 阶段 03 未通过，禁止阶段 06。
- 阶段 04 未通过，禁止阶段 06 避障测试。
- 阶段 05 自启动避障链路未通过，禁止阶段 06 飞行。
- 01 人工接管测试未通过，禁止任何后续自动飞行。

---

## 退出条件

全部 5 项测试均通过后，阶段 06 判定通过。任意一项未通过，记录问题，修复后从该项重新执行。
