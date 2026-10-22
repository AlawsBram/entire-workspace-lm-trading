#!/usr/bin/env python3
"""
truth_recorder.py — TRUTH-FEED DIVERGENCE RECORDER (measurement only, no keys)

For every BTC 5m & 15m up/down round, record what EACH information source
claims about the outcome, and WHEN, then measure divergence vs the only
ground truth (Polygon CTF payoutNumerators):

  LIVE (1 Hz, during the round)
    rtds_twap   Chainlink TWAP60 stream  — the settlement feed itself
    rtds_spot   Chainlink spot
    arbiter     our own accumulated-TWAP reconstruction vs open ref (S1-verified)
    book        CLOB best bid/ask/mid for the UP token (what traders believe)
  SETTLEMENT (polling after round end)
    gamma       gamma outcomePrices -> first-final timestamp + house display direction
    pastres     /api/past-results `outcome`  — the KNOWN-BUGGY derived field
                (wrong on 27.5-35% of sub-2bp rounds; that's what we measure)
    chain       payoutNumerators on Polygon — GROUND TRUTH direction + finality lag
    house_v2    Data API v2 /v2/resolutions — lifecycle (resolved/disputed/extended)

OUTPUTS (truth_data/)
    timeline-YYYY-MM-DD.jsonl   1 Hz live records + one "verdict" record/round
    divergences.csv             one verdict row per round (analysis input)

Provenance: RTDS/model core copied from maker_lab/book_recorder.py; chain +
house core copied from maker_lab/chain_verify.py (audit 2026-09-27, fourth
witness 2026-10-07). Slug format btc-updown-{5m,15m}-<start> verified live
2026-10-14. Read-only public endpoints; polite rates; KILL file honored.
"""
import asyncio, csv, json, math, os, time, urllib.request
from collections import deque
from datetime import datetime, timezone

try:
    import websockets
except ImportError:
    websockets = None

RTDS = "wss://ws-live-data.polymarket.com"
SYMBOL = "btc/usd"
ROUNDS = [(300, "5m"), (900, "15m")]
SIGMA_SAFETY = 1.5
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "truth_data")
KILL_FILE = os.path.join(HERE, "KILL")

GAMMA_POLL_S   = 5      # settlement display polling
CHAIN_POLL_S   = 15     # ground-truth polling
PR_DELAY_S     = 100    # past-results fetch delay after round end
FINAL_TIMEOUT_S = 2700  # give up finalizing a round after 45 min
BOOK_EVERY_S   = 2      # poll CLOB book every N seconds (per round)

CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
SEL = "0x0504c814"   # payoutNumerators(bytes32,uint256)
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://rpc-mainnet.matic.quiknode.pro",
        "https://1rpc.io/matic"]
HOUSE_V2 = "https://data-api.polymarket.com/v2/resolutions?condition="

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)

def iso(ts): return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def http_json(url, t=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())

def norm_cdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

# ------------------------------------------------------------------ state
class State:
    def __init__(self):
        self.holding = None; self.holding_since = None
        self.spot = None
        self.samples = deque(maxlen=1500)
        self.sigma1 = None
        self.rounds = {}
        self.markets = {}     # (label,start) -> dict(tokens,condition_id,accepting)
        self.last_feed = time.time()
state = State()
WS_HOLDER = [None]

def round_state(T, label, start):
    key = (T, label, start)
    if key not in state.rounds:
        state.rounds[key] = dict(o_twap=None, o_spot=None, acc=0.0, elapsed=0.0,
                                 last_ts=None, book=None, last_mid=None,
                                 finalize_spawned=False)
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
        return dict(p=p, acc_avg=acc_avg, gap_bps=gap_bps, r=0, o=o, coverage=e / T)
    f_req = (T * o - e * acc_avg) / r
    sigma_f = SIGMA_SAFETY * stream_sigma() * math.sqrt(r / 3.0)
    p = norm_cdf((state.holding - f_req) / sigma_f)
    return dict(p=p, acc_avg=acc_avg, gap_bps=gap_bps, r=r, o=o, coverage=e / T)

