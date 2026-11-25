# 01_Offboard低空悬停与人工接管测试

## 目标

Offboard 起飞至 1.0 m 后稳定悬停，验证摇杆 RC override 和模式开关兜底接管，接管后飞手人工控制并安全降落。

---

## 本项飞行程序

| 项目 | 内容 |
|---|---|
| 入口脚本 | `stage06/01_manual_takeover_first_check.sh` |
| Python 任务 | `tasks/stage06/01_hover_takeover.py` |
| 接管方式 | 摇杆 RC override / 模式开关切离 OFFBOARD |

---

## 前置条件

- 阶段 03/04/05 已通过。
- 机载电脑上电后自启动避障链路已常驻运行。
- 遥控器模式开关可切回 Stabilized / Altitude。
- 安全员到位，场地空旷。

---

## 默认参数

| 脚本变量 | 默认值 | 说明 |
|---|---|---|
| `ALT` | `1.0` | 起飞高度，单位 m |
| `HOVER_TIME` | `6` | 悬停时间，单位 s |
| `TAKEOVER_TIMEOUT` | `15` | 等待接管超时，单位 s |

---

## 运行方式

```bash
cd /home/<user>/X400_workspace/03_SourceCode/mavros_auto_flight/stage06
bash 01_manual_takeover_first_check.sh
```

---

## 现场步骤

1. 运行本项一键脚本。
2. 脚本提示安全确认时输入 `Y`。
3. 脚本自动 Offboard 解锁，起飞至 1.0 m 并悬停。
4. 脚本提示接管测试后，先明显打摇杆尝试 RC override，若未接管则拨模式开关切回 Stabilized / Altitude。
5. 确认 QGC 模式离开 OFFBOARD，脚本停止发送 setpoint。
6. 接管后飞手手动降落。
7. 任意异常立即遥控器接管或 QGC Land。

---

## 脚本输出日志

脚本运行结束后会自动打印结果，将终端输出粘贴至此处即可：

```


```
