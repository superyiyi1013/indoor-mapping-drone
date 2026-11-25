#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-0.8}"
OVER_SIZE_DIST="${OVER_SIZE_DIST:-3.0}"
VALID_DIST="${VALID_DIST:-0.5}"
FENCE_SPEED="${FENCE_SPEED:-0.15}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "07_06_安全围栏验证测试" "tasks/stage07/06_fence_check.py" \
  --alt "$ALT" \
  --oversize-dist "$OVER_SIZE_DIST" \
  --valid-dist "$VALID_DIST" \
  --fence-speed "$FENCE_SPEED"
