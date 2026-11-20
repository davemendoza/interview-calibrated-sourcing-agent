#!/usr/bin/env bash
# Nightly run: harvest, score, and run the test gate if a test set exists.
# A failed gate exits non-zero so cron or launchd can alert you.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
echo "=== $(date '+%Y-%m-%d %H:%M') ==="
icsa run "$@"
