#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
PRE_HOVER="${PRE_HOVER:-5}"
FORWARD_DISTANCE="${FORWARD_DISTANCE:-0.5}"
FORWARD_SPEED="${FORWARD_SPEED:-0.12}"
TAKEOVER_TIMEOUT="${TAKEOVER_TIMEOUT:-15}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "07_02_Offboard航线模式人工接管测试" "tasks/stage07/02_route_takeover_check.py" \
  --alt "$ALT" \
  --pre-hover "$PRE_HOVER" \
  --forward-distance "$FORWARD_DISTANCE" \
  --forward-speed "$FORWARD_SPEED" \
  --takeover-timeout "$TAKEOVER_TIMEOUT"
