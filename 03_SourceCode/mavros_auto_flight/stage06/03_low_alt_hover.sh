#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-0.8}"
HOVER_TIME="${HOVER_TIME:-8}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "03_低空悬停" "tasks/stage06/03_low_alt_hover.py" \
  --alt "$ALT" \
  --hover-time "$HOVER_TIME"
