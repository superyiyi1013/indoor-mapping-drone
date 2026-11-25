#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
PRE_HOVER="${PRE_HOVER:-5}"
FORWARD_DISTANCE="${FORWARD_DISTANCE:-1.0}"
FORWARD_SPEED="${FORWARD_SPEED:-0.12}"
WAYPOINT_TOLERANCE="${WAYPOINT_TOLERANCE:-0.15}"
WAYPOINT_HOVER="${WAYPOINT_HOVER:-5}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "07_03_单边短距离航点飞行测试" "tasks/stage07/03_single_waypoint.py" \
  --alt "$ALT" \
  --pre-hover "$PRE_HOVER" \
  --forward-distance "$FORWARD_DISTANCE" \
  --forward-speed "$FORWARD_SPEED" \
  --waypoint-tolerance "$WAYPOINT_TOLERANCE" \
  --waypoint-hover "$WAYPOINT_HOVER"
