#!/usr/bin/env python3
"""
book_recorder.py — high-frequency book + fair-value recorder (no credentials)

Feeds the maker quoting simulator. Every second, for the live BTC 5m & 15m
up/down rounds, it records:
  * Chainlink 60s-TWAP + spot (RTDS, the settlement feeds)
  * the S1-verified fair-value model output (p = prob Up settles, gap_bps)
  * CLOB book: best bid/ask + sizes, top-5 ladder, mid, spread

Output: book_data/YYYY-MM-DD.jsonl  (one JSON object per second per round)
Replay corpus for maker_sim.py --replay. Pure public endpoints.
"""
import asyncio, json, math, time, os, urllib.request
from collections import deque
from datetime import datetime, timezone

import websockets

RTDS = "wss://ws-live-data.polymarket.com"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "book_data")
SYMBOL = "btc/usd"
ROUNDS = [(300, "5m"), (900, "15m")]
SIGMA_SAFETY = 1.5

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def norm_cdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

class State:
    def __init__(self):
        self.holding = None; self.holding_since = None
        self.spot = None
        self.samples = deque(maxlen=1500)
        self.sigma1 = None
        self.rounds = {}
        self.tokens = {}
        self.last_feed = time.time()

state = State()
WS_HOLDER = [None]

def round_state(T, label, start):
    key = (T, label, start)
    if key not in state.rounds:
        state.rounds[key] = dict(o_twap=None, o_spot=None, acc=0.0, elapsed=0.0,
                                 last_ts=None, tokens=None, book=None)
    return state.rounds[key]

def snap_open_refs(label, start, now):
    rs = round_state({"5m": 300, "15m": 900}[label], label, start)
    if rs["o_twap"] is None and state.holding is not None and (now - start) <= 3:
        rs["o_twap"] = state.holding; rs["o_spot"] = state.spot
        log(f"{label} {start}: open refs snapped twap={rs['o_twap']:.2f}")

