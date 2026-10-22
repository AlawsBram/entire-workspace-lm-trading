#!/usr/bin/env python3
"""Pair-spread existence probe (passive, read-only). For live BTC 5m rounds, sample
both tokens' books at 1 Hz and log: sum of best BIDS (the maker pair price), sum of
best ASKS (taker mint-arb price), top-of-book sizes, and quote churn. Answers:
  (1) does bidUp+bidDown <= 0.97/0.98 still exist, how often, at what depth?
  (2) how fast does top-of-book churn (the cancel/replace race intensity)?
  (3) does askUp+askDown < 1.00 ever print (free mint arb — expect ~never)?
No orders, no keys. ~2 REST calls/second, venue-polite.
"""
import asyncio, json, os, time, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pair_spread_probe.jsonl")

def hj(u, t=10):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())

def book(tok):
    b = hj(f"https://clob.polymarket.com/book?token_id={tok}")
    bids = sorted(((float(x["price"]), float(x["size"])) for x in b["bids"]), reverse=True)
    asks = sorted(((float(x["price"]), float(x["size"])) for x in b["asks"]))
    return bids, asks

async def main(secs=780):
    t0 = time.time()
    prev = {}
    while time.time() - t0 < secs:
        now = int(time.time())
        start = (now // 300) * 300
        try:
            ev = hj(f"https://gamma-api.polymarket.com/events?slug=btc-updown-5m-{start}")[0]["markets"][0]
            toks = json.loads(ev["clobTokenIds"])
        except Exception:
            await asyncio.sleep(1); continue
        try:
            bu, au = book(toks[0]); bd, ad = book(toks[1])
        except Exception:
            await asyncio.sleep(1); continue
        bb_u, bb_d = (bu[0] if bu else None), (bd[0] if bd else None)
        ba_u, ba_d = (au[0] if au else None), (ad[0] if ad else None)
        rec = dict(ts=now, t_el=now - start,
                   sum_bids=round(bb_u[0] + bb_d[0], 4) if bb_u and bb_d else None,
                   sum_asks=round(ba_u[0] + ba_d[0], 4) if ba_u and ba_d else None,
                   depth_u=bb_u[1] if bb_u else None, depth_d=bb_d[1] if bb_d else None,
                   churn_u=int(prev.get("u") not in (None, bb_u and bb_u[0])),
                   churn_d=int(prev.get("d") not in (None, bb_d and bb_d[0])))
        prev = dict(u=bb_u and bb_u[0], d=bb_d and bb_d[0])
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(main())
