#!/usr/bin/env python3
"""US-venue BTC updown round recorder + BRTI-proxy arbiter.

MEASURE-ONLY: subscribes anonymously to the public Polymarket US websocket,
records frames with local ns clocks, samples public constituent-exchange
order books (Coinbase, Kraken, Bitstamp, Gemini) and computes a BRTI-proxy
TWAP60 per round boundary. NO trading, NO auth surfaces, polite traffic.

Oracle under audit (from the live market description):
  "60 BRTI prices are collected in the last minute before each of those two
   times. The official value is the simple average, rounded to 2dp, ties Up."

BRTI methodology (CME CF guide v2): consolidated relevant ORDER BOOKS of the
constituent exchanges, 100 BTC per-order cap, mid price-volume curve median,
books stale >30s or deviating >25% from median-of-mids are disregarded.
Our proxy simplifies to top-of-book mids + volume-weighted median of mids;
the resulting reconstruction error is THE measurement we care about.

Outputs (all under app_lab/us_rounds/):
  frames-<UTCdate>.jsonl      every venue WS frame + recv clock
  brti-proxy-<UTCdate>.jsonl  per-second proxy samples + final-minute TWAPs
  rounds.csv                  one row per round: settlement vs proxy vs book

Usage:
  python3 us_round_recorder.py --test      # 12s smoke test
  python3 us_round_recorder.py             # run forever (background)
"""
import asyncio, json, os, sys, time, urllib.request
from collections import deque
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "us_rounds")
os.makedirs(OUT, exist_ok=True)
WS = "wss://gateway-ws-markets.polymarket.us/v1/ws/subscriptions"
UA = {"User-Agent": "Mozilla/5.0 (measurement-only research)"}

def now_ns(): return time.time_ns()
def utc(): return datetime.now(timezone.utc)
def log(*a): print(f"[{utc().strftime('%H:%M:%S')}]", *a, flush=True)

