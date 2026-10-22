#!/usr/bin/env python3
"""
trimmer.py — Hyperliquid position trimmer ("never get liquidated" style)

Built from the Moon Dev stream spec (transcript, Oct 2026):
  * Watch a live Hyperliquid position and its REAL liquidation price (from HL).
  * Measure distance from whichever of MARK and MID is CLOSER to liquidation
    (conservative — mark is what HL liquidates on; mid moves faster).
  * When distance <= TRIGGER_PERCENT (default 2%): trim TRIM_PERCENT (default 5%)
    of the current position with a REDUCE-ONLY IOC limit order capped at
    SLIPPAGE_PERCENT (default 2%).
      - long  -> SELL to reduce
      - short -> BUY to reduce
  * After a trim, wait TRIM_WAIT_SECONDS (2s), then re-check immediately.
    Trim again only if still inside the zone. Loop every LOOP_SECONDS (1s).
  * NEVER cancels orders. NEVER adds to a position. Reduce-only by design.
  * MAX_TRIMS=0 means unlimited (keep trimming until outside the zone).
    Set MAX_TRIMS>0 only for testing.
  * LIVE=false (DEFAULT) -> prints what it WOULD do. Nothing trades.

Data: Hyperliquid public info API (no keys needed to READ any address).
      Optional MOONDEV_API backup if HL throttles (see .env.example).
Rate: ~3 REST calls/loop = ~180/min, far under HL's 1200/min cap; backoff on 429.

Usage:
  cp .env.example .env   # fill WALLET address (public) + optional key
  python trimmer.py
"""
import json, os, sys, time
import urllib.request, urllib.error
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# ------------------------------------------------------------------ config
def env(k, d=None): return os.environ.get(k, d)
def envf(k, d):
    try: return float(env(k, d))
    except (TypeError, ValueError): return d

WALLET           = env("HL_WALLET_ADDRESS", "")           # public address to watch (anyone's)
PRIVATE_KEY      = env("HL_PRIVATE_KEY", "")              # LIVE only. Never logged.
COIN             = env("COIN", "auto")                    # e.g. "BTC" or "auto" = biggest position
TRIGGER_PERCENT  = envf("TRIGGER_PERCENT", 2.0)           # distance to liq that starts trimming
TRIM_PERCENT     = envf("TRIM_PERCENT", 5.0)              # % of CURRENT position per trim
SLIPPAGE_PERCENT = envf("SLIPPAGE_PERCENT", 2.0)          # IOC limit cap
LOOP_SECONDS     = envf("LOOP_SECONDS", 1.0)
TRIM_WAIT_SECONDS= envf("TRIM_WAIT_SECONDS", 2.0)
MAX_TRIMS        = int(envf("MAX_TRIMS", 0))              # 0 = unlimited (production)
LIVE             = env("LIVE", "false").strip().lower() == "true"
API              = env("HL_API", "https://api.hyperliquid.xyz")
BACKUP_API_URL   = env("MOONDEV_API_URL", "")             # optional throttle backup
BACKUP_API_KEY   = env("MOONDEV_API_KEY", "")
KILL_FILE        = env("KILL_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "KILL"))

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)

