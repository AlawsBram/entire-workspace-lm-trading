#!/usr/bin/env python3
"""NWS forecast-change watcher + weather bucket-sum scanner (measure-only).

Watches api.weather.gov forecast UPDATES for the 5 cities the US venue prices
daily-high temperature markets for. Each forecast change is a timestamped
public information event; on change we snapshot the affected bucket prices via
the anonymous Polymarket WS at t+0/+10s/+60s/+300s -> market reaction-lag
table. Independently, every hour we scan all buckets and alert when the
probability sum breaks coherence (<0.985 buy-arb / >1.05 overround).

Outputs (app_lab/weather/):
  nws_forecasts.jsonl   every observed forecast state (city, high, updateTime)
  lag_table.jsonl       forecast-change events + bucket px reactions
  bucket_sums.csv       hourly coherence scan per city/day

Usage: python3 nws_watch.py            # run forever (background)
       python3 nws_watch.py --once     # single scan pass (test/cron)
"""
import asyncio, json, os, sys, time, urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "weather")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "polymarket-weather-research (measure-only)"}
WS = "wss://gateway-ws-markets.polymarket.us/v1/ws/subscriptions"

# venue grid: city -> (lat, lon, station-code embedded in slug prefix)
CITIES = {
    "nyc": (40.7812, -73.9665, "nychigh"),
    "mia": (25.7959, -80.2870, "miahigh"),
    "sfo": (37.6190, -122.3810, "sfohigh"),
    "lax": (33.9425, -118.4080, "laxhigh"),
    "mdw": (41.7868, -87.7522, "mdwhigh"),
}
STATE = os.path.join(OUT, "state.json")

def load_state():
    try: return json.load(open(STATE))
    except Exception: return {"last_update": {}, "last_high": {}}

def save_state(st):
    tmp = STATE + ".tmp"; json.dump(st, open(tmp, "w")); os.replace(tmp, STATE)

def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def append(path, obj):
    with open(path, "a") as f: f.write(json.dumps(obj) + "\n")

def today_slugs(city_key, high_guess=None):
    """Today's + tomorrow's candidate bucket slugs for a city."""
    code = CITIES[city_key][2]
    out = []
    for d in (0, 1):
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d") if d == 0 else \
              datetime.fromtimestamp(time.time() + 86400, timezone.utc).strftime("%Y-%m-%d")
        out.append((day, f"tc-temp-{code}-{day}"))
    return out

async def snapshot_buckets(prefixes):
    """Lite-quote snapshot for every bucket matching given date prefixes."""
    import websockets, uuid
    # discover bucket slugs: try a wide °F range around plausible values
    slugs, meta = [], {}
    for day, pref in prefixes:
        for f in range(30, 111):
            # bucket naming: lt{f}f, gte{f}lt{f+1}f, gte{f}f handled via patterns
            pass
    # cheaper: query unified search per event to get actual bucket list
    for day, pref in prefixes:
        try:
            body = json.dumps({"query": f"Highest temperature {day}"}).encode()
            req = urllib.request.Request(
                "https://unified-api.polymarket.us/unified.domain.search.v1.SearchUnifiedService/Search",
                data=body, headers=dict(UA, **{"Content-Type": "application/json"}))
            bag = json.load(urllib.request.urlopen(req, timeout=20)).get("bag", {})
            for m in bag.get("markets", []):
                s = (m.get("slug") or {}).get("value", "")
                if pref in s and s not in slugs:
                    slugs.append(s); meta[s] = day
        except Exception as e:
            append(os.path.join(OUT, "errors.jsonl"),
                   {"op": "discover", "err": str(e)[:120], "ts": time.time()})
    if not slugs: return {}
    res = {}
    async with websockets.connect(WS, open_timeout=10) as ws:
        rid = str(uuid.uuid4())
        await ws.send(json.dumps({"subscribe": {"requestId": rid,
            "subscriptionType": "SUBSCRIPTION_TYPE_MARKET_DATA_LITE",
            "marketSlugs": slugs}}))
        seen = {}; t_end = time.time() + 8
        while time.time() < t_end and len(seen) < len(slugs):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                d = json.loads(raw).get("marketDataLite") or {}
                if d.get("marketSlug"): seen[d["marketSlug"]] = d
            except asyncio.TimeoutError: break
        await ws.send(json.dumps({"unsubscribe": {"requestId": rid}}))
    for s, d in seen.items():
        px = (d.get("currentPx") or {}).get("value")
        bb = (d.get("bestBid") or {}).get("value")
        ba = (d.get("bestAsk") or {}).get("value")
        res[s] = {"px": float(px) if px else None,
                  "bid": float(bb) if bb else None,
                  "ask": float(ba) if ba else None}
    return res

