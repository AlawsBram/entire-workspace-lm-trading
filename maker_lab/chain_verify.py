#!/usr/bin/env python3
"""
chain_verify.py — the ONLY authoritative outcome source for auto-resolved
crypto rounds: the CTF payout vector on Polygon.

  payoutNumerators(conditionId, idx) on 0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
  idx 0 = "Up", idx 1 = "Down"  (order of market outcomes at creation)
  winner = index with payout 1 (both 0 => not yet resolved on-chain)

Background (audit 2026-09-27): neither /api/past-results `outcome` (derived
display field, == sign(close-open); wrong on 28-35% of sub-2bp rounds) nor a
single gamma `outcomePrices` fetch (replicas serve stale sides for hours after
settlement) is reliable on razor / late-reversal rounds. Money paid = chain.

FOURTH WITNESS (2026-10-07): the house's own Data API v2 resolution record
(GET /v2/resolutions?condition=… up to 20 ids, {data:[…]} envelope) is pulled
automatically on every run and cross-checked: status must be `resolved`,
`was_disputed`/`extended_review` must be false. Any row failing this is
counted in `house_flags` and carries the house tx hash for manual review.
Chain remains authoritative for DIRECTION; the house record certifies the
resolution LIFECYCLE (no disputes / re-resolutions).

Usage:
  chain_verify.py --csv history/BTC_fiveminute_long.csv [--sample N] [--seed S]
                  [--no-house]
Writes <csv>.chain.csv adding chain_outcome + house_* columns; prints
comparison vs `outcome`. Batched JSON-RPC (~0.3s/round); house lookups add
one HTTP call per 20 rows. 500-round sample ~ 3-4 min, full 76k ~ 1.5h.
"""
import argparse, csv, json, os, random, time, urllib.request

CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
SEL = "0x0504c814"   # payoutNumerators(bytes32,uint256)
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://rpc-mainnet.matic.quiknode.pro",
        "https://1rpc.io/matic"]   # llamarpc DNS-dead in this env; don't re-add

def post(u, payload, t=6):
    req = urllib.request.Request(u, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=t) as r:
        j = json.loads(r.read().decode())
    if isinstance(j, dict) and "error" in j: raise RuntimeError(str(j["error"]))
    return j

def chain_outcome(cid, tries=3):
    batch = [{"jsonrpc": "2.0", "id": i, "method": "eth_call",
              "params": [{"to": CTF, "data": SEL + cid[2:] + hex(i)[2:].rjust(64, "0")}, "latest"]} for i in (0, 1)]
    for t in range(tries):
        try:
            r = post(RPCS[t % len(RPCS)], batch)
            tot = [int(x["result"], 16) for x in sorted(r, key=lambda y: y["id"])]
            if tot[0] == tot[1] == 0: return "pending"
            return "up" if tot[0] > tot[1] else "down"
        except Exception:
            time.sleep(0.3)
    return "RPC_ERR"

HOUSE_V2 = "https://data-api.polymarket.com/v2/resolutions?condition="

def house_records(cids, tries=3):
    """House Data API v2 resolution records for up to 20 condition ids."""
    for t in range(tries):
        try:
            req = urllib.request.Request(HOUSE_V2 + ",".join(cids),
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return {d["condition_id"]: d for d in json.loads(r.read().decode())["data"]}
        except Exception:
            time.sleep(0.4)
    return {}

def house_cols(rec):
    if rec is None:
        return {"house_status": "", "house_disputed": "", "house_extended": "",
                "house_tx": "", "cross_verdict": "HOUSE-MISSING"}
    dis, ext = bool(rec.get("was_disputed")), bool(rec.get("extended_review"))
    st = rec.get("status")
    verdict = ("OK" if st == "resolved" and not dis and not ext
               else ("DISPUTED" if dis else ("EXTENDED_REVIEW" if ext else "NOT-RESOLVED:" + str(st))))
    return {"house_status": st, "house_disputed": dis, "house_extended": ext,
            "house_tx": rec.get("transaction_hash", ""), "cross_verdict": verdict}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--sample", type=int, default=0, help="verify a random sample of N rows (0=all)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-house", action="store_true", help="skip the Data API v2 house cross-check")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv)))
    idxs = list(range(len(rows)))
    if a.sample:
        random.seed(a.seed); idxs = sorted(random.sample(idxs, min(a.sample, len(idxs))))
    # prefetch the house lifecycle records (20 ids per call, polite cadence)
    HOUSE = {}
    if not a.no_house:
        cids = sorted({rows[k]["condition_id"] for k in idxs if rows[k].get("condition_id")})
        for i in range(0, len(cids), 20):
            HOUSE.update(house_records(cids[i:i + 20]))
            time.sleep(0.25)
    out_rows, m_ = [], {"match": 0, "differ": 0, "pending": 0, "err": 0, "house_flags": 0}
    t00 = time.time()
    for i, k in enumerate(idxs):
        r = dict(rows[k])
        r["chain_outcome"] = chain_outcome(r["condition_id"]) if r.get("condition_id") else "RPC_ERR"
        if a.no_house:
            r.update({"house_status": "", "house_disputed": "", "house_extended": "",
                      "house_tx": "", "cross_verdict": "SKIPPED"})
        else:
            hc = house_cols(HOUSE.get(r.get("condition_id")))
            r.update(hc)
            if hc["cross_verdict"] != "OK":
                m_["house_flags"] += 1
        out_rows.append(r)
        co = r["chain_outcome"]
        m_["match" if co == r["outcome"] else ("differ" if co in ("up", "down") else co if co == "pending" else "err")] += 1
        if i % 25 == 0:
            print(f"  {i}/{len(idxs)} match={m_['match']} differ={m_['differ']} pending={m_['pending']} "
                  f"err={m_['err']} house_flags={m_['house_flags']} {time.time()-t00:.0f}s", flush=True)
        time.sleep(0.04)
    outp = a.csv.replace(".csv", ".chain.csv")
    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys())); w.writeheader(); w.writerows(out_rows)
    flagged = [r for r in out_rows if r["cross_verdict"] not in ("OK", "SKIPPED")]
    for r in flagged[:10]:
        print("  HOUSE-FLAG:", r["condition_id"], r["cross_verdict"], r.get("house_tx"))
    print(json.dumps(dict(checked=len(out_rows), **m_, seconds=round(time.time() - t00), saved=outp), indent=1))

if __name__ == "__main__":
    main()
