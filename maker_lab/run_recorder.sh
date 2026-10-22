#!/usr/bin/env bash
# run_recorder.sh — self-installing launcher for the book recorder
set -e
cd "$(dirname "$0")"
python3 -c "import websockets" 2>/dev/null || pip install -q websockets
exec python3 book_recorder.py
