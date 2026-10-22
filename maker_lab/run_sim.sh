#!/usr/bin/env bash
# run_sim.sh — self-installing launcher for the maker simulator
# usage: ./run_sim.sh            -> live paper mode (default on VPS)
#        ./run_sim.sh --replay book_data/2026-09-25.jsonl
set -e
cd "$(dirname "$0")"
python3 -c "import websockets" 2>/dev/null || pip install -q websockets
if [ "$1" = "--replay" ]; then
  shift
  exec python3 maker_sim.py --replay "$@"
fi
exec python3 maker_sim.py --live
