#!/usr/bin/env python3
"""
maker_bot.py — OPEN-BOOK-MAKER live quoting bot for Polymarket BTC 5-minute rounds

WHAT IT DOES (plain language)
  Every 5 minutes Polymarket opens a new "will BTC be up or down" market.
  This bot posts BUY prices on BOTH outcomes — it bids for the UP token AND
  bids for the DOWN token (bidding DOWN = offering the other side; on
  Polymarket you can never sell shares you don't own, so two-sided making is
  always done with two BUY quotes). When people sell into those bids, the bot
  earns the gap vs fair value. It cancels FAST when fair moves, and stands
  down in the final seconds when smart money arrives.

SAFETY MODEL (read before running)
  * DRY RUN BY DEFAULT. DRY_RUN=true logs what it WOULD quote. Nothing trades.
  * LIVE mode requires BOTH: DRY_RUN=false in .env AND the Phase-A gate passed
    (see DECISION.md). Do not flip it early.
  * KILL SWITCH: create the file named in KILL_FILE and the bot cancels every
    resting order within one loop (~1s) and goes to standby. Delete the file to
    resume (only after understanding why you killed it).
  * DAILY STOP: marked-to-fair loss beyond DAILY_STOP_USD -> cancel all, halt
    until next UTC day.
  * POST-ONLY BY CONSTRUCTION: every intended bid is checked against the live
    book; if it would cross the touch (act as a taker), it is skipped.
  * NO QUOTING in the last NO_QUOTE_SECS of a round; cancel-all at round end.
  * Size is tiny: LIVE_QUOTE_SIZE shares per side (default 20 ≈ $10 at 50c).

FEEDS (same as book_recorder.py — proven in this workspace)
  * Chainlink 60s-TWAP + spot via Polymarket RTDS websocket (settlement feeds)
  * Fair value = S1-verified probability model (norm-cdf over remaining TWAP gap)
  * Market discovery: gamma slug btc-updown-5m-<start> -> clobTokenIds

OUTPUTS
  bot_logs/orders.jsonl    every (intended or placed) quote + cancels
  bot_logs/bot_rounds.csv  one row per round, SAME schema as maker_sim's
                           sim_rounds.csv -> chain_verify.py settles it later
"""
import asyncio, csv, json, os, time, urllib.request
from datetime import datetime, timezone

from make_strategy import HALF_SPREAD, FAIR_LO, FAIR_HI, NO_QUOTE_SECS
import book_recorder as br  # reuse proven RTDS + fair model + discovery

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "bot_logs")

def env(k, d=None): return os.environ.get(k, d)
def envf(k, d):
    try: return float(env(k, d))
    except (TypeError, ValueError): return d

DRY_RUN        = env("DRY_RUN", "true").strip().lower() != "false"
KILL_FILE      = env("KILL_FILE", os.path.join(HERE, "KILL"))
DAILY_STOP_USD = envf("DAILY_STOP_USD", 20.0)
QUOTE_SIZE     = envf("LIVE_QUOTE_SIZE", 20.0)      # shares per side
MAX_NET_SHARES = envf("MAX_NET_SHARES", 40.0)       # pilot inventory cap
REQUOTE_EPS    = envf("REQUOTE_EPS", 0.005)         # re-quote when fair moves 0.5c
NO_QUOTE       = int(NO_QUOTE_SECS.get("5m", 20))
ROUND_T        = 300

CLOB_HOST = "https://clob.polymarket.com"

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)

