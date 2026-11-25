#!/usr/bin/env bash
# 开机自启脚本：启动 MAVROS + D435i 前向感知链路
# 配合 systemd 使用，实现开机自动运行 + 崩溃自动重启
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOG_DIR="${LOG_DIR:-$WS_DIR/../logs}"
FCU_URL="${FCU_URL:-/dev/ttyTHS0:921600}"
GCS_URL="${GCS_URL:-udp-b://@14550}"
ROS_MASTER_URI="${ROS_MASTER_URI:-http://localhost:11311}"
ROS_HOSTNAME="${ROS_HOSTNAME:-$(hostname)}"

export ROS_MASTER_URI ROS_HOSTNAME
export ROS_DISTRO=noetic

mkdir -p "$LOG_DIR"

source /opt/ros/noetic/setup.bash
source "$WS_DIR/devel/setup.bash"

exec roslaunch x400_bringup onboard_sensing_stack.launch \
  fcu_url:="$FCU_URL" \
  gcs_url:="$GCS_URL" \
  respawn_mavros:=true \
  > "$LOG_DIR/sensing_stack.log" 2>&1
