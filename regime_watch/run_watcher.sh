#!/usr/bin/env bash
# run_watcher.sh — self-installing launcher for the regime-change sentinel.
# Stdlib-only (urllib), so no pip needed; installs nothing.
set -e
cd "$(dirname "$0")"
exec python3 regime_watch.py "$@"
