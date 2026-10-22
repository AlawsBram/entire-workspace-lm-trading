# Regime Watch — Polymarket rule-change sentinel

The venue edits its own physics (fees, tick size, taker delay, rewards,
settlement docs), sometimes without announcement. This daemon diffs every
structural parameter it can see and raises a loud alert the moment anything
changes — so you react before the PnL teaches you.

## What it watches
| source | what it catches |
|---|---|
| `docs-full` | ANY change to the entire docs site (plain-text mirror at `docs.polymarket.com/llms-full.txt`): fee structure, API changes, settlement mechanics, changelogs |
| `docs-toc` | pages added/removed |
| `sentinel-5m/15m/1h` | live BTC up/down rounds: feesEnabled, feeType, **feeSchedule**, maker/taker base fees, tick size, negRisk, rewards min size & max spread (Gamma) **plus CLOB physics: `seconds_delay` (the taker speed-bump!), minimum_order_size, minimum_tick_size, rewards rates** |
| `fee-rate-*` | the *effective* per-token fee straight from the CLOB `/fee-rate` endpoint (what the docs tell you not to hardcode) |

Non-existent labels (e.g. `60m` vs `1h`) auto-disable after 8 tries.

## Deploy on your VPS
```bash
sudo mkdir -p /opt/regime_watch && sudo tar xzf regime_watch.tar.gz -C /opt/regime_watch --strip-components=1
cd /opt/regime_watch
python3 regime_watch.py --baseline      # record today's regime
python3 regime_watch.py --once          # sanity check: "no regime changes"
sudo cp deploy/regime-watch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now regime-watch
journalctl -fu regime-watch             # watch it work
```

Optional Telegram alerts: put `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` in the
unit's `Environment=` lines (or export them), then restart the service.
Without them it's log-only — still fine.

## Operating protocol (important)
1. On a `REGIME-CHANGE` alert touching **fees, feeSchedule, seconds_delay,
   tick size, or anything settlement-related**: stop the S1 trader first
   (`touch /opt/s1/s1_harness/KILL`), read the diff in `regime_watch.log` +
   `snapshots/`, decide, then restart.
2. Check `python3 regime_watch.py --status` whenever the harness/trader
   behaves oddly — rule changes are suspect #1.
3. If you see `WATCHER-BLIND`, the watcher itself is failing; fix that
   before trusting any "no change" output.

## Files
- `regime_watch.py` — the daemon (stdlib only, no pip)
- `regime_state.json` — hashes + change counts (auto-created)
- `regime_watch.log` — append-only alert log
- `snapshots/<source>/` — last 4 snapshots per source, for diffing
- `run_watcher.sh`, `deploy/regime-watch.service` — launchers

No secrets anywhere. Read-only against public endpoints. ~6 requests per cycle.