def get_market(label, start):
    """gamma discovery: tokens + condition_id (slug format verified live)."""
    key = (label, start)
    if key not in state.markets:
        try:
            m = http_json(f"https://gamma-api.polymarket.com/markets?slug=btc-updown-{label}-{start}")[0]
            state.markets[key] = dict(tokens=json.loads(m["clobTokenIds"]),
                                      condition_id=m.get("conditionId"),
                                      accepting=bool(m.get("acceptingOrders", True)))
        except Exception:
            state.markets[key] = None
    return state.markets[key]

def poll_book(rs, label, start):
    mk = get_market(label, start)
    if not mk: rs["book"] = None; return
    try:
        book = http_json(f"https://clob.polymarket.com/book?token_id={mk['tokens'][0]}", t=10)
        bids = sorted(((float(b["price"]), float(b["size"])) for b in book["bids"]), reverse=True)[:5]
        asks = sorted(((float(a["price"]), float(a["size"])) for a in book["asks"]))[:5]
        bb = bids[0][0] if bids else None; ba = asks[0][0] if asks else None
        rs["book"] = dict(bb=bb, ba=ba, bids=bids, asks=asks)
        if bb is not None and ba is not None:
            rs["last_mid"] = (bb + ba) / 2
    except Exception:
        rs["book"] = None

# ------------------------------------------------------------------ chain + house (proven)
def rpc_post(u, payload, t=6):
    req = urllib.request.Request(u, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=t) as r:
        j = json.loads(r.read().decode())
    if isinstance(j, dict) and "error" in j: raise RuntimeError(str(j["error"]))
    return j

def chain_outcome(cid, tries=3):
    batch = [{"jsonrpc": "2.0", "id": i, "method": "eth_call",
              "params": [{"to": CTF, "data": SEL + cid[2:] + hex(i)[2:].rjust(64, "0")}, "latest"]}
             for i in (0, 1)]
    for t in range(tries):
        try:
            r = rpc_post(RPCS[t % len(RPCS)], batch)
            tot = [int(x["result"], 16) for x in sorted(r, key=lambda y: y["id"])]
            if tot[0] == tot[1] == 0: return "pending"
            return "Up" if tot[0] > tot[1] else "Down"
        except Exception:
            time.sleep(0.3)
    return "RPC_ERR"

def house_record(cid):
    try:
        req = urllib.request.Request(HOUSE_V2 + cid, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode()).get("data", [])
        return data[0] if data else None
    except Exception:
        return None

def pastresults_outcome(label, start):
    """Fetch the buggy derived display field for this exact round."""
    variant = "fiveminute" if label == "5m" else "fifteenminute"
    try:
        u = (f"https://polymarket.com/api/past-results?symbol=BTC&variant={variant}"
             f"&assetType=crypto&currentEventStartTime={iso(start + 2 * (300 if label=='5m' else 900))}")
        res = http_json(u, t=20)["data"]["results"]
        for r in res:
            try:
                st = int(datetime.fromisoformat(r["startTime"].replace("Z", "+00:00")).timestamp())
            except Exception:
                continue
            if st == start:
                op, cp = r.get("openPrice"), r.get("closePrice")
                pr_gap = ((cp - op) / op * 1e4) if (op and cp) else None
                return dict(outcome=(r.get("outcome") or "").capitalize() or None,
                            openPrice=op, closePrice=cp,
                            pr_gap_bps=round(pr_gap, 2) if pr_gap is not None else None,
                            pct_change=r.get("percentChange"))
    except Exception:
        pass
    return dict(outcome=None, openPrice=None, closePrice=None, pr_gap_bps=None, pct_change=None)

# ------------------------------------------------------------------ outputs
CSV_COLS = ["start", "end", "label", "condition_id", "coverage", "gap_bps",
            "o_ref", "acc_avg", "rtds_close", "arbiter_outcome",
            "chain_outcome", "chain_final_ts", "chain_lag_s",
            "gamma_outcome", "gamma_first_final_ts", "gamma_lag_s",
            "pr_outcome", "pr_match", "pr_open", "pr_close", "pr_gap_bps",
            "book_mid_end",
            "house_status", "house_disputed", "house_extended", "house_verdict",
            "arbiter_match", "arbiter_early_s"]

