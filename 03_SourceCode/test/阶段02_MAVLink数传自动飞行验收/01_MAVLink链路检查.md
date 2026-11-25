# 01_MAVLink链路检查

## 目标

确认地面电脑可通过 LQ 数传与 Pixhawk 建立 MAVLink 通信。

## 前置条件

- 阶段01 基础飞行基线验收通过。
- QGC 关闭或不占用脚本端口。

## 测试步骤

| 操作 | 通过标准 |
|---|---|
| 检查地面电脑网络 | IP 与数传链路匹配 |
| ping 数传地面端 | 能连通 |
| 运行链路检查脚本 | 能收到 Pixhawk 心跳 |
| 查看 QGC 备份链路 | QGC 可重新连接查看状态 |

## 命令

```powershell
ping 192.168.1.200
.\.venv\Scripts\python.exe .\03_SourceCode\mavlink_auto_flight\link_check.py
```

## 通过条件

- 脚本能收到飞控心跳。
- 链路稳定。
- QGC 可作为监控/备份链路使用。

## 结论

状态：✅ 通过  
问题：无  
确认：AI 自动记录 / 2026-06-11