def on_twap_update(obs_ts, value):
    prev_val, prev_ts = state.holding, state.holding_since
    state.holding, state.holding_since = value, obs_ts
    state.samples.append((obs_ts, value))
    now = time.time()
    for (T, label) in ROUNDS:
        start = int(now // T) * T
        snap_open_refs(label, start, now)
        rs = round_state(T, label, start)
        if rs["last_ts"] is None: rs["last_ts"] = max(prev_ts or obs_ts, start)
        t0 = max(rs["last_ts"], start); t1 = min(obs_ts, start + T)
        if t1 > t0 and prev_val is not None:
            rs["acc"] += prev_val * (t1 - t0); rs["elapsed"] += (t1 - t0)
        rs["last_ts"] = obs_ts

def stream_sigma():
    vals = [v for _, v in list(state.samples)[-120:]]
    if len(vals) >= 30:
        d = [b - a for a, b in zip(vals, vals[1:])]; m = sum(d) / len(d)
        var = sum((x - m) ** 2 for x in d) / len(d)
        state.sigma1 = math.sqrt(max(var, 1e-12))
    if state.sigma1 is None: state.sigma1 = (state.holding or 80000) * 4.3e-6
    return state.sigma1

def model_for(T, rs):
    o = rs["o_twap"] if rs["o_twap"] is not None else rs["o_spot"]
    if o is None or rs["elapsed"] <= 0: return None
    e = min(rs["elapsed"], T); r = T - e
    acc_avg = rs["acc"] / e
    gap_bps = (acc_avg - o) / o * 1e4
    if r <= 1:
        p = 1.0 if acc_avg >= o else 0.0
        return dict(p=p, p_end=p, acc_avg=acc_avg, gap_bps=gap_bps, r=0)
    f_req = (T * o - e * acc_avg) / r
    sigma_f = SIGMA_SAFETY * stream_sigma() * math.sqrt(r / 3.0)
    p = norm_cdf((state.holding - f_req) / sigma_f)
    p_end = norm_cdf((state.holding - o) / sigma_f)
    return dict(p=p, p_end=p_end, acc_avg=acc_avg, gap_bps=gap_bps, r=r)

def get_tokens(label, start):
    key = (label, start)
    if key not in state.tokens:
        try:
            m = http_json(f"https://gamma-api.polymarket.com/markets?slug=btc-updown-{label}-{start}")[0]
            state.tokens[key] = (json.loads(m["clobTokenIds"]), bool(m.get("acceptingOrders", True)))
        except Exception:
            state.tokens[key] = None
    return state.tokens[key]

def poll_book(rs, label, start):
    tok = get_tokens(label, start)
    if not tok: rs["book"] = None; return
    try:
        book = http_json(f"https://clob.polymarket.com/book?token_id={tok[0][0]}")
        bids = sorted(((float(b["price"]), float(b["size"])) for b in book["bids"]), reverse=True)[:5]
        asks = sorted(((float(a["price"]), float(a["size"])) for a in book["asks"]))[:5]
        rs["book"] = dict(bids=bids, asks=asks,
                          bb=bids[0][0] if bids else None, ba=asks[0][0] if asks else None)
    except Exception:
        rs["book"] = None

def out_path():
    return os.path.join(DATA_DIR, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".jsonl")

async def record_loop():
    os.makedirs(DATA_DIR, exist_ok=True)
    n = 0
    while True:
        now = time.time()
        try:
            with open(out_path(), "a") as f:
                for (T, label) in ROUNDS:
                    start = int(now // T) * T
                    rs = round_state(T, label, start)
                    if rs["o_twap"] is None: continue
                    poll_book(rs, label, start)
                    md = model_for(T, rs)
                    b = rs["book"] or {}
                    bb, ba = b.get("bb"), b.get("ba")
                    rec = dict(ts=round(now, 2), label=label, start=start,
                               t_el=round(now - start, 1), t_rem=round(start + T - now, 1),
                               twap=state.holding, spot=state.spot,
                               acc_avg=md["acc_avg"] if md else None,
                               gap_bps=round(md["gap_bps"], 2) if md else None,
                               fair_p=round(md["p"], 4) if md else None,
                               fair_p_end=round(md["p_end"], 4) if md else None,
                               bb=bb, ba=ba,
                               bb_sz=b.get("bids", [[None, None]])[0][1] if b.get("bids") else None,
                               ba_sz=b.get("asks", [[None, None]])[0][1] if b.get("asks") else None,
                               mid=round((bb + ba) / 2, 4) if (bb and ba) else None,
                               spread=round(ba - bb, 4) if (bb and ba) else None,
                               bids=b.get("bids"), asks=b.get("asks"))
                    f.write(json.dumps(rec, separators=(",", ":")) + "\n")
            n += 1
            if n % 60 == 0: log(f"recorded {n}s of data (twap={state.holding and round(state.holding,1)})")
        except Exception as e:
            log(f"WARN record tick failed: {e}")
        await asyncio.sleep(1.0)

async def rtds():
    backoff = 2
    while True:
        try:
            async with websockets.connect(RTDS, max_size=None) as ws:
                WS_HOLDER[0] = ws
                log("RTDS connected")
                await ws.send(json.dumps({"action": "subscribe", "subscriptions": [
                    {"topic": "crypto_prices_twap_sixty", "type": "update",
                     "filters": json.dumps({"symbol": SYMBOL}, separators=(",", ":"))},
                    {"topic": "crypto_prices_chainlink", "type": "update",
                     "filters": json.dumps({"symbol": SYMBOL}, separators=(",", ":"))}]}))
                backoff = 2
                async def hb():
                    while True:
                        await asyncio.sleep(5); await ws.send("PING")
                hbt = asyncio.create_task(hb())
                async for raw in ws:
                    state.last_feed = time.time()
                    try: msg = json.loads(raw)
                    except Exception: continue
                    if msg.get("type") != "update": continue
                    p = msg.get("payload", {})
                    if p.get("symbol") != SYMBOL: continue
                    try:
                        val = float(p["full_accuracy_value"]) / 1e18 if "full_accuracy_value" in p else float(p["value"])
                    except Exception: continue
                    topic = msg.get("topic", "")
                    obs_ts = p.get("timestamp", time.time() * 1000) / 1000.0
                    if topic == "crypto_prices_twap_sixty":
                        on_twap_update(obs_ts, val)
                    elif topic == "crypto_prices_chainlink":
                        state.spot = val
        except Exception as e:
            log(f"RTDS error: {e}; reconnect in {backoff}s")
            await asyncio.sleep(backoff); backoff = min(backoff * 2, 60)
        finally:
            WS_HOLDER[0] = None

async def watchdog():
    while True:
        await asyncio.sleep(15)
        staleness = time.time() - state.last_feed
        if staleness > 45 and WS_HOLDER[0] is not None:
            log(f"FEED-STALE {staleness:.0f}s — forcing RTDS reconnect")
            try: await WS_HOLDER[0].close()
            except Exception: pass
            state.last_feed = time.time()

def main():
    log(f"book_recorder starting -> {DATA_DIR}/YYYY-MM-DD.jsonl")
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    loop.create_task(rtds()); loop.create_task(record_loop()); loop.create_task(watchdog())
    try: loop.run_forever()
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    main()
