#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WS_DIR="$(cd "$SCRIPT_DIR/../../ros_catkin_ws_lite" && pwd)"

WS_DIR="${WS_DIR:-$DEFAULT_WS_DIR}"
DISTANCE_TOPIC="${DISTANCE_TOPIC:-/x400/obstacle/front_distance}"
MAVROS_DISTANCE_TOPIC="${MAVROS_DISTANCE_TOPIC:-/mavros/distance_sensor/laser_1_sub}"

source /opt/ros/noetic/setup.bash
if [[ ! -f "$WS_DIR/devel/setup.bash" ]]; then
  echo "未找到 $WS_DIR/devel/setup.bash，请先编译工作区。" >&2
  exit 1
fi
source "$WS_DIR/devel/setup.bash"

source "$SCRIPT_DIR/../common/preflight_stack_check.sh"
check_flight_stack_ready

echo
echo "阶段06-02：Position 模式前向手动避障辅助检查"
echo "本脚本不解锁、不切模式、不发送飞行指令。"
echo "请由飞手在 QGC/遥控器中完成起飞、Position 模式和手动前推测试。"
echo
echo "QGC MAVLink Inspector 观察目标："
echo "  - 消息：DISTANCE_SENSOR"
echo "  - 前向 D435i：orientation=0"
echo "  - 光流/下视测距通常：orientation=25"
echo
echo "现在持续显示 D435i 前向距离。确认完成后按 Ctrl+C 退出。"

read_range_once() {
  rostopic echo -n 1 "$DISTANCE_TOPIC" 2>/dev/null \
    | awk '/^[[:space:]]*range:/ { print $2; exit }'
}

while true; do
  range="$(read_range_once || true)"
  if [[ -n "$range" ]]; then
    printf '[%s] D435i 前向距离：%s m\n' "$(date +%H:%M:%S)" "$range"
  else
    printf '[%s] 未收到 D435i 前向距离\n' "$(date +%H:%M:%S)"
  fi
  sleep 1
done
