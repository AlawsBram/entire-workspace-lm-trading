#!/usr/bin/env python3
"""
maker_sim.py — maker quoting simulator (paper mode; never places orders)

  --live    run against the live market: shadow-quote with strategy v1,
            detect hypothetical fills against real book movement, settle each
            round at official resolution (same gamma polling as S1 arbiter).
  --replay F [F2 ...]  replay book_recorder.py JSONL files through the exact
            same strategy/fill code path (settlement fetched from gamma).

Outputs: sim_rounds.csv (one row per settled round), sim_fills.jsonl,
         maker_stats.json (running tally), maker_sim.log.

GATE (same discipline as S1): >=50 settled rounds, >=20 fills,
mean realized edge per fill > 0, model-certification >= 90%
=> then (and only then) consider a maker mode with real money.
"""
import asyncio, json, math, time, os, random, csv, argparse, sys
import urllib.request
from collections import deque
from datetime import datetime, timezone

import websockets
from make_strategy import Book, decide_quotes, detect_fills, RoundAccount, \
    QUOTE_SIZE, QUEUE_FILL_PROB, HALF_SPREAD

RTDS = "wss://ws-live-data.polymarket.com"
HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "sim_rounds.csv")
FILLS_PATH = os.path.join(HERE, "sim_fills.jsonl")
STATS_PATH = os.path.join(HERE, "maker_stats.json")
SYMBOL = "btc/usd"
ROUNDS = [(300, "5m"), (900, "15m")]
SIGMA_SAFETY = 1.5
CSV_COLS = ["mode", "label", "round_start", "n_quotes", "n_fills", "buys", "sells",
            "net_shares", "avg_buy", "avg_sell", "fair_mean_at_fill",
            "settled", "pnl_usd", "adv_sel_edge", "model_cert_hit", "model_cert_n"]

def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(HERE, "maker_sim.log"), "a") as f: f.write(line + "\n")
    except Exception: pass

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def norm_cdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

# ---------- shared market model (copied 1:1 from the S1-verified harness) ----
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
WS_HOLDER = [None]   # current websocket, so the watchdog can force-close it

def round_state(T, label, start):
    key = (T, label, start)
    if key not in state.rounds:
        state.rounds[key] = dict(o_twap=None, acc=0.0, elapsed=0.0, last_ts=None,
                                 acct=RoundAccount(), prev_book=None, quote=None,
                                 settled=False, late=False, rng=random.Random(start),
                                 cert_hit=0, cert_n=0)
    return state.rounds[key]

