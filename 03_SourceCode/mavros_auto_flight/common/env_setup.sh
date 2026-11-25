#!/usr/bin/env bash
# 飞行脚本公共环境设定。
# 所有 stage*_*.sh 入口脚本先 source 本文件，再调用 run_flight_task。
#
# 本文件位于 mavros_auto_flight/common/。
# 相对路径约定：
#   common/..                     = mavros_auto_flight 根目录
#   common/../..                  = 03_SourceCode 根目录
#   ../../ros_catkin_ws_lite       = ROS 工作区
#   ../../flight_core              = 飞行核心包
#
# 使用方法：
#   source "$(dirname "${BASH_SOURCE[0]}")/common/env_setup.sh"
#   run_flight_task "01_task_name" "tasks/task.py" \
#       --alt "$ALT" --hover-time "$HOVER_TIME"
#
# 环境变量覆盖：
#   WS_DIR=/路径           → ROS 工作区路径
#   FLIGHT_CORE_DIR=/路径  → flight_core 路径

set -euo pipefail

# ── 路径推导 ──────────────────────────────────────────────
# SCRIPT_DIR = mavros_auto_flight/common/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# MAVROS_DIR = mavros_auto_flight/
MAVROS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# REPO_ROOT = 03_SourceCode/
REPO_ROOT="$(cd "$MAVROS_DIR/.." && pwd)"

# ── ROS 工作区 ────────────────────────────────────────────
DEFAULT_WS_DIR="$REPO_ROOT/ros_catkin_ws_lite"
WS_DIR="${WS_DIR:-$DEFAULT_WS_DIR}"

# ── 飞行核心包 ────────────────────────────────────────────
DEFAULT_FLIGHT_CORE_DIR="$REPO_ROOT/flight_core"
FLIGHT_CORE_DIR="${FLIGHT_CORE_DIR:-$DEFAULT_FLIGHT_CORE_DIR}"

# ── 加载 ROS 环境 ─────────────────────────────────────────
source /opt/ros/noetic/setup.bash
if [[ ! -f "$WS_DIR/devel/setup.bash" ]]; then
  echo "未找到 $WS_DIR/devel/setup.bash，请先编译工作区。" >&2
  exit 1
fi
source "$WS_DIR/devel/setup.bash"

# ── 飞行前链路检查 ────────────────────────────────────────
source "$SCRIPT_DIR/preflight_stack_check.sh"
check_flight_stack_ready

# ── 入口函数 ──────────────────────────────────────────────
run_flight_task() {
  local label="$1"
  local rel_script="$2"
  shift 2

  echo "— ${label}"
  echo "=========================================="

  export PYTHONPATH="$FLIGHT_CORE_DIR:${PYTHONPATH:-}"

  python3 "$MAVROS_DIR/$rel_script" "$@"
}