def append_csv(row):
    os.makedirs(DATA_DIR, exist_ok=True)
    p = os.path.join(DATA_DIR, "divergences.csv")
    new = not os.path.exists(p)
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        if new: w.writeheader()
        w.writerow({k: row.get(k, "") for k in CSV_COLS})

def append_timeline(rec):
    os.makedirs(DATA_DIR, exist_ok=True)
    p = os.path.join(DATA_DIR, f"timeline-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl")
    with open(p, "a") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")

# ------------------------------------------------------------------ finalizer
async def finalize_round(T, label, start):
    """Poll every post-settlement source, measure lags/divergence, write verdict."""
    end = start + T
    rs = round_state(T, label, start)
    mk = get_market(label, start)
    cid = (mk or {}).get("condition_id")
    md = model_for(T, rs)
    acc_avg = md["acc_avg"] if md else None
    o_ref = md["o"] if md else None
    coverage = md["coverage"] if md else 0.0
    arbiter = ("Up" if acc_avg >= o_ref else "Down") if (acc_avg is not None and o_ref) else None

    gamma_out = gamma_ff = None
    chain_out = None; chain_ff = None
    deadline = time.time() + FINAL_TIMEOUT_S

    # gamma + chain polling (interleaved)
    while time.time() < deadline:
        await asyncio.sleep(GAMMA_POLL_S)
        if gamma_ff is None:
            try:
                m = http_json(f"https://gamma-api.polymarket.com/events?slug=btc-updown-{label}-{start}")[0]["markets"][0]
                pr = [float(x) for x in json.loads(m["outcomePrices"])]
                final = m.get("closed") or not m.get("acceptingOrders") or pr[0] >= 0.9995 or pr[0] <= 0.0005
                if final:
                    gamma_out = "Up" if pr[0] > 0.5 else "Down"
                    gamma_ff = time.time()
                    log(f"{label} {start}: gamma FINAL {gamma_out} lag={gamma_ff - end:.0f}s")
            except Exception:
                pass
        if cid and chain_out is None and time.time() > end + 20:
            co = await asyncio.get_event_loop().run_in_executor(None, chain_outcome, cid)
            if co not in ("pending", "RPC_ERR"):
                chain_out, chain_ff = co, time.time()
                log(f"{label} {start}: CHAIN TRUTH {chain_out} lag={chain_ff - end:.0f}s")
        if gamma_ff is not None and (chain_out is not None or time.time() > end + 600):
            break
    if chain_out is None and cid:
        chain_out = await asyncio.get_event_loop().run_in_executor(None, chain_outcome, cid)

    # past-results (buggy display field) + house lifecycle
    await asyncio.sleep(max(0, (end + PR_DELAY_S) - time.time()))
    prr = await asyncio.get_event_loop().run_in_executor(None, pastresults_outcome, label, start)
    house = await asyncio.get_event_loop().run_in_executor(None, house_record, cid) if cid else None
    if house:
        dis, ext = bool(house.get("was_disputed")), bool(house.get("extended_review"))
        st = house.get("status")
        hv = ("OK" if st == "resolved" and not dis and not ext
              else ("DISPUTED" if dis else ("EXTENDED_REVIEW" if ext else f"NOT-RESOLVED:{st}")))
    else:
        dis, ext, st, hv = "", "", "", "HOUSE-MISSING"

    gamma_lag = round(gamma_ff - end, 1) if gamma_ff else None
    row = dict(start=start, end=end, label=label, condition_id=cid or "",
               coverage=round(coverage, 3),
               gap_bps=round(md["gap_bps"], 2) if md else "",
               o_ref=round(o_ref, 2) if o_ref else "", acc_avg=round(acc_avg, 2) if acc_avg else "",
               rtds_close=round(state.holding, 2) if state.holding else "",
               arbiter_outcome=arbiter or "",
               chain_outcome=chain_out or "", chain_final_ts=round(chain_ff, 1) if chain_ff else "",
               chain_lag_s=round(chain_ff - end, 1) if chain_ff else "",
               gamma_outcome=gamma_out or "", gamma_first_final_ts=round(gamma_ff, 1) if gamma_ff else "",
               gamma_lag_s=gamma_lag if gamma_lag is not None else "",
               pr_outcome=prr["outcome"] or "",
               pr_match=(str(prr["outcome"]).lower() == str(chain_out).lower()) if (prr["outcome"] and chain_out in ("Up", "Down")) else "",
               pr_open=round(prr["openPrice"], 4) if prr.get("openPrice") else "",
               pr_close=round(prr["closePrice"], 4) if prr.get("closePrice") else "",
               pr_gap_bps=prr.get("pr_gap_bps") if prr.get("pr_gap_bps") is not None else "",
               book_mid_end=round(rs["last_mid"], 4) if rs.get("last_mid") else "",
               house_status=st, house_disputed=dis, house_extended=ext, house_verdict=hv,
               arbiter_match=(arbiter == chain_out) if (arbiter and chain_out in ("Up", "Down")) else "",
               arbiter_early_s=(gamma_lag if (arbiter == chain_out and gamma_lag is not None) else ""))
    append_csv(row)
    append_timeline(dict(type="verdict", ts=round(time.time(), 2), **{k: v for k, v in row.items()}))
    log(f"VERDICT {label} {start}: chain={chain_out} gamma={gamma_out}(lag {gamma_lag}s) "
        f"pr={prr['outcome']}(match={row['pr_match']}) arbiter={arbiter}(match={row['arbiter_match']}) house={hv}")

