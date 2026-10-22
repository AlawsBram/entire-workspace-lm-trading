#!/usr/bin/env python3
"""Fetch closed weather events (buckets + resolutions) + forecast archives per city."""
import sys, time, re, datetime as dt
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from config import *

ALIASES = {"new-york-city": ["new-york-city", "nyc"], "los-angeles": ["los-angeles", "la"],
           "san-francisco": ["san-francisco", "sf"], "washington-dc": ["washington-dc", "dc"]}

def parse_bin(q):
    mb = re.search(r"between (-?\d+)°([CF]) and (-?\d+)°", q)
    if mb:
        return ("between", (int(mb.group(1)), int(mb.group(3))), mb.group(2))
    m = re.search(r"be (-?\d+)°([CF])", q)
    if not m:
        return None
    kind = "le" if "or below" in q else ("ge" if "or above" in q else "eq")
    return (kind, int(m.group(1)), m.group(2))

def fetch_events():
    kept = {}
    for city in CITIES:
        evs = None
        for alias in ALIASES.get(city, [city]):
            try:
                cand = hj(f"https://gamma-api.polymarket.com/events?series_slug={alias}-daily-weather"
                          f"&closed=true&limit=100&order=endDate&ascending=false")
                if cand: evs = cand; break
            except Exception:
                continue
        if evs is None:
            print(f"  {city}: series probe failed"); continue
        rows = []
        for e in evs:
            ed = (e.get("endDate") or "")[:10]
            if ed < WINDOW_START: continue
            mk = []
            for m in (e.get("markets") or []):
                pr = m.get("outcomePrices")
                if not pr: continue
                pr = json.loads(pr) if isinstance(pr, str) else pr
                toks = m.get("clobTokenIds")
                toks = json.loads(toks) if isinstance(toks, str) else toks
                b = parse_bin(m["question"])
                if b is None: continue
                mk.append(dict(bin=b, token=toks[0],
                               won=(pr[0] == "1")))
            if mk and sum(1 for m in mk if m["won"]) == 1:
                rows.append(dict(slug=e.get("slug"), end=e.get("endDate"), buckets=mk))
        if len(rows) >= 15:
            kept[city] = rows
            save(f"events_{city}.json", rows)
            print(f"  {city}: {len(rows)} settled events in window")
        else:
            print(f"  {city}: only {len(rows)} events — dropped")
        time.sleep(SLEEP)
    save("cities_kept.json", sorted(kept))
    print(f"kept {len(kept)} cities")

def fetch_weather():
    for city in sorted(load("cities_kept.json")):
        lat, lon, tz = CITIES[city]
        evs = load(f"events_{city}.json")
        d0 = min(e["end"][:10] for e in evs); d1 = max(e["end"][:10] for e in evs)
        s = (dt.date.fromisoformat(d0) - dt.timedelta(days=4)).isoformat()
        e = (dt.date.fromisoformat(d1) + dt.timedelta(days=1)).isoformat()
        base = f"latitude={lat}&longitude={lon}&models=gfs_seamless&timezone=UTC"
        hrs = "temperature_2m,temperature_2m_previous_day1,temperature_2m_previous_day2,temperature_2m_previous_day3"
        try:
            pr = hj(f"https://previous-runs-api.open-meteo.com/v1/forecast?{base}&hourly={hrs}"
                    f"&start_date={s}&end_date={e}")
            hf = hj(f"https://historical-forecast-api.open-meteo.com/v1/forecast?{base}"
                    f"&hourly=temperature_2m&start_date={s}&end_date={e}")
        except Exception as ex:
            print(f"  {city}: wx fetch failed ({ex})"); continue
        def dmax(series, date_local, tz):
            vals = []
            for t, v in zip(series["time"], series["vals"]):
                if v is None: continue
                ts = dt.datetime.fromisoformat(t).timestamp() + tz * 3600
                if dt.datetime.utcfromtimestamp(ts).date().isoformat() == date_local:
                    vals.append(v)
            return max(vals) if vals else None
        out = {}
        for key, series in [("L0", hf["hourly"])] + [(f"L{i}", pr["hourly"]) for i in (1, 2, 3)]:
            col = "temperature_2m" if key == "L0" else f"temperature_2m_previous_day{key[1]}"
            ser = dict(time=series["time"], vals=series[col])
            out[key] = {d: dmax(ser, d, tz) for d in sorted({e["end"][:10] for e in evs})}
        save(f"wx_{city}.json", out)
        print(f"  {city}: wx archived {len(out['L0'])} days")
        time.sleep(SLEEP)

if __name__ == "__main__":
    fetch_events(); fetch_weather()
