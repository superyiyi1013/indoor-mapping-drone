#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-0.8}"
FORWARD_DISTANCE="${FORWARD_DISTANCE:-1.0}"
FORWARD_SPEED="${FORWARD_SPEED:-0.15}"
HOVER_TIME="${HOVER_TIME:-6}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "04_短距离前进" "tasks/stage06/04_short_forward.py" \
  --alt "$ALT" \
  --forward-distance "$FORWARD_DISTANCE" \
  --forward-speed "$FORWARD_SPEED" \
  --hover-time "$HOVER_TIME"