# ------------------------------------------------------------------ live loops
async def record_loop():
    os.makedirs(DATA_DIR, exist_ok=True)
    n = 0
    last_starts = {}
    while True:
        if os.path.exists(KILL_FILE):
            log("KILL file present — recorder paused (no writes)")
            await asyncio.sleep(2); continue
        now = time.time()
        try:
            for (T, label) in ROUNDS:
                start = int(now // T) * T
                # boundary crossing: spawn finalizer for the round that just ended
                prev = last_starts.get((T, label))
                if prev is not None and start != prev:
                    prs = state.rounds.get((T, label, prev))
                    if prs and prs["o_twap"] is not None and not prs["finalize_spawned"]:
                        prs["finalize_spawned"] = True
                        log(f"{label} {prev}: round ended — finalizer spawned")
                        asyncio.get_event_loop().create_task(finalize_round(T, label, prev))
                last_starts[(T, label)] = start
                rs = round_state(T, label, start)
                if rs["o_twap"] is None: continue
                if int(now) % BOOK_EVERY_S == 0:
                    await asyncio.get_event_loop().run_in_executor(None, poll_book, rs, label, start)
                md = model_for(T, rs)
                b = rs.get("book") or {}
                append_timeline(dict(type="live", ts=round(now, 2), label=label, start=start,
                                     t_el=round(now - start, 1),
                                     twap=round(state.holding, 2) if state.holding else None,
                                     spot=round(state.spot, 2) if state.spot else None,
                                     arbiter_p=round(md["p"], 4) if md else None,
                                     gap_bps=round(md["gap_bps"], 2) if md else None,
                                     bb=b.get("bb"), ba=b.get("ba"),
                                     bs=(b["bids"][0][1] if b.get("bids") else None),
                                     asz=(b["asks"][0][1] if b.get("asks") else None),
                                     mid=round(rs["last_mid"], 4) if rs.get("last_mid") else None))
            n += 1
            if n % 300 == 0:
                log(f"alive {n}s twap={state.holding and round(state.holding, 1)}")
        except Exception as e:
            log(f"WARN record tick: {e}")
        await asyncio.sleep(1.0)

async def rtds():
    if websockets is None:
        log("FATAL: pip install websockets"); return
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

# ------------------------------------------------------------------ daily (C2) tracker
# Daily up/down markets settle on BINANCE 1m candle closes at 12:00 ET (not Chainlink).
# Track: open ref = Binance 1m close at boundary; live gap + lock prob from Binance spot;
# PM daily-market book mid for the UP token. One boundary per day -> multi-day corpus.
from datetime import timedelta
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:
    ET = None

class Daily:
    boundary = None; o_ref = None; samples = deque(maxlen=2000); mid = None; tokens = None
daily = Daily()

def next_boundary(now):
    if ET is None: return None
    t = datetime.fromtimestamp(now, ET)
    b = t.replace(hour=12, minute=0, second=0, microsecond=0)
    if t >= b: b += timedelta(days=1)
    return b.timestamp()

BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]  # vision = official public mirror (api. geo-451s in some regions)

