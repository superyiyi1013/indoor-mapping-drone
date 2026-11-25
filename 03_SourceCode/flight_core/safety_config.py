"""
全局安全常量与飞行参数。

所有安全边界统一管理，Fly 层和各 Task 共用。
现场可根据场地/载重通过环境变量或构造函数覆盖。
"""

# ── 起飞与爬升 ──────────────────────────────────────────
GROUND_BASELINE_DURATION_S = 2.5   # 起飞前地面高度基准采样时长
LIFTOFF_TARGET_ALT_M = 0.70        # 起跳台阶目标高度，先明确离地再爬升
LIFTOFF_DETECTED_ALT_M = 0.40      # 确认为"已离地"的本次地面基准高度差
LIFTOFF_HOLD_AFTER_DETECTED_S = 0.15  # 离地后短时保持（~2 周期），防止检测抖动
LIFTOFF_STALL_TIMEOUT_S = 3.0      # 起跳段高度停滞超时（连续不增长则判定失败）
LIFTOFF_TOTAL_TIMEOUT_S = 12.0     # 起跳段总超时硬上限
LIFTOFF_PROGRESS_THRESHOLD_M = 0.01  # 起跳段高度增长判定阈值（>此值视为有进步）
CLIMB_RATE_MPS = 0.30              # 爬升速率，兼顾果断起飞和室内安全余量
CLIMB_TIMEOUT_S = 20.0             # 爬升超时

# ── 高度限幅 ─────────────────────────────────────────────
MAX_SAFE_ALT_M = 2.0               # 绝对安全上限（超过则中止）

# ── 水平运动 ─────────────────────────────────────────────
MAX_FORWARD_DISTANCE_M = 2.0       # 单次前进最大距离
MAX_FORWARD_SPEED_MPS = 0.5        # 前进最大速率
DEFAULT_FORWARD_SPEED_MPS = 0.15   # 前进默认速率

# ── 降落 ─────────────────────────────────────────────────
DESCEND_RATE_MPS = 0.20            # 下降速率（Offboard 全程控制）
LAND_FINAL_ALT_M = 0.30            # 低于该高度后锁定当前 XY，避免贴地继续追 home
LAND_FINAL_DESCEND_RATE_MPS = 0.12 # 末端下降速率，降低触地弹跳和横向滑移
TOUCHDOWN_BOTTOM_HOLD_S = 1.0      # 下降目标到底后的触地确认等待时间
TOUCHDOWN_BOTTOM_ALT_M = 0.18      # 下降目标到底后允许上锁的最大相对高度
DESCENT_TIMEOUT_S = 25.0           # 下降超时
LAND_DISARM_WAIT_S = 5.0           # 切 AUTO.LAND 后等待自动上锁的超时时间
DISARM_RETRY_COUNT = 3             # 触地后标准上锁重试次数
DISARM_RECHECK_DELAY_S = 0.5       # 每次上锁后复核 armed 状态前的等待时间

# ── Offboard 通信 ────────────────────────────────────────
SETPOINT_HZ = 10.0                 # setpoint 发布频率
SETPOINT_DT = 1.0 / SETPOINT_HZ
PRESEND_OFFBOARD_DURATION_S = 2.0  # 切 Offboard 前预发 setpoint 时长
READY_TIMEOUT_S = 30.0             # 等待链路就绪超时

# ── 悬停 ─────────────────────────────────────────────────
DEFAULT_HOVER_TIME_S = 6.0         # 默认悬停时长
DEFAULT_TARGET_ALT_M = 1.0         # 默认目标高度

# ── 偏航控制 ─────────────────────────────────────────────
YAW_TOLERANCE_DEG = 5.0             # 偏航到位容差（度）
YAW_TIMEOUT_S = 6.0                 # 偏航旋转超时

# ── 避障 ─────────────────────────────────────────────────
DEFAULT_OBSTACLE_STOP_DISTANCE_M = 1.0   # 默认障碍停止距离
DEFAULT_FRONT_DISTANCE_TOPIC = "/x400/obstacle/front_distance"
