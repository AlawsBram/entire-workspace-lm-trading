#!/usr/bin/env python3
"""Stage 1: model probs -> candidate (event,bucket,lead) list. Stage 2: fetch price
history for candidate tokens only. No market data touches the candidate filter."""
import sys, os, time, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

def bin_interval(b):
    # floor cut-off rule: bucket b = [b, b+1)  (31.9 counts as 31)
    kind, v = b[0], b[1]
    if kind == "le": return (-99.0, v + 1.0)
    if kind == "ge": return (v, 99.0)
    if kind == "between": return (v[0], v[1] + 1.0)
    return (v, v + 1.0)

def lead_ts(end_iso, lead, tz):
    """Timestamp at which the market price is sampled for this lead.
    L0: 09:00 local on event day. L1: 18:00 local day before. L2: 18:00 local D-2. L3: D-3."""
    d = dt.date.fromisoformat(end_iso[:10])
    if lead == "L0": day, hour = d, 9
    else: day, hour = d - dt.timedelta(days=int(lead[1])), 18
    return int(dt.datetime(day.year, day.month, day.day, hour, 0).timestamp()) - tz * 3600

def candidates():
    cands = []
    for city in load("cities_kept.json"):
        wx = load(f"wx_{city}.json"); tz = CITIES[city][2]
        for ev in load(f"events_{city}.json"):
            d = ev["end"][:10]
            for bk in ev["buckets"]:
                lo, hi = bin_interval(bk["bin"])
                for lead in ("L0", "L1", "L2", "L3"):
                    fc = wx.get(lead, {}).get(d)
                    if fc is None: continue
                    cands.append(dict(city=city, slug=ev["slug"], end=ev["end"], lead=lead,
                                      lo=lo, hi=hi, fc=fc, token=bk["token"], won=bk["won"],
                                      ts=lead_ts(ev["end"], lead, tz)))
    save("candidates_raw.json", cands)
    print(f"raw (event,bucket,lead) rows: {len(cands)}")

def fetch_prices():
    from concurrent.futures import ThreadPoolExecutor
    cands = load("candidates_raw.json")
    toks = sorted({c["token"] for c in cands})
    todo = [t for t in toks if not os.path.exists(os.path.join(DATA, f"px_{t[:16]}.json"))]
    print(f"unique tokens: {len(toks)}; remaining: {len(todo)}", flush=True)
    done = [0]
    def one(tok):
        try:
            h = hj(f"https://clob.polymarket.com/prices-history?market={tok}&interval=1w&fidelity=10")
            save(f"px_{tok[:16]}.json", h.get("history") or [])
        except Exception:
            save(f"px_{tok[:16]}.json", [])
        done[0] += 1
        if done[0] % 250 == 0: print(f"  {done[0]}/{len(todo)}", flush=True)
        time.sleep(0.1)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, todo))
    print("prices done", flush=True)

if __name__ == "__main__":
    candidates(); fetch_prices()