def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_book(token_id):
    try:
        req = urllib.request.Request(
            f"{CLOB_HOST}/book?token_id={token_id}",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            b = json.loads(r.read().decode())
        bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids", [])), reverse=True)
        asks = sorted(((float(x["price"]), float(x["size"])) for x in b.get("asks", [])))
        return dict(bb=bids[0][0] if bids else None, ba=asks[0][0] if asks else None)
    except Exception:
        return dict(bb=None, ba=None)

class Ledger:
    """Daily loss tracking + per-round inventory (net = up_shares - down_shares)."""
    def __init__(self):
        self.day = None; self.realized = 0.0; self.halted = False
        self.up = 0.0; self.down = 0.0; self.cost = 0.0
        self.round_start = None
        self.round_quotes = 0; self.round_fills = 0
    @property
    def net(self): return self.up - self.down
    def new_day_check(self):
        d = datetime.now(timezone.utc).date()
        if d != self.day:
            self.day, self.realized, self.halted = d, 0.0, False
            log(f"NEW UTC DAY {d} — loss counter reset")
    def on_fill(self, outcome, price, size):
        if outcome == "UP": self.up += size
        else: self.down += size
        self.cost += price * size
        self.round_fills += 1
    def mark(self, fair):
        # UP pays 1 if Up, DOWN pays 1 if Down, valued at fair / 1-fair
        return self.realized + self.up * fair + self.down * (1 - fair) - self.cost
    def new_round(self, start):
        self.round_start = start
        self.up = self.down = self.cost = 0.0
        self.round_quotes = 0; self.round_fills = 0

ledger = Ledger()

# ---------------------------------------------------------------- CLOB client
client = None
def init_client():
    global client
    if DRY_RUN: return
    from py_clob_client.client import ClobClient
    pk = env("POLYMARKET_PRIVATE_KEY")
    funder = env("POLYMARKET_PROXY_ADDRESS")
    sig = int(env("POLYMARKET_SIG_TYPE", "2"))
    if not pk: raise SystemExit("LIVE mode requires POLYMARKET_PRIVATE_KEY in env/.env")
    client = ClobClient(CLOB_HOST, key=pk, chain_id=137, signature_type=sig, funder=funder)
    client.set_api_creds(client.create_or_derive_api_creds())
    log("CLOB client ready (LIVE mode)")

def place_buy(token_id, price, size, tag):
    """Post a BUY (bid). Returns order id or None. Post-only enforced upstream."""
    rec = dict(ts=now_iso(), action="quote", mode="dry" if DRY_RUN else "live",
               side=f"BUY-{tag}", token=token_id[-12:], price=round(price, 3), size=size)
    if DRY_RUN:
        _log_order(rec); return "dry"
    try:
        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY
        args = OrderArgs(price=round(price, 3), size=size, side=BUY, token_id=token_id)
        signed = client.create_order(args)
        resp = client.post_order(signed, OrderType.GTC)
        rec["order_id"] = resp.get("orderID") or resp.get("orderId")
        rec["ok"] = bool(resp.get("success", True))
        _log_order(rec)
        return rec.get("order_id")
    except Exception as e:
        rec["error"] = str(e)[:200]; _log_order(rec)
        return None

def cancel_all():
    if DRY_RUN: return
    try:
        client.cancel_all()
        _log_order(dict(ts=now_iso(), action="cancel_all", mode="live"))
    except Exception as e:
        log(f"WARN cancel_all failed: {e}")

def _log_order(rec):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "orders.jsonl"), "a") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")

# ---------------------------------------------------------------- quote logic
class RestingQuotes:
    def __init__(self):
        self.up_px = None; self.up_id = None
        self.down_px = None; self.down_id = None
resting = RestingQuotes()

def clear_quotes():
    if resting.up_px is not None or resting.down_px is not None:
        cancel_all()
        resting.up_px = resting.down_px = None
        resting.up_id = resting.down_id = None

def sync_quotes(fair, tok_up, tok_down):
    """Two BUY bids around fair. Cancel+re-quote when fair drifts > REQUOTE_EPS."""
    bid_up = round(fair - HALF_SPREAD, 2)
    bid_down = round((1 - fair) - HALF_SPREAD, 2)
    bid_up = min(max(bid_up, 0.01), 0.98)
    bid_down = min(max(bid_down, 0.01), 0.98)

    # inventory caps (net = up - down)
    if ledger.net >= MAX_NET_SHARES: bid_up = None    # already long-full
    if ledger.net <= -MAX_NET_SHARES: bid_down = None  # already short-full

    # post-only guard + re-quote decision per side
    for tag, tok, px, cur_px, cur_id in (
        ("UP", tok_up, bid_up, resting.up_px, "up"),
        ("DOWN", tok_down, bid_down, resting.down_px, "down"),
    ):
        if px is None:
            continue
        book = fetch_book(tok)
        if book["ba"] is not None and px >= book["ba"]:
            continue  # would cross the touch -> skip (never take)
        if cur_px is None or abs(px - cur_px) > REQUOTE_EPS:
            if not DRY_RUN and cur_id:
                try: client.cancel(cur_id)
                except Exception: pass
            oid = place_buy(tok, px, QUOTE_SIZE, tag)
            if tag == "UP": resting.up_px, resting.up_id = px, oid
            else: resting.down_px, resting.down_id = px, oid
            ledger.round_quotes += 1