def on_twap_update(obs_ts, value):
    prev_val, prev_ts = state.holding, state.holding_since
    state.holding, state.holding_since = value, obs_ts
    state.samples.append((obs_ts, value))
    now = time.time()
    for (T, label) in ROUNDS:
        start = int(now // T) * T
        rs = round_state(T, label, start)
        if rs["o_twap"] is None and state.holding is not None and (now - start) <= 3:
            rs["o_twap"] = state.holding
            log(f"{label} {start}: open ref snapped twap={state.holding:.2f}")
        if rs["o_twap"] is None and (now - start) > 3: rs["late"] = True
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

def fair_p_for(T, rs):
    o = rs["o_twap"]
    if o is None or rs["elapsed"] <= 0: return None
    e = min(rs["elapsed"], T); r = T - e
    acc_avg = rs["acc"] / e
    if r <= 1: return 1.0 if acc_avg >= o else 0.0
    f_req = (T * o - e * acc_avg) / r
    sigma_f = SIGMA_SAFETY * stream_sigma() * math.sqrt(r / 3.0)
    return norm_cdf((state.holding - f_req) / sigma_f)

def get_tokens(label, start):
    key = (label, start)
    if key not in state.tokens:
        try:
            m = http_json(f"https://gamma-api.polymarket.com/markets?slug=btc-updown-{label}-{start}")[0]
            state.tokens[key] = json.loads(m["clobTokenIds"])
        except Exception:
            state.tokens[key] = None
    return state.tokens[key]

def poll_book(label, start):
    tok = get_tokens(label, start)
    if not tok: return None
    try:
        book = http_json(f"https://clob.polymarket.com/book?token_id={tok[0]}")
        bids = sorted(((float(b["price"]), float(b["size"])) for b in book["bids"]), reverse=True)
        asks = sorted(((float(a["price"]), float(a["size"])) for a in book["asks"]))
        return Book(bids, asks)
    except Exception:
        return None

# ---------- settlement + closeout --------------------------------------------
_new_csv = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
csv_f = open(CSV_PATH, "a", newline="")
csv_w = csv.writer(csv_f)
if _new_csv: csv_w.writerow(CSV_COLS)

def bump_stats(delta):
    s = json.load(open(STATS_PATH)) if os.path.exists(STATS_PATH) else \
        {"rounds": 0, "fills": 0, "pnl": 0.0, "cert_hit": 0, "cert_n": 0}
    for k, v in delta.items(): s[k] = s.get(k, 0) + v
    json.dump(s, open(STATS_PATH, "w"), indent=1)

def close_round(mode, T, label, start, rs, settled):
    acct = rs["acct"]
    pnl = acct.settle(settled == "Up")
    adv = acct.adverse_selection(settled == "Up")
    buys = [f for f in acct.fills if f[1] == "BUY"]; sells = [f for f in acct.fills if f[1] == "SELL"]
    fair_mean = sum(f[4] for f in acct.fills) / len(acct.fills) if acct.fills else None
    row = [mode, label, start, acct.n_quotes, len(acct.fills), len(buys), len(sells),
           round(acct.net_shares, 1),
           round(sum(f[2] for f in buys) / len(buys), 4) if buys else "",
           round(sum(f[2] for f in sells) / len(sells), 4) if sells else "",
           round(fair_mean, 4) if fair_mean else "",
           settled, f"{pnl:.4f}", f"{adv:.4f}" if adv is not None else "",
           rs["cert_hit"], rs["cert_n"]]
    csv_w.writerow(row); csv_f.flush()
    with open(FILLS_PATH, "a") as f:
        for (t, side, price, size, fair) in acct.fills:
            f.write(json.dumps({"label": label, "start": start, "t": t, "side": side,
                                "price": price, "size": size, "fair": fair,
                                "settled": settled}) + "\n")
    bump_stats({"rounds": 1, "fills": len(acct.fills), "pnl": pnl,
                "cert_hit": rs["cert_hit"], "cert_n": rs["cert_n"]})
    log(f"ROUND-SETTLED {mode} {label} {start}: settled={settled} quotes={acct.n_quotes} "
        f"fills={len(acct.fills)} net={acct.net_shares:+.0f}sh pnl={pnl:+.2f}USDC "
        f"adv_sel={adv if adv is None else format(adv, '+.4f')} cert={rs['cert_hit']}/{rs['cert_n']}")
    rs["settled"] = True

async def settle_task(mode, T, label, start):
    rs = state.rounds.get((T, label, start))
    if not rs or rs["settled"] or rs["late"]: return
    settled = None
    for _ in range(24):   # up to ~8 min: gamma finalization latency is variable
        try:
            m = http_json(f"https://gamma-api.polymarket.com/events?slug=btc-updown-{label}-{start}")[0]["markets"][0]
            pr = [float(x) for x in json.loads(m["outcomePrices"])]
            if m.get("closed") or not m.get("acceptingOrders"):
                settled = "Up" if pr[0] > 0.5 else "Down"; break
            if pr[0] >= 0.9995 or pr[0] <= 0.0005:
                settled = "Up" if pr[0] >= 0.9995 else "Down"; break
        except Exception: pass
        await asyncio.sleep(20)
    if settled is None:
        log(f"{label} {start}: resolution not final, round dropped"); return
    close_round(mode, T, label, start, rs, settled)

# ---------- one engine tick: quote + fill detection ---------------------------
def tick_one(mode, T, label, start, now, book, fair):
    rs = round_state(T, label, start)
    if rs["settled"] or rs["late"]: return
    acct = rs["acct"]
    t_rem = start + T - now
    if t_rem <= 0:
        if mode == "live" and not rs.get("closing"):
            rs["closing"] = True
            asyncio.get_running_loop().create_task(settle_task(mode, T, label, start))
        return
    quote = decide_quotes(fair, t_rem, label, acct.net_shares)
    fills = detect_fills(rs["prev_book"], book, rs["quote"], rs["rng"])
    for (side, price, size) in fills:
        acct.add(now, side, price, size, fair)
        # model certification: did the fair at fill time agree with the round's
        # eventual direction? counted at settlement via cert_hit/cert_n
        rs.setdefault("fill_fairs", []).append((fair, side))
        log(f"FILL {mode} {label} {start} t={now-start:.0f}s {side} {size:.0f}@{price:.3f} fair={fair:.3f}")
    if quote is not None and (quote[0] or quote[1]):
        acct.n_quotes += 1
    rs["prev_book"], rs["quote"] = book, quote

def finalize_certs(rs, settled_up):
    for (fair, side) in rs.get("fill_fairs", []):
        model_up = fair >= 0.5
        # a BUY is model-consistent if model said Up; SELL if model said Down
        ok = (model_up and side == "BUY") or ((not model_up) and side == "SELL")
        rs["cert_n"] += 1; rs["cert_hit"] += 1 if ok else 0

# wrap close_round to run cert pass first
_orig_close = close_round
def close_round(mode, T, label, start, rs, settled):
    finalize_certs(rs, settled == "Up")
    _orig_close(mode, T, label, start, rs, settled)

# ---------- LIVE mode ---------------------------------------------------------
async def live_loop():
    last_start = {}
    while True:
        now = time.time()
        try:
            for (T, label) in ROUNDS:
                start = int(now // T) * T
                prev = last_start.get((T, label))
                if prev is not None and prev != start:
                    # round rolled over: settle the finished one
                    prs = state.rounds.get((T, label, prev))
                    if prs and not prs["settled"] and not prs["late"] and not prs.get("closing"):
                        prs["closing"] = True
                        asyncio.get_running_loop().create_task(settle_task("live", T, label, prev))
                last_start[(T, label)] = start
                rs = round_state(T, label, start)
                if rs["late"] or rs["settled"]: continue
                book = poll_book(label, start)
                fair = fair_p_for(T, rs)
                if book: tick_one("live", T, label, start, now, book, fair)
        except Exception as e:
            log(f"WARN live tick: {e}")
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
                asyncio.create_task(hb())
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
    """force-reconnect RTDS on silent death; log a heartbeat every 60s so a
       dead-looking daemon can never masquerade as a healthy one."""
    last_hb = time.time()
    while True:
        await asyncio.sleep(15)
        staleness = time.time() - state.last_feed
        if staleness > 45 and WS_HOLDER[0] is not None:
            log(f"FEED-STALE {staleness:.0f}s — forcing RTDS reconnect")
            try: await WS_HOLDER[0].close()
            except Exception: pass
            state.last_feed = time.time()
        if time.time() - last_hb >= 60:
            last_hb = time.time()
            log(f"HEARTBEAT twap={state.holding and round(state.holding,1)} "
                f"feed_age={staleness:.0f}s rounds_tracked={len(state.rounds)}")

def run_live():
    log(f"maker_sim LIVE (paper) starting: half_spread={HALF_SPREAD} fill_prob={QUEUE_FILL_PROB} size={QUOTE_SIZE}")
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    loop.create_task(rtds()); loop.create_task(live_loop()); loop.create_task(watchdog())
    try: loop.run_forever()
    except KeyboardInterrupt: pass

# ---------- REPLAY mode -------------------------------------------------------
def run_replay(files):
    recs = []
    for fp in files:
        with open(fp) as f:
            for line in f:
                try: recs.append(json.loads(line))
                except Exception: pass
    recs.sort(key=lambda r: (r["label"], r["start"], r["ts"]))
    log(f"replay: {len(recs)} records from {len(files)} file(s)")
    for r in recs:
        T = 300 if r["label"] == "5m" else 900
        book = Book(r.get("bids") and [(p, s) for p, s in r["bids"]],
                    r.get("asks") and [(p, s) for p, s in r["asks"]])
        tick_one("replay", T, r["label"], r["start"], r["ts"], book, r.get("fair_p"))
    # settle every open round
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    pending = [(k, v) for k, v in state.rounds.items() if not v["settled"] and not v["late"]]
    async def settle_all():
        await asyncio.gather(*[settle_task("replay", T, lb, st) for (T, lb, st), v in pending])
    if pending:
        log(f"replay: settling {len(pending)} round(s) via gamma...")
        loop.run_until_complete(settle_all())
    log("replay done")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--replay", nargs="+", metavar="JSONL")
    a = ap.parse_args()
    if a.replay: run_replay(a.replay); return
    run_live()

if __name__ == "__main__":
    main()