def nws_forecast(city_key):
    lat, lon, _ = CITIES[city_key]
    pt = get_json(f"https://api.weather.gov/points/{lat},{lon}")
    fc = get_json(pt["properties"]["forecast"])
    upd = fc.get("properties", {}).get("updateTime")
    highs = []
    for p in fc["properties"]["periods"][:4]:
        if "Today" in p["name"] and "Tonight" not in p["name"]:
            highs.append((p["name"], p.get("temperature")))
    return upd, highs

def bucket_sum(snap, day):
    pxs = [v["px"] for s, v in snap.items() if day in s and v["px"] is not None]
    asks = [v["ask"] for s, v in snap.items() if day in s and v["ask"] is not None]
    n = len(pxs)
    return sum(pxs), n, (sum(asks) if len(asks) == n and n else None)

async def scan_once(state):
    """One full pass: forecast diffs + hourly bucket sums."""
    changes = []
    for city in CITIES:
        try:
            upd, highs = nws_forecast(city)
        except Exception as e:
            append(os.path.join(OUT, "errors.jsonl"),
                   {"op": "nws", "city": city, "err": str(e)[:120], "ts": time.time()})
            continue
        prev_upd = state["last_update"].get(city)
        if upd != prev_upd:
            state["last_update"][city] = upd
            append(os.path.join(OUT, "nws_forecasts.jsonl"),
                   {"city": city, "updateTime": upd, "highs": highs, "ts": time.time()})
            if prev_upd is not None:  # not the first sighting
                changes.append((city, upd, highs))
    save_state(state)
    # react to forecast changes: snapshot now + delayed re-snapshots
    for city, upd, highs in changes:
        day_slugs = today_slugs(city)
        snap0 = await snapshot_buckets(day_slugs)
        ev = {"city": city, "updateTime": upd, "highs": highs, "t0": time.time(),
              "px_t0": snap0}
        append(os.path.join(OUT, "lag_table.jsonl"), ev)
        for delay in (10, 60, 300):
            await asyncio.sleep(delay)
            snap = await snapshot_buckets(day_slugs)
            append(os.path.join(OUT, "lag_table.jsonl"),
                   {"city": city, "t": f"+{delay}s", "ts": time.time(), "px": snap})
    # hourly bucket-sum coherence scan (all cities, today)
    path = os.path.join(OUT, "bucket_sums.csv")
    new = not os.path.exists(path)
    with open(path, "a") as f:
        if new: f.write("ts,city,day,sum_px,n_buckets,verdict\n")
        for city in CITIES:
            day_slugs = today_slugs(city)
            try:
                snap = await snapshot_buckets(day_slugs)
            except Exception as e:
                append(os.path.join(OUT, "errors.jsonl"),
                       {"op": "buckets", "city": city, "err": str(e)[:120], "ts": time.time()})
                continue
            for day, _ in day_slugs:
                s, n, asksum = bucket_sum(snap, day)
                if n == 0: continue
                # Real buy-arb costs the ASK to acquire every bucket; mids can
                # fake a signal on wide/thin next-day books. Flag only if the
                # executable ask-sum is <0.985.
                if asksum is not None and asksum < 0.985:
                    verdict = "BUY-ARB"
                elif asksum is not None and asksum > 1.05:
                    verdict = "OVERROUND-ASK"
                elif 0.985 <= s <= 1.05:
                    verdict = "OK"
                elif s > 1.05:
                    verdict = "OVERROUND-MID"
                else:
                    verdict = "MID-ONLY-UNRELIABLE"
                f.write(f"{time.time():.0f},{city},{day},{s:.4f},{n},"
                        f"{asksum if asksum is not None else ''},{verdict}\n")
                print(f"[sum] {city} {day}: mid={s:.3f} ask={asksum and round(asksum,3)} "
                      f"-> {verdict}", flush=True)

async def main(once=False):
    state = load_state()
    if once:
        await scan_once(state); return
    while True:
        try:
            await scan_once(state)
        except Exception as e:
            append(os.path.join(OUT, "errors.jsonl"),
                   {"op": "cycle", "err": str(e)[:160], "ts": time.time()})
        await asyncio.sleep(1800)  # 30-min cadence (forecast updates are slower)

if __name__ == "__main__":
    asyncio.run(main(once="--once" in sys.argv))
