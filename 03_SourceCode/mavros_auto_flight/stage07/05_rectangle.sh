#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
ALT_TOLERANCE="${ALT_TOLERANCE:-0.1}"
PRE_HOVER="${PRE_HOVER:-5}"
RECT_SIZE="${RECT_SIZE:-1.0}"
WAYPOINT_SPEED="${WAYPOINT_SPEED:-0.15}"
WAYPOINT_TOLERANCE="${WAYPOINT_TOLERANCE:-0.15}"
CORNER_HOVER="${CORNER_HOVER:-2}"
RETURN_HOVER="${RETURN_HOVER:-3}"
CLOSE_TOLERANCE="${CLOSE_TOLERANCE:-0.15}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "07_05_小矩形航线飞行测试" "tasks/stage07/05_rectangle.py" \
  --alt "$ALT" \
  --alt-tolerance "$ALT_TOLERANCE" \
  --pre-hover "$PRE_HOVER" \
  --rect-size "$RECT_SIZE" \
  --waypoint-speed "$WAYPOINT_SPEED" \
  --waypoint-tolerance "$WAYPOINT_TOLERANCE" \
  --corner-hover "$CORNER_HOVER" \
  --return-hover "$RETURN_HOVER" \
  --close-tolerance "$CLOSE_TOLERANCE"
