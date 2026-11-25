#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
HOVER_TIME="${HOVER_TIME:-6}"
TAKEOVER_TIMEOUT="${TAKEOVER_TIMEOUT:-15}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "01_悬停人工接管" "tasks/stage06/01_hover_takeover.py" \
  --alt "$ALT" \
  --hover-time "$HOVER_TIME" \
  --takeover-timeout "$TAKEOVER_TIMEOUT"