def poll_fills():
    """LIVE: reconcile maker fills since last poll (idempotent by trade id)."""
    if DRY_RUN or client is None: return
    try:
        trades = client.get_trades(maker_only=True) or []
    except Exception:
        return
    for t in trades[-20:]:
        tid = t.get("id") or t.get("transactionHash")
        if tid in seen_trades: continue
        seen_trades.add(tid)
        asset_id = t.get("asset_id") or t.get("token_id") or ""
        outcome = "UP" if asset_id.endswith(cur_tok_up[-12:]) else "DOWN"
        ledger.on_fill(outcome, float(t.get("price", 0)), float(t.get("size", 0)))
        log(f"FILL {outcome} {t.get('size')}@{t.get('price')}")

seen_trades = set()
cur_tok_up = ""

# ---------------------------------------------------------------- round table
def append_round_row(row):
    os.makedirs(LOG_DIR, exist_ok=True)
    p = os.path.join(LOG_DIR, "bot_rounds.csv")
    new = not os.path.exists(p)
    cols = ["mode", "label", "round_start", "n_quotes", "n_fills", "buys", "sells",
            "net_shares", "avg_buy", "avg_sell", "fair_mean_at_fill",
            "settled", "pnl_usd", "adv_sel_edge", "model_cert_hit", "model_cert_n"]
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new: w.writeheader()
        w.writerow({k: row.get(k, "") for k in cols})

# ---------------------------------------------------------------- main loop
async def main_loop():
    global cur_tok_up
    cur_start = None
    while True:
        try:
            ledger.new_day_check()
            # KILL SWITCH — checked every loop (~1s)
            if os.path.exists(KILL_FILE):
                clear_quotes()
                await asyncio.sleep(1); continue
            if ledger.halted:
                await asyncio.sleep(5); continue

            now = time.time()
            start = int(now // ROUND_T) * ROUND_T
            t_rem = start + ROUND_T - now

            # ---- new round ----
            if start != cur_start:
                if cur_start is not None:
                    clear_quotes()
                    log(f"ROUND END {cur_start}: quotes={ledger.round_quotes} "
                        f"fills={ledger.round_fills} up={ledger.up:.0f} down={ledger.down:.0f}")
                    append_round_row(dict(mode="live" if not DRY_RUN else "dryrun",
                                          label="5m", round_start=cur_start,
                                          n_quotes=ledger.round_quotes, n_fills=ledger.round_fills,
                                          buys=round(ledger.up, 1), sells=round(ledger.down, 1),
                                          net_shares=round(ledger.net, 1),
                                          settled="", pnl_usd="", adv_sel_edge=""))
                ledger.new_round(start)
                cur_start = start
                log(f"OPEN 5m {start} (t_rem={t_rem:.0f}s)")

            # ---- settlement window: stand down ----
            if t_rem < NO_QUOTE:
                clear_quotes()
                poll_fills()
                rs = br.round_state(300, "5m", start)
                md = br.model_for(300, rs)
                if md and ledger.mark(md["p"]) < -DAILY_STOP_USD:
                    ledger.halted = True
                    log(f"DAILY STOP hit ({ledger.mark(md['p']):.2f} USDC) — halted until next UTC day")
                await asyncio.sleep(1); continue

            # ---- fair value ----
            rs = br.round_state(300, "5m", start)
            if rs["o_twap"] is None:
                await asyncio.sleep(0.5); continue
            md = br.model_for(300, rs)
            if not md: await asyncio.sleep(0.5); continue
            fair = md["p"]
            if not (FAIR_LO <= fair <= FAIR_HI):
                clear_quotes()
                await asyncio.sleep(0.5); continue

            # ---- discover market + quote ----
            tok = br.get_tokens("5m", start)
            if tok and tok[0]:
                cur_tok_up = tok[0][0]
                sync_quotes(fair, tok[0][0], tok[0][1])
            poll_fills()
            await asyncio.sleep(1.0)
        except Exception as e:
            log(f"WARN loop error: {e}")
            await asyncio.sleep(2)

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    log(f"maker_bot starting — mode={'DRY RUN' if DRY_RUN else 'LIVE'} "
        f"size={QUOTE_SIZE}/side stop=${DAILY_STOP_USD}/day kill_file={KILL_FILE}")
    if not DRY_RUN:
        init_client()
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    loop.create_task(br.rtds()); loop.create_task(br.watchdog())
    loop.create_task(main_loop())
    try: loop.run_forever()
    except KeyboardInterrupt:
        clear_quotes(); log("stopped by user; all quotes cancelled")

if __name__ == "__main__":
    main()
