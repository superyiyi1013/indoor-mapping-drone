#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
HOVER_TIME="${HOVER_TIME:-10}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "07_00_起飞降落稳定性循环测试" "tasks/stage07/00_takeoff_hover_land.py" \
  --alt "$ALT" \
  --hover-time "$HOVER_TIME"
