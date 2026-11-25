#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-0.8}"
FORWARD_DISTANCE="${FORWARD_DISTANCE:-0.5}"
FORWARD_SPEED="${FORWARD_SPEED:-0.12}"
OBSTACLE_STOP_DISTANCE="${OBSTACLE_STOP_DISTANCE:-1.0}"
HOVER_TIME="${HOVER_TIME:-6}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "05_障碍停止" "tasks/stage06/05_obstacle_stop.py" \
  --alt "$ALT" \
  --forward-distance "$FORWARD_DISTANCE" \
  --forward-speed "$FORWARD_SPEED" \
  --obstacle-stop-distance "$OBSTACLE_STOP_DISTANCE" \
  --hover-time "$HOVER_TIME"
