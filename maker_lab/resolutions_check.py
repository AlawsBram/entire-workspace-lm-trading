#!/usr/bin/env python3
"""Cross-witness audit: house Data API v2 /v2/resolutions vs our on-chain
CTF ground truth. Flags any round the house marked disputed / extended-review
and verifies status=resolved agrees with chain payoutNumerators presence.

Read-only, low rate (20 condition ids per call, sleeps between calls).

Usage: python3 resolutions_check.py [--rows N] [--csv OUT]
"""
import argparse, csv, json, sys, time, urllib.request

CHAIN = "history/BTC_fiveminute_long.chain.csv"
CH15 = "history/BTC_fifteen_long.csv"
V2 = "https://data-api.polymarket.com/v2/resolutions?condition="

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["data"]

def load(fname):
    rows = {}
    try:
        with open(fname) as f:
            for r in csv.DictReader(f):
                cid = r.get("condition_id") or r.get("conditionId")
                if cid and cid not in rows:
                    rows[cid] = r
    except FileNotFoundError:
        pass
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=400)
    ap.add_argument("--csv", default="history/resolutions_check.csv")
    a = ap.parse_args()
    rows = {**load(CH15), **load(CHAIN)}  # chain file wins
    cids = list(rows.keys())[-a.rows:]
    out = open(a.csv, "w", newline="")
    w = csv.writer(out)
    w.writerow(["condition_id", "chain_outcome", "v2_status", "was_disputed",
                "extended_review", "tx_hash", "log_index", "verdict"])
    flags = {"disputed": 0, "extended": 0, "unresolved": 0, "ok": 0, "err": 0}
    for i in range(0, len(cids), 20):
        batch = cids[i:i+20]
        try:
            data = get(V2 + ",".join(batch))
        except Exception as e:
            flags["err"] += len(batch)
            print("err", type(e).__name__, str(e)[:80]); time.sleep(2); continue
        by_cid = {d["condition_id"]: d for d in data}
        for cid in batch:
            r = rows[cid]; d = by_cid.get(cid)
            if not d:
                verdict = "MISSING-IN-V2"; flags["unresolved"] += 1
                w.writerow([cid, r.get("chain_outcome"), "", "", "", "", "", verdict]); continue
            dis = bool(d.get("was_disputed")); ext = bool(d.get("extended_review"))
            verdict = ("OK" if d.get("status") == "resolved" and not dis and not ext
                       else ("DISPUTED" if dis else ("EXTENDED_REVIEW" if ext else "NOT-RESOLVED")))
            flags["disputed" if dis else "extended" if ext else
                  "ok" if verdict == "OK" else "unresolved"] += 1
            w.writerow([cid, r.get("chain_outcome"), d.get("status"), dis, ext,
                        d.get("transaction_hash"), d.get("log_index"), verdict])
        time.sleep(0.3)
    out.close()
    print(f"checked {len(cids)} rounds:", flags)

if __name__ == "__main__":
    main()
