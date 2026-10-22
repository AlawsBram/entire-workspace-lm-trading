#!/usr/bin/env bash
# run_recorder.sh — self-installing launcher for the truth-feed divergence recorder
set -e
cd "$(dirname "$0")"
mkdir -p truth_data
python3 -c "import websockets" 2>/dev/null || pip install -q websockets
exec python3 truth_recorder.py