# ------------------------------------------------------------------ HL REST
def hl_info(payload, tries=3):
    """POST to /info with backoff on 429/5xx."""
    body = json.dumps(payload).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(API + "/info", data=body,
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": "trimmer/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                wait = 2 ** i * 2
                log(f"THROTTLED/HTTP {e.code} — backing off {wait}s (attempt {i+1}/{tries})")
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if i == tries - 1: raise
            log(f"WARN request failed: {e} — retry {i+1}")
            time.sleep(1)
    # last resort: optional Moon Dev API backup (read-only position mirror)
    if BACKUP_API_URL and BACKUP_API_KEY:
        try:
            req = urllib.request.Request(BACKUP_API_URL, headers={"X-API-Key": BACKUP_API_KEY})
            with urllib.request.urlopen(req, timeout=10) as r:
                log("using MOONDEV backup feed")
                return json.loads(r.read().decode())
        except Exception as e:
            log(f"backup feed failed too: {e}")
    return None

def get_state():
    return hl_info({"type": "clearinghouseState", "user": WALLET})

def get_mids():
    return hl_info({"type": "allMids"}) or {}

def get_marks():
    """markPx per coin via metaAndAssetCtxs."""
    res = hl_info({"type": "metaAndAssetCtxs"})
    out = {}
    try:
        universe, ctxs = res[0]["universe"], res[1]
        for asset, ctx in zip(universe, ctxs):
            mp = ctx.get("markPx")
            if mp: out[asset["name"]] = float(mp)
    except Exception:
        pass
    return out

# ------------------------------------------------------------------ position
def pick_position(state):
    """Return (coin, pos) for COIN, or 'auto' = largest |positionValue|."""
    aps = (state or {}).get("assetPositions", [])
    rows = []
    for ap in aps:
        p = ap.get("position", {})
        try:
            szi = float(p.get("szi", 0))
        except (TypeError, ValueError):
            continue
        if szi == 0: continue
        rows.append((p.get("coin"), p, abs(float(p.get("positionValue", 0) or 0))))
    if not rows: return None, None
    if COIN and COIN != "auto":
        for coin, p, _ in rows:
            if coin == COIN: return coin, p
        return None, None
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows[0][0], rows[0][1]

def reference_price(side, mark, mid):
    """Whichever of mark/mid is CLOSER to liquidation (the more at-risk one)."""
    if mark is None: return mid
    if mid is None: return mark
    return min(mark, mid) if side > 0 else max(mark, mid)

def distance_pct(price, liq, side):
    if not price or not liq: return None
    return abs(price - liq) / price * 100.0

# ------------------------------------------------------------------ trim
exchange = None
def init_exchange():
    global exchange
    if not LIVE: return
    if not PRIVATE_KEY:
        log("LIVE=true but HL_PRIVATE_KEY missing — refusing to start. Exiting.")
        sys.exit(1)
    try:
        from hyperliquid.exchange import Exchange
        from eth_account import Account
        wallet = Account.from_key(PRIVATE_KEY)
        exchange = Exchange(wallet, API, account_address=WALLET or None)
        log("LIVE exchange ready (orders WILL be sent)")
    except ImportError:
        log("pip install hyperliquid-python-sdk  (required for LIVE)")
        sys.exit(1)

def do_trim(coin, side, size, mid, mark):
    """Reduce-only IOC limit order capped at slippage. Long->sell, Short->buy."""
    is_buy = side < 0                     # short trims by BUYING
    px_ref = mid or mark
    if is_buy:
        limit_px = round(px_ref * (1 + SLIPPAGE_PERCENT / 100), 6)
    else:
        limit_px = round(px_ref * (1 - SLIPPAGE_PERCENT / 100), 6)
    verb = "BUY" if is_buy else "SELL"
    if not LIVE:
        log(f"[DRY] WOULD {verb} {size} {coin} reduce-only IOC @<= {limit_px} "
            f"(slippage cap {SLIPPAGE_PERCENT}%)")
        return True
    try:
        resp = exchange.order(coin, is_buy, size, limit_px,
                              {"type": "Ioc"}, reduce_only=True)
        st = ((resp or {}).get("response", {}).get("data", {})
              .get("statuses", [{}]))
        log(f"[LIVE] {verb} {size} {coin} reduce-only IOC @<={limit_px} -> {st}")
        return True
    except Exception as e:
        log(f"[LIVE] trim FAILED: {e}")
        return False

def round_size(coin, size):
    """Round down to the coin's size tick (szDecimals)."""
    try:
        meta = hl_info({"type": "meta"})
        for a in meta.get("universe", []):
            if a.get("name") == coin:
                d = int(a.get("szDecimals", 4))
                f = 10 ** d
                return max(int(size * f) / f, 1 / f)
    except Exception:
        pass
    return round(size, 4)

# ------------------------------------------------------------------ main
def main():
    if not WALLET:
        log("Set HL_WALLET_ADDRESS in .env (any public 0x address works — reading is public).")
        sys.exit(1)
    log(f"trimmer starting — LIVE={LIVE} trigger={TRIGGER_PERCENT}% trim={TRIM_PERCENT}% "
        f"slippage={SLIPPAGE_PERCENT}% loop={LOOP_SECONDS}s coin={COIN} max_trims={MAX_TRIMS or 'unlimited'}")
    init_exchange()
    trims_this_streak = 0
    while True:
        try:
            if os.path.exists(KILL_FILE):
                log("KILL file present — standing by (no orders). Delete it to resume.")
                time.sleep(2); continue

            state = get_state()
            coin, pos = pick_position(state)
            if not pos:
                log("no open position" + (f" for {COIN}" if COIN != "auto" else ""))
                time.sleep(LOOP_SECONDS); continue

            szi = float(pos["szi"])
            side = 1 if szi > 0 else -1
            liq = float(pos.get("liquidationPx") or 0)
            entry = float(pos.get("entryPx") or 0)
            upnl = float(pos.get("unrealizedPnl") or 0)
            value = float(pos.get("positionValue") or 0)
            ret_pct = (upnl / value * 100) if value else 0.0

            mids = get_mids()
            marks = get_marks()
            mid = float(mids.get(coin, 0)) or None
            mark = marks.get(coin)
            ref = reference_price(side, mark, mid)
            dist = distance_pct(ref, liq, side)

            trim_size = round_size(coin, abs(szi) * TRIM_PERCENT / 100)
            log(f"{coin} {'LONG' if side>0 else 'SHORT'} size={abs(szi)} entry={entry} "
                f"mid={mid} mark={mark} ref={ref} liq={liq} dist={dist:.2f}% | "
                f"uPnL={upnl:+.2f} USDC ({ret_pct:+.2f}%) | next trim={trim_size} "
                f"({'SELL' if side>0 else 'BUY'}) @trigger<={TRIGGER_PERCENT}%")

            if dist is not None and dist <= TRIGGER_PERCENT:
                if MAX_TRIMS and trims_this_streak >= MAX_TRIMS:
                    log(f"inside zone but MAX_TRIMS={MAX_TRIMS} reached — watching only")
                else:
                    log(f"INSIDE ZONE ({dist:.2f}% <= {TRIGGER_PERCENT}%) — trimming {TRIM_PERCENT}%")
                    if do_trim(coin, side, trim_size, mid, mark):
                        trims_this_streak += 1
                    time.sleep(TRIM_WAIT_SECONDS)   # then re-check immediately
                    continue
            else:
                trims_this_streak = 0
            time.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            log("stopped by user"); break
        except Exception as e:
            log(f"WARN loop error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
