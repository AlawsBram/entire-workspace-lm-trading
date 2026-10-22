# INSTRUCTIONS — full 76k on-chain relabel + daily history cron (YOUR VPS)

Run everything below on your VPS — the same box that runs `/opt/s1` and
`/opt/regime_watch` per MASTER-RUNBOOK. No keys, no wallet, no packages to
install: the relabel is read-only public Polygon RPC calls, Python stdlib only.

**Why:** the deep corpus labels came from single gamma fetches, and gamma
intermittently serves a stale side after settlement (past-results `outcome` is
worse — wrong on ~28-35% of sub-2bp rounds). The CTF payout vector on Polygon
is the literal record of which token paid $1. A 500-round random sample already
matched 500/500; this job does all 76,666 so zero doubt remains.

---

## STEP 0 — ship the updated tarball to the VPS (one-time)

The relabel tooling is new, so re-deliver `maker_lab.tar.gz` (from the machine
where this workspace lives — same scp pattern as MASTER-RUNBOOK §2):

```bash
scp maker_lab.tar.gz user@YOUR_VPS:/tmp/

# on the VPS — extract OVER the existing install (overwrites scripts, keeps your
# book_data/ recordings and anything else you added — no rm -rf needed):
sudo tar xzf /tmp/maker_lab.tar.gz -C /opt/maker_lab --strip-components=1
chmod +x /opt/maker_lab/deploy/history-refresh.sh
```

(If /opt/maker_lab doesn't exist yet, create it first:
`sudo mkdir -p /opt/maker_lab` — same layout as MASTER-RUNBOOK §2.)

## STEP 1 — test the relabel on 1,000 rounds (~2 min)

```bash
cd /opt/maker_lab
python3 chain_relabel.py --csv history/BTC_fiveminute_long.csv --limit 1000
```

Expected: a few hundred rows at 5-12 rounds/s, then a JSON stats block with
`labels_changed` in the low single digits. If `errs` climbs, fix RPC access
first (Troubleshooting at the bottom).

## STEP 2 — the full 76k run (~2-3.5h, survives logout, resumable)

```bash
cd /opt/maker_lab
nohup python3 chain_relabel.py --csv history/BTC_fiveminute_long.csv --workers 4 \
  > /var/log/chain-relabel.log 2>&1 &
echo $! | sudo tee /var/log/chain-relabel.pid
```

Monitor (progress line every 250 rounds, with rate + ETA):

```bash
tail -f /var/log/chain-relabel.log
```

- **If it dies / you kill it:** run the exact same nohup command again. It
  resumes from `history/BTC_fiveminute_long.chainlog.jsonl` (append-only
  checkpoint); `RPC_ERR` rows retry automatically.
- **Speed knob:** `--workers` up to 6 max on public RPCs; more workers usually
  just triggers 429 throttling and goes slower.
- The job is safe to run while S1/regime-watch run — it touches no credentials
  and only adds files under `history/`.

## STEP 3 — verify + promote the result

When the log shows the final JSON block:

```bash
cd /opt/maker_lab
python3 - <<'EOF'
import csv, json
s = json.load(open("history/BTC_fiveminute_long.relabel_stats.json"))
print(json.dumps(s, indent=1))
rows = list(csv.DictReader(open("history/BTC_fiveminute_long.relabeled.csv")))
bad = [r for r in rows if r["chain_outcome"] in ("", "RPC_ERR", "NO_ID")]
print("unresolved rows:", len(bad), bad[:3])
EOF
```

Healthy output: `chain_verified` ≈ 76,666 (minus ~14 abandoned 2025-12-19 rounds
that show `pending`), `change_rate` ~0.005-0.015. Spot-check any flipped row in
`history/BTC_fiveminute_long.chain_changes.csv` on Polygonscan:
contract `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` → read `payoutNumerators(conditionId, 0)`
and `(..., 1)` — index 0 = Up.

Then promote it (keeps a backup):

```bash
cd /opt/maker_lab/history
cp BTC_fiveminute_long.csv BTC_fiveminute_long.gamma-original.csv
mv BTC_fiveminute_long.relabeled.csv BTC_fiveminute_long.csv
```

## STEP 4 — same for the 15m corpus (optional, ~1h, ~27k rounds)

```bash
cd /opt/maker_lab
nohup python3 chain_relabel.py --csv history/BTC_fifteen_long.csv --workers 4 \
  > /var/log/chain-relabel-15m.log 2>&1 &
# when done: same verify block with the fifteen filenames, then the same cp/mv promote
```

## STEP 5 — install the daily history-refresh cron

```bash
crontab -l 2>/dev/null > /tmp/cron.bak
(crontab -l 2>/dev/null; echo "10 0 * * * /opt/maker_lab/deploy/history-refresh.sh >> /var/log/history-refresh.log 2>&1") | crontab -
crontab -l   # confirm the line is there
```

What it does daily at 00:10 UTC: rewrites the rolling 7-day full-precision price
corpus (the endpoint keeps only ~1 week), then incrementally extends both deep
outcome corpora from the newest stored round. Log rotation:

```bash
echo '/var/log/history-refresh.log { monthly; rotate 6; compress; missingok; notifempty }' \
  | sudo tee /etc/logrotate.d/history-refresh
```

## STEP 6 — keep new rounds chain-verified (after STEP 2 succeeds once)

```bash
sudo sed -i 's|^# python3 chain_relabel.py|python3 chain_relabel.py|' /opt/maker_lab/deploy/history-refresh.sh
grep chain_relabel /opt/maker_lab/deploy/history-refresh.sh   # both lines uncommented
```

The daily cron now chain-verifies yesterday's ~290 new 5m rounds (and ~96 15m)
in a few minutes, so the corpus stays 100% on-chain-verified forever.

---

## Troubleshooting

- **`errs` climbing:** a public RPC is throttling. Edit the `RPCS` list at the
  top of `/opt/maker_lab/chain_relabel.py` (remove the offender, add e.g.
  `https://polygon.drpc.org` or an Alchemy/Infura Polygon URL if you have one).
- **`pending` rows:** never-resolved on-chain (abandoned early rounds). They keep
  their original label; expected ~14 total.
- **Disk:** all outputs ≈ 15 MB plus a ~6 MB checkpoint.
- **Re-run is always safe:** with a complete checkpoint the script skips straight
  to writing outputs; delete the `.chainlog.jsonl` only if you want a full re-read.
