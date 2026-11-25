# ROS 现场速查卡

## 1. 进入工作区

```bash
cd ~/ros_catkin_ws_lite
```

> 如果机载电脑上还没有这个目录，先把电脑上 `03_SourceCode/ros_catkin_ws_lite` 整个拷过去。

---

## 2. 编译（仅首次 / 改代码后需要）

```bash
cd ~/ros_catkin_ws_lite
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash
```

看到末尾没有报错就过了。

检查编译是否成功：

```bash
rospack find x400_bringup
```

应该返回路径，而不是报错。

---

## 3. 跑起来（三种场景，按需选一个）

### 场景 A：只测 Pixhawk 连接（测串口通不通）

```bash
cd ~/ros_catkin_ws_lite
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch x400_bringup mavros_px4_t3.launch fcu_url:=/dev/ttyTHS0:921600 gcs_url:=udp-b://@14550
```

新终端检查：

```bash
rostopic echo /mavros/state
```

看到 `connected: True` 即成功。

### 场景 B：只测 D435i 深度相机（测摄像头是否正常）

```bash
cd ~/ros_catkin_ws_lite
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch x400_bringup d435i_front_distance.launch
```

新终端检查：

```bash
rostopic hz /camera/depth/image_rect_raw
```

能看到频率（如 15 Hz）即成功。

### 场景 C：完整启动（MAVROS + D435i + 避障）

```bash
cd ~/ros_catkin_ws_lite
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch x400_bringup onboard_sensing_stack.launch fcu_url:=/dev/ttyTHS0:921600
```

检查三项：

```bash
rostopic echo /mavros/state        # connected: True
rostopic hz /camera/depth/image_rect_raw   # 有频率
rostopic echo /x400/obstacle/front_distance  # 距离会变化
```

---

## 4. 每次开机的标准三步

```bash
cd ~/ros_catkin_ws_lite
source /opt/ros/noetic/setup.bash
source devel/setup.bash
```

然后选上面场景 A/B/C 中的一个启动即可。

---

## 5. 常见问题一句话解决

| 问题 | 解决 |
|---|---|
| `rospack find` 找不到 | 没 `source devel/setup.bash` |
| `connected: False` | 检查串口线 TX/RX 是否交叉、GND 是否共地 |
| D435i 无图 | 插 USB3 口；`rs-enumerate-devices` 看设备是否存在 |
| 串口名不对 | `ls /dev/ttyTHS*` 查看实际设备名 |
