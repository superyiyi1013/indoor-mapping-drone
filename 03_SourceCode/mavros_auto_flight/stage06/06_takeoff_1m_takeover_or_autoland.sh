#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALT="${ALT:-1.0}"
TAKEOVER_TIMEOUT="${TAKEOVER_TIMEOUT:-20}"

source "$SCRIPT_DIR/../common/env_setup.sh"
run_flight_task "06_1m起飞等待接管超时降落" "tasks/stage06/06_takeoff_1m_takeover_or_autoland.py" \
  --alt "$ALT" \
  --takeover-timeout "$TAKEOVER_TIMEOUT"