def binance_klines(q):
    last = None
    for h in BINANCE_HOSTS:
        try:
            return http_json(f"{h}/api/v3/klines?symbol=BTCUSDT&interval=1m&{q}", t=10)
        except Exception as e:
            last = e
    raise last

async def binance_loop():
    last_book_poll = 0.0
    while True:
        try:
            now = time.time()
            k = binance_klines("limit=2")
            spot = float(k[-1][4])
            daily.samples.append((now, spot))
            if daily.boundary is None or now >= daily.boundary:
                daily.boundary = next_boundary(now)
                daily.o_ref = None; daily.mid = None; daily.tokens = None
            if daily.o_ref is None and daily.boundary and now >= daily.boundary - 86400 + 65:
                # boundary passed 65+s ago: fetch the official 1m candle close
                bt = daily.boundary - 86400
                kk = binance_klines(f"startTime={int(bt*1000)}&limit=1")
                if kk:
                    daily.o_ref = float(kk[0][4]); daily.boundary = bt + 86400
                    log(f"DAILY boundary {int(bt)}: open ref snapped {daily.o_ref:.2f}")
            if daily.o_ref and now - last_book_poll > 10:
                last_book_poll = now
                if daily.tokens is None:
                    d = datetime.fromtimestamp(daily.boundary, ET)
                    slug = f"bitcoin-up-or-down-on-{d.strftime('%B').lower()}-{d.day}-{d.year}"
                    mk = get_market_like(slug)
                    daily.tokens = mk["tokens"] if mk else None
                if daily.tokens:
                    try:
                        bk = http_json(f"https://clob.polymarket.com/book?token_id={daily.tokens[0]}", t=10)
                        bb = max((float(x["price"]) for x in bk["bids"]), default=None)
                        ba = min((float(x["price"]) for x in bk["asks"]), default=None)
                        daily.mid = (bb + ba) / 2 if bb is not None and ba is not None else None
                    except Exception: pass
            if daily.o_ref:
                r = daily.boundary - now
                vals = [v for _, v in list(daily.samples)[-360:]]
                sig = 1.0
                if len(vals) >= 30:
                    d5 = [b - a for a, b in zip(vals, vals[1:])]
                    m = sum(d5) / len(d5)
                    sig = math.sqrt(max(sum((x - m) ** 2 for x in d5) / len(d5), 1e-12)) / math.sqrt(5.0)
                p_lock = norm_cdf((spot - daily.o_ref) / (sig * math.sqrt(max(r, 1)))) if r > 0 else (1.0 if spot >= daily.o_ref else 0.0)
                append_timeline(dict(type="daily", ts=round(now, 2), boundary=int(daily.boundary),
                                     o_ref=round(daily.o_ref, 2), spot=round(spot, 2),
                                     gap_bps=round((spot - daily.o_ref) / daily.o_ref * 1e4, 2),
                                     r_sec=round(r, 1), p_lock=round(p_lock, 4), mid=daily.mid))
        except Exception as e:
            log(f"WARN binance tick: {e}")
        await asyncio.sleep(5)

def get_market_like(slug):
    try:
        m = http_json(f"https://gamma-api.polymarket.com/markets?slug={slug}")[0]
        return dict(tokens=json.loads(m["clobTokenIds"]), condition_id=m.get("conditionId"))
    except Exception:
        return None

def main():
    log(f"truth_recorder starting -> {DATA_DIR} (rounds: {[l for _, l in ROUNDS]})")
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    loop.create_task(rtds()); loop.create_task(record_loop()); loop.create_task(watchdog())
    loop.create_task(binance_loop())
    try: loop.run_forever()
    except KeyboardInterrupt:
        log("stopped by user")

if __name__ == "__main__":
    main()
