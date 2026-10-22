#!/usr/bin/env bash
# history-refresh.sh — daily history corpus maintenance (cron: 10 0 * * *)
# 1) rewrites the rolling 7-day FULL-PRECISION price corpus (past-results keeps ~1 week only)
# 2) incrementally extends the deep OUTCOME corpora back to series start
# Safe to re-run any time; gamma deep step resumes from the newest stored round.
set -euo pipefail
cd "$(dirname "$0")/.."    # /opt/maker_lab when deployed per MASTER-RUNBOOK

echo "[$(date -u +%FT%TZ)] history refresh start"

# rolling 7-day price corpus (both variants)
python3 history_backfill.py --symbol BTC --variant fiveminute --days 7
python3 history_backfill.py --symbol BTC --variant fifteen  --days 7

# deep outcome corpora (incremental; refetches last ~1 day and merges)
python3 history_backfill_gamma.py --symbol BTC --variant fiveminute --incremental
python3 history_backfill_gamma.py --symbol BTC --variant fifteen  --incremental

# OPTIONAL: keep the chain-verified labels fresh for yesterday's new rounds.
# Cheap (~900 rounds) — uncomment after the one-time full relabel has run once:
# python3 chain_relabel.py --csv history/BTC_fiveminute_long.csv --workers 2
# python3 chain_relabel.py --csv history/BTC_fifteen_long.csv  --workers 2

echo "[$(date -u +%FT%TZ)] history refresh done"