def rpc(path, body=None, host="gateway.polymarket.us"):
    req = urllib.request.Request(f"https://{host}/{path}",
        data=json.dumps(body or {}).encode(),
        headers=dict(UA, **{"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

# ---------- round plumbing ----------
def current_rounds():
    """(15m-round-start, 1h-round-start) aligned to wall clock."""
    t = int(time.time())
    return (t // 900) * 900, (t // 3600) * 3600

def slug_for(start, secs):
    tag = {900: "15m", 3600: "1h"}[secs]
    return f"btc-updown-{tag}-{datetime.fromtimestamp(start, timezone.utc).strftime('%Y-%m-%d-%H%M')}z"

def next_boundary():
    t = time.time()
    c15, c1h = current_rounds()
    return min(c15 + 900, c1h + 3600)

# ---------- constituent order books ----------
class Books:
    """Top-of-book state per constituent exchange; mid() returns (px, ts)."""
    def __init__(self):
        self.best = {}   # exch -> {"bid":..,"ask":..,"ts":..}
    def mid(self, exch):
        b = self.best.get(exch)
        if not b or b.get("bid") is None or b.get("ask") is None: return None
        if now_ns()/1e9 - b["ts"] > 30: return None            # staleness rule
        return (b["bid"] + b["ask"]) / 2, b["ts"]
    def proxy_px(self):
        """Volume-weighted median of mids (sizes approx equal -> median)."""
        mids = sorted(m for m in (self.mid(e) for e in self.best) if m)
        if not mids: return None
        vals = [m[0] for m in mids]
        med = vals[len(vals)//2]
        keep = [v for v in vals if abs(v/med - 1) <= 0.25]      # 25% deviation rule
        if not keep: keep = vals
        return sum(keep)/len(keep)

BOOKS = Books()
SAMPLES = deque()          # (ts, proxy_px) — rolling, trimmed to ~75s
TWAPS = {}                 # boundary_ts -> {"samples": n, "twap": px}

async def feed_coinbase():
    """Coinbase ADV WS level2 now requires auth; use REST book snapshot @1s."""
    while True:
        try:
            j = await asyncio.get_event_loop().run_in_executor(None, lambda: urllib.request.urlopen(
                urllib.request.Request("https://api.exchange.coinbase.com/products/BTC-USD/book?level=1",
                                       headers=UA), timeout=8).read())
            b = json.loads(j)
            bids, asks = b.get("bids"), b.get("asks")
            if bids and asks:
                BOOKS.best["coinbase"] = {"bid": float(bids[0][0]), "ask": float(asks[0][0]),
                                          "ts": now_ns()/1e9}
        except Exception as e: log("coinbase poll:", type(e).__name__)
        await asyncio.sleep(1.0)

async def feed_kraken():
    """Kraken public REST OHLC/book: best bid/ask via /public/Ticker @1s."""
    while True:
        try:
            raw = await asyncio.get_event_loop().run_in_executor(None, lambda: urllib.request.urlopen(
                urllib.request.Request("https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
                                       headers=UA), timeout=8).read())
            d = json.loads(raw)["result"]
            k = next(iter(d))
            bid = float(d[k]["b"][0]); ask = float(d[k]["a"][0])
            BOOKS.best["kraken"] = {"bid": bid, "ask": ask, "ts": now_ns()/1e9}
        except Exception as e: log("kraken poll:", type(e).__name__)
        await asyncio.sleep(1.0)

async def feed_bitstamp():
    import websockets
    while True:
        try:
            async with websockets.connect("wss://ws.bitstamp.net", open_timeout=10) as ws:
                await ws.send(json.dumps({"event": "bts:subscribe", "data": {"channel": "order_book_btcusd"}}))
                async for raw in ws:
                    j = json.loads(raw)
                    if j.get("event") == "data" and "bids" in j.get("data", {}):
                        d = j["data"]
                        if d["bids"] and d["asks"]:
                            BOOKS.best["bitstamp"] = {"bid": float(d["bids"][0][0]),
                                                      "ask": float(d["asks"][0][0]),
                                                      "ts": now_ns()/1e9}
        except Exception as e: log("bitstamp feed restart:", type(e).__name__); await asyncio.sleep(2)

async def feed_gemini():
    import websockets
    while True:
        try:
            async with websockets.connect("wss://api.gemini.com/v1/marketdata/BTCUSD?top_of_book=true", open_timeout=10) as ws:
                async for raw in ws:
                    j = json.loads(raw)
                    bid = ask = None
                    for ev in j.get("events", []):
                        if ev.get("type") == "change" and ev.get("remaining") not in ("0", 0):
                            if ev.get("side") == "bid": bid = float(ev["price"])
                            elif ev.get("side") == "ask": ask = float(ev["price"])
                    b = BOOKS.best.setdefault("gemini", {})
                    if bid is not None: b["bid"] = bid
                    if ask is not None: b["ask"] = ask
                    if bid or ask: b["ts"] = now_ns()/1e9
        except Exception as e: log("gemini feed restart:", type(e).__name__); await asyncio.sleep(2)

async def sampler():
    """1 Hz proxy sample; on boundary crossings compute final-minute TWAP."""
    import websockets  # noqa
    boundaries_seen = set()
    while True:
        px = BOOKS.proxy_px()
        t = time.time()
        if px:
            SAMPLES.append((t, px))
            while SAMPLES and SAMPLES[0][0] < t - 75: SAMPLES.popleft()
            with open(os.path.join(OUT, f"brti-proxy-{utc().strftime('%Y%m%d')}.jsonl"), "a") as f:
                f.write(json.dumps({"ts": round(t, 3), "px": round(px, 2),
                                    "books": sorted(BOOKS.best.keys())}) + "\n")
        # boundary crossings: compute TWAP60 for the minute that just ended
        for secs in (900, 3600):
            b = int(t // secs) * secs
            if b and b not in boundaries_seen and t - b >= 1.0:
                boundaries_seen.add(b)
                wins = [p for (ts, p) in SAMPLES if b - 60 <= ts < b]
                if wins:
                    TWAPS[b] = {"n": len(wins), "twap": sum(wins)/len(wins)}
                    log(f"boundary {b} ({slug_for(b-900 if secs==900 else b-3600, secs)} close): "
                        f"proxy TWAP60={TWAPS[b]['twap']:.2f} (n={len(wins)})")
        await asyncio.sleep(1.0)

# ---------- venue recorder ----------
class RoundState:
    def __init__(self, start, secs):
        self.start, self.secs = start, secs
        self.slug = slug_for(start, secs)
        self.frames = 0
        self.last = {}
        self.settled = None       # (px, source) once known
        self.res_polls = 0

def frame_file():
    return os.path.join(OUT, f"frames-{utc().strftime('%Y%m%d')}.jsonl")

def csv_row(state, up_px):
    path = os.path.join(OUT, "rounds.csv")
    new = not os.path.exists(path)
    b_close = state.start + state.secs
    tw_c = TWAPS.get(b_close, {})
    tw_o = TWAPS.get(state.start, {})
    settle_px, settle_src = (state.settled if state.settled else (None, None))
    pc, po = tw_c.get("twap"), tw_o.get("twap")
    # venue outcome: settlement 1.0 = Up wins; ~0 = Down wins
    venue_up = None if settle_px is None else settle_px >= 0.5
    # proxy outcome per the rule: close >= open on 2dp-rounded TWAP60, ties Up
    proxy_up = None
    if pc is not None:
        ref = po if po is not None else state.last.get("open_proxy")
        if ref is not None:
            proxy_up = round(pc, 2) >= round(ref, 2)
    match = None
    if venue_up is not None and proxy_up is not None:
        match = "OK" if venue_up == proxy_up else "DIVERGENCE"
    row = {
        "round": state.slug, "start": state.start, "end": b_close,
        "frames": state.frames,
        "up_px_final": up_px, "book_one_sided": state.last.get("one_sided"),
        "proxy_twap60_open": round(po, 2) if po else None,
        "proxy_twap60_close": round(pc, 2) if pc else None,
        "proxy_samples": tw_c.get("n"),
        "proxy_up": proxy_up, "venue_up": venue_up, "match": match,
        "settlement_px": settle_px, "settlement_src": settle_src,
    }
    with open(path, "a") as f:
        if new: f.write(",".join(row.keys()) + "\n")
        f.write(",".join("" if v is None else str(v) for v in row.values()) + "\n")
    log("round closed:", json.dumps(row))

async def venue_session(test=False):
    import websockets, uuid
    rounds = {}
    rid = str(uuid.uuid4())
    while True:
        try:
            c15, c1h = current_rounds()
            # track current AND next rounds: pre-subscribe before open so we
            # capture the opening book formation (open-book-maker research)
            want = {c15: 900, c1h: 3600, c15 + 900: 900, c1h + 3600: 3600}
            for start, secs in want.items():
                if start not in rounds:
                    st = rounds[start] = RoundState(start, secs)
                    st.last["open_proxy"] = BOOKS.proxy_px()
                    log("tracking", st.slug, "(pre-open)" if start > time.time() else "")
            slugs = [rounds[s].slug for s in want]
            async with websockets.connect(WS, open_timeout=10) as ws:
                await ws.send(json.dumps({"subscribe": {"requestId": rid,
                    "subscriptionType": "SUBSCRIPTION_TYPE_MARKET_DATA_LITE",
                    "marketSlugs": [f"cpc-{s}" for s in slugs]}}))
                t_end = time.time() + (12 if test else 900)
                while time.time() < t_end:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        continue
                    recv = now_ns()
                    j = json.loads(raw)
                    d = j.get("marketDataLite") or {}
                    slug = d.get("marketSlug")
                    if not slug: continue
                    st = next((r for r in rounds.values() if f"cpc-{r.slug}" == slug), None)
                    if not st: continue
                    st.frames += 1
                    px = (d.get("currentPx") or {}).get("value")
                    one_sided = (d.get("bestAsk") is None) or (d.get("bestBid") is None)
                    st.last.update(px=float(px) if px else st.last.get("px"),
                                   one_sided=one_sided,
                                   settle=d.get("settlementPx"))
                    if d.get("settlementPx") and not st.settled:
                        st.settled = (float(d["settlementPx"]["value"]), "ws")
                        log(st.slug, "settlementPx via WS:", st.settled[0])
                    with open(frame_file(), "a") as f:
                        f.write(json.dumps({"recv_ns": recv, "data": d},
                                           separators=(",", ":")) + "\n")
                await ws.send(json.dumps({"unsubscribe": {"requestId": rid}}))
            # session end: close out any rounds whose window fully passed
            now = time.time()
            for start, st in list(rounds.items()):
                end = start + st.secs
                if now >= end:
                    # poll HTTP settlement as second witness if WS didn't deliver
                    if not st.settled and st.res_polls < 3:
                        st.res_polls += 1
                        try:
                            r = rpc("gateway.market.v1.MarketService/GetMarketSettlement",
                                    {"slug": f"cpc-{st.slug}"})
                            if r.get("settlement") is not None:
                                st.settled = (float(r["settlement"]), "http")
                        except Exception as e:
                            log("settlement poll:", type(e).__name__)
                    csv_row(st, st.last.get("px"))
                    del rounds[start]
            if test: return
            await asyncio.sleep(2)
        except Exception as e:
            log("venue session restart:", type(e).__name__, str(e)[:120])
            await asyncio.sleep(3)

async def settlement_poller():
    """Long-poll rounds whose WS session ended before settlementPx arrived."""
    import websockets  # noqa
    pending = {}
    while True:
        try:
            done = []
            for slug in list(pending):
                r = rpc("gateway.market.v1.MarketService/GetMarketSettlement",
                        {"slug": f"cpc-{slug}"})
                if r.get("settlement") is not None:
                    with open(os.path.join(OUT, "settlements.jsonl"), "a") as f:
                        f.write(json.dumps({"slug": slug, "settlement": r["settlement"],
                                            "ts": time.time()}) + "\n")
                    done.append(slug)
            for d in done: pending.pop(d)
        except Exception:
            pass
        await asyncio.sleep(30)

async def main(test=False):
    tasks = [asyncio.create_task(coro()) for coro in
             (feed_coinbase, feed_kraken, feed_bitstamp, feed_gemini, sampler)]
    tasks.append(asyncio.create_task(venue_session(test=test)))
    if not test: tasks.append(asyncio.create_task(settlement_poller()))
    if test:
        await asyncio.sleep(14)
        log("test books:", {k: BOOKS.mid(k) for k in BOOKS.best})
        for t in tasks: t.cancel()
        return
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main(test="--test" in sys.argv))
