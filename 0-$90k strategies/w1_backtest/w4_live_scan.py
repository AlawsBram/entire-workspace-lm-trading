#!/usr/bin/env python3
"""W4-LIVE-SCAN: cross-section test of every public 'market lags the forecast' claim.
For today's and tomorrow's buckets in all kept cities: calibrated forecast prob
(bias/sigma fit on past settled days, floor bins) vs the LIVE book ask of the YES
token right now. Executable dislocation = prob - (ask+2c) > theta. One snapshot;
repeat daily to build the revision-lag evidence base. Read-only."""
import sys, os, json, statistics as st
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/0-$90k strategies/w1_backtest")
from config import hj, CITIES, norm_cdf, load as w1load
import datetime as dt

WB = "/home/user/0-$90k strategies/w1_backtest"
def bin_interval(b):
    kind, v = b[0], b[1]
    if kind == "le": return (-99.0, v + 1.0)
    if kind == "ge": return (v, 99.0)
    if kind == "between": return (v[0], v[1] + 1.0)
    return (v, v + 1.0)

def fit_city(city):
    wx = w1load(f"wx_{city}.json"); evs = w1load(f"events_{city}.json")
    out = {}
    for lead in ("L0", "L1"):
        res = []
        for e in evs:
            d = e["end"][:10]; fc = wx.get(lead, {}).get(d)
            win = [bk for bk in e["buckets"] if bk["won"]]
            if fc is None or not win: continue
            lo, hi = bin_interval(win[0]["bin"]); res.append(fc - (lo + hi) / 2)
        if len(res) >= 8:
            out[lead] = (st.mean(res), max(st.pstdev(res), 0.6))
    return out

def fresh_wx(city):
    lat, lon, tz = CITIES[city]
    base = f"latitude={lat}&longitude={lon}&models=gfs_seamless&timezone=UTC"
    out = {"L0": {}, "L1": {}}
    hf = hj(f"https://historical-forecast-api.open-meteo.com/v1/forecast?{base}&daily=temperature_2m_max&start_date=2026-10-21&end_date=2026-10-22")
    for t, v in zip(hf["daily"]["time"], hf["daily"]["temperature_2m_max"]):
        out["L0"][t] = v
    pr = hj(f"https://previous-runs-api.open-meteo.com/v1/forecast?{base}&hourly=temperature_2m_previous_day1&start_date=2026-10-20&end_date=2026-10-23")
    acc = {}
    for t, v in zip(pr["hourly"]["time"], pr["hourly"]["temperature_2m_previous_day1"]):
        if v is None: continue
        ts = dt.datetime.fromisoformat(t).timestamp() + tz * 3600
        d = dt.datetime.utcfromtimestamp(ts).date().isoformat()
        acc[d] = max(acc.get(d, -99), v)
    out["L1"] = acc
    return out

def scan_city(city):
    fits = fit_city(city)
    fw = fresh_wx(city)
    rows = []
    today = dt.date(2026, 10, 21)
    for day, lead in ((today, "L0"), (today + dt.timedelta(days=1), "L1")):
        slug = f"highest-temperature-in-{city}-on-{day.strftime('%B').lower()}-{day.day}-{day.year}"
        try:
            ev = hj(f"https://gamma-api.polymarket.com/events?slug={slug}")[0]
        except Exception:
            continue
        f = fits.get(lead)
        if not f: continue
        bias, sigma = f
        for m in ev.get("markets") or []:
            toks = json.loads(m.get("clobTokenIds") or "[]")
            if not toks: continue
            try:
                bk = hj(f"https://clob.polymarket.com/book?token_id={toks[0]}")
                asks = sorted((float(x["price"]), float(x["size"])) for x in bk["asks"])
            except Exception:
                continue
            if not asks: continue
            ask, ask_sz = asks[0]
            lo, hi = bin_interval_parse(m["question"])
            if lo is None: continue
            mu = fw.get(lead, {}).get(day.isoformat())
            if mu is None: continue
            mu = mu - bias
            prob = norm_cdf((hi - mu) / sigma) - norm_cdf((lo - mu) / sigma)
            rows.append(dict(city=city, day=day.isoformat(), q=m["question"][-42:],
                             prob=round(prob, 3), ask=ask, ask_sz=ask_sz,
                             edge=round(prob - (ask + 0.02), 3)))
    return rows

import re
def bin_interval_parse(q):
    mb = re.search(r"between (-?\d+)°([CF]) and (-?\d+)°", q)
    if mb: return (int(mb.group(1)), int(mb.group(3)) + 1.0)
    m = re.search(r"be (-?\d+)°([CF])", q)
    if not m: return (None, None)
    v = int(m.group(1))
    if "or below" in q: return (-99.0, v + 1.0)
    if "or above" in q: return (v, 99.0)
    return (v, v + 1.0)

if __name__ == "__main__":
    cities = w1load("cities_kept.json")
    with ThreadPoolExecutor(6) as ex:
        allrows = [r for rows in ex.map(scan_city, cities) for r in rows]
    json.dump(allrows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_scan.json"), "w"), indent=1)
    live = [r for r in allrows if r["edge"] > 0.10]
    near = [r for r in allrows if 0.05 < r["edge"] <= 0.10]
    print(f"buckets scanned: {len(allrows)}; executable dislocations edge>10pts: {len(live)}; 5-10pts: {len(near)}")
    for r in sorted(live, key=lambda x: -x["edge"])[:15]:
        print(f"  {r['city']:<12} {r['day']} prob={r['prob']:.2f} ask={r['ask']:.2f} (size {r['ask_sz']:.0f}) edge={r['edge']:+.2f}  {r['q']}")
