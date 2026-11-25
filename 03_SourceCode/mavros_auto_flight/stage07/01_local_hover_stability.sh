#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
HOVER_TIME="${HOVER_TIME:-20}"
DRIFT_PASS="${DRIFT_PASS:-0.20}"
DRIFT_WARN="${DRIFT_WARN:-0.30}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "07_01_定点悬停与局部坐标稳定性检查" "tasks/stage07/01_local_hover_stability.py" \
  --alt "$ALT" \
  --hover-time "$HOVER_TIME" \
  --drift-pass "$DRIFT_PASS" \
  --drift-warn "$DRIFT_WARN"
