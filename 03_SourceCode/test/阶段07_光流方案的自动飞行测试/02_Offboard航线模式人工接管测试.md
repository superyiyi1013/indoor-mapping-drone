# 02_Offboard航线模式人工接管测试

## 目标
在进入自动航线前，先验证路线任务中的人工接管机制。验证脚本检测到飞控模式离开 OFFBOARD 后立即停止发送 setpoint，飞手能够接管并安全降落。本项必须早于单边航点、往返、矩形和圆形路线测试。

---

## 本项飞行程序

| 项目 | 内容 |
|---|---|
| 入口脚本 | `03_SourceCode/mavros_auto_flight/stage07/02_route_takeover_check.sh` |
| Python 任务 | `03_SourceCode/mavros_auto_flight/tasks/stage07/02_route_takeover_check.py` |
| 接管判断 | `/mavros/state.mode != OFFBOARD` |
| 超时兜底 | `TAKEOVER_TIMEOUT` 内未检测到接管则自动降落 |

---

## 前置条件

- 阶段 07-01 定点悬停与局部坐标稳定性检查已通过。
- 阶段 06 人工接管和自动降落兜底已通过。
- 遥控器模式开关可明确切出 OFFBOARD。
- 安全员到位，可随时接管。
- 场地前方至少留出 1.5 m 安全距离。

---

## 默认参数

| 脚本变量 | 默认值 | 说明 |
|---|---:|---|
| `ALT` | `1.0` | 起飞和航线高度，单位 m |
| `PRE_HOVER` | `5` | 起飞后预备悬停时间，单位 s |
| `FORWARD_DISTANCE` | `0.5` | 微小前向航点距离，单位 m |
| `FORWARD_SPEED` | `0.12` | 前向 setpoint 推进速度，单位 m/s |
| `TAKEOVER_TIMEOUT` | `15` | 等待人工接管时间，单位 s |

---

## 运行方式

```bash
cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight/stage07
bash 02_route_takeover_check.sh
```

---

## 现场步骤

1. 确认 07-01 已通过，遥控器模式开关能可靠切出 OFFBOARD。
2. 确认前方至少 1.5 m 空旷距离。
3. 运行本项一键脚本。
4. 脚本提示安全确认时输入 `Y`。
5. 脚本自动起飞到目标高度并预备悬停。
6. 脚本开始发送微小前向航点 setpoint，进入路线任务形态。
7. 飞手拨模式开关离开 OFFBOARD，观察脚本是否打印"已检测到人工接管"并停止 setpoint。
8. 接管后飞手手动控制并安全降落。
9. 若超时未接管，脚本自动降落兜底。
10. 任意异常立即遥控器切出 OFFBOARD 或 QGC Land。

---

## 脚本输出日志

脚本运行结束后会自动打印结果，将终端输出粘贴至此处即可：

```


```



**接管方式：** □ 模式开关 / □ 摇杆 / □ QGC

**确认人/日期：**
