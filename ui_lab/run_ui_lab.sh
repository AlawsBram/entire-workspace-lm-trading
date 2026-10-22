#!/usr/bin/env bash
# run_ui_lab.sh — self-installing launcher: one full 5m round per cycle, forever.
set -e
cd "$(dirname "$0")"
python3 -c "import websockets" 2>/dev/null || pip install -q websockets
python3 -c "import playwright" 2>/dev/null || pip install -q playwright
python3 -c "
from playwright.sync_api import sync_playwright
" 2>/dev/null && python3 - <<'EOF' 2>/dev/null || python3 -m playwright install --with-deps chromium
import glob, os
assert glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium*")), "no browser"
EOF
while true; do
  python3 ui_api_comparator.py || echo "cycle failed; retry next bell"
done
