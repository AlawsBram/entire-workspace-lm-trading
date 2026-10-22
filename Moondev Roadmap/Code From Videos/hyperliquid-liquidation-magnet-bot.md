<!-- source: https://moondev.com/hyperliquid-liquidation-magnet-bot -->
<!-- captured: 2026-10-07 -->
<!-- title: Liq Magnet — Hyperliquid Liquidation Imbalance Trading Bot -->

Liq Magnet: A Hyperliquid Liquidation Imbalance Trading Bot | Algorithmic Trading | Moon Dev

Moon Dev Open Source

# Liq Magnet: A Hyperliquid Liquidation Imbalance Trading Bot

A single-file Python trading bot that reads which side of Hyperliquid is closest to getting blown up, then bets the 5-minute Polymarket BTC UP/DOWN window toward the bigger pool of forced market orders — with a maker-only bid resting **20% under the book**.

By Moon Dev · July 29, 2026

## The Thesis: Price Hunts Liquidity

Here is the idea in one sentence: **price goes where the forced orders are.** Every leveraged long on Hyperliquid has a liquidation price sitting *below* spot. Every leveraged short has one sitting *above* spot. When those levels get hit, the exchange does not politely ask the trader to close — it fires a market order into the book. Those forced market orders are the cleanest, most predictable flow in all of crypto, because they are legally obligated to happen.

So if you can see which side has more dollars parked near its liquidation price, you can see which direction has the bigger pool of guaranteed fuel. The Moon Dev API serves exactly that: the top 50 BTC longs and the top 50 BTC shorts on Hyperliquid that are closest to liquidation, filtered to a minimum position value of $75,000, priced off a live websocket feed. That is the whole signal.

**More LONG value near liquidation** → the fuel is **below** → bet **Down**.
**More SHORT value near liquidation** → the fuel is **above** → bet **Up**.

This bot is #1 of a five-bot fleet, and it is deliberately the **dumbest** one. Raw total value imbalance. No distance weighting, no leverage weighting, no whale filter, no cleverness. That is on purpose: Bot #1 is the baseline every other bot in the fleet gets measured against. Bots #2 through #4 refine the read, and Bot #5 (liq_sweep_fade) is the control arm that bets the exact opposite. Between #1 and #5, one of them prints if this signal has any direction in it at all. If neither does, the signal is noise and you learned that cheaply.

What you are going to learn in this walkthrough: how to turn a liquidation feed into a directional signal, how to place maker-only orders that can never accidentally pay the spread, how to detect a fill using position size instead of guessing from trade history, how to resolve a binary market honestly instead of assuming, and how to wire up risk controls that turn themselves off before you do. Let us build it.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hyperliquid-liquidation-magnet-bot)

## Step 1: The Docstring Is the Strategy

Every Moon Dev bot opens with a fat docstring that *is* the strategy document. If someone hands you this file six months from now with no context, the header alone tells you the thesis, the data source, the mechanics, the risk controls, and whether it is pointed at real money. Write these for future-you, because future-you will not remember.

Pay attention to the section labeled **HONEST CAVEAT**. Most trading bot code hides its weakness. This one leads with it. The bot rests a stink bid 20% under the market, which means it only gets filled when the market is actively moving *against* the direction the bot just picked. That is adverse selection, and it is baked into the mechanic. Stating it up front is not pessimism — it is the whole reason the eval log exists. The experiment is whether the liq-magnet signal is strong enough to pay for that adverse selection, and every window writes down enough data to answer that question with numbers instead of vibes.

Also note the deployment shape: single file, one pip dependency, repo-root .env required. A bot that touches real money should be auditable in one sitting.

The header — thesis, hard rule, and the honest caveat

```python
"""
================================================================================
🧲 MOON DEV's LIQ MAGNET v1.0   (july_29th_liq fleet, Bot #1)
================================================================================
THE THESIS: price hunts liquidity. The Moon Dev API (api.moondev.com
/api/positions.json) serves the top-50 BTC longs and top-50 BTC shorts on
Hyperliquid that are CLOSEST TO LIQUIDATION (min position value $75k, live
websocket price feed). Long liq prices sit BELOW spot, short liq prices sit
ABOVE spot. Whichever side has more dollar value at risk is the bigger pool of
forced market orders — and the market loves to sweep it.

  More LONG value near liquidation  -> the fuel is BELOW  -> bet DOWN
  More SHORT value near liquidation -> the fuel is ABOVE  -> bet UP

BOT #1 is the PUREST read: raw total value imbalance, no distance weighting,
no leverage weighting, no whale filter. Bots #2-#4 refine it; Bot #5
(liq_sweep_fade) bets the exact OPPOSITE as the control arm. Between #1 and #5
one of them prints if this signal has ANY direction in it at all.

--------------------------------------------------------------------------------
THE ONE HARD RULE — MOON DEV'S 20% BID DISCOUNT (every bot in this fleet)
--------------------------------------------------------------------------------
We NEVER pay the ask. We NEVER pay the bid. We rest a maker BUY (GTC,
post_only=True) at 20% UNDER the chosen side's best bid and WAIT FOR THE
PULLBACK. Book bid 0.52 -> our bid rests at 0.41. If the pullback never comes,
NO_FILL — zero dollars risked. If it fills, we own the side we wanted at a
20%-off price and hold to resolution.

HONEST CAVEAT (July 24th fleet lesson, stated up front): a stink bid fills
EXACTLY when the market moves against the thesis. That adverse selection is
inherent to the mechanic Moon Dev asked for — the experiment is whether the
liq-magnet signal is strong enough to pay for it. Every window logs the full
liq snapshot + the book so the answer gets measured, not vibed.

MECHANICS (identical across all 5 bots — only the brain differs):
  1. New 5-min window (btc-updown-5m-{T}) -> fetch a FRESH positions.json
     snapshot (BTC rows only). No data = no bet, logged as NO_LIQ_DATA. Real
     data or nothing — never faked.
  2. decide() picks Up or Down (this file: raw value imbalance).
  3. Read the chosen side's best bid, rest maker BUY at bid*(1-0.20), floored
     to the 1c tick, GTC post_only=True, $5 flat.
  4. Poll the position every 3s — a fill is detected by POSITION SIZE, the
     ground truth (we're the maker, so the fill price IS our limit).
  5. Cancel the unfilled order at T-20 and at rollover. Filled -> hold to
     resolution. Resolution = Gamma closed=true outcomePrices 1/0 ONLY
     (the July 24th correction — the default query hides closed markets).
  6. Daily stop -$30 realized (ET day). Kill switch: after 20 resolved trades,
     trailing-40 avg P&L < -$0.40/trade -> stop entering.

🔴 PAPER_MODE = False — LIVE on the AUG14 account (Gnosis Safe, sig type 2),
$5 flat. Flip to True to paper (paper fills simulate when the book bid trades
down through our resting price).

📦 SINGLE-FILE: only pip dep is py_clob_client_v2. Repo-root .env required
(MOONDEV_API_KEY + AUG14 keys).
Built by Moon Dev 🌙 — price hunts liquidity, we hunt the pullback. 🚀
================================================================================
"""
```
Read the PAPER_MODE = False line twice. This file ships aimed at a live account. Before you run anything, you flip it to True and watch it paper-trade for a few hours.

## Step 2: Zero-Dependency Stand-Ins and the Account Wiring

This is the "single file" promise in code. Instead of termcolor, there is a six-line colored() that emits raw ANSI escape codes. Instead of python-dotenv, there is a ten-line load_env() that reads .env, skips blanks and comments, splits on the first equals sign, and strips quotes. The os.environ.setdefault is deliberate: a variable already exported in the real environment always wins over the file.

Why bother? Because every pip package you add is a package that can ship a breaking change at 3am while your bot is holding a position. Two tiny helpers buy you immunity from that for the two most trivial dependencies in Python. The only thing left that genuinely cannot be inlined is py_clob_client_v2, which does real elliptic-curve order signing.

The re-exec block at the top is a small quality-of-life trick worth stealing. If the file gets launched by the wrong Python (cron, a different shell, a stale IDE interpreter), it detects that and os.execv replaces the running process with the correct interpreter, same arguments. No more "module not found" mysteries.

Then the account block. ACCOUNT_SUFFIX is a single knob that swaps which wallet the bot trades from — the private key, public key, and API credentials are all derived from that one string. SIGNATURE_TYPE = 2 means this address is a Gnosis Safe proxy rather than a plain EOA; get that wrong and Polymarket rejects your signatures. The keys themselves live in .env and never appear in the source.

Inline termcolor, inline dotenv, and the account block

```python
import sys
import os

# 🌙 Moon Dev - Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)

import time
import json
import csv
import math
import itertools
from collections import deque
import requests
from datetime import datetime, timezone, timedelta

# ============================================================================
# 🌙 MOON DEV - ZERO-DEP STAND-INS (stdlib only, py_clob_client_v2 is the only pip)
# ============================================================================
ANSI = {"red": "31", "green": "32", "yellow": "33", "magenta": "35", "cyan": "36", "white": "37"}

def colored(text, color=None, attrs=None):
    """🌙 Moon Dev - inline termcolor replacement (ANSI escapes, stdlib only)."""
    codes = (["1"] if attrs and "bold" in attrs else []) + ([ANSI[color]] if color in ANSI else [])
    return f"\033[{';'.join(codes)}m{text}\033[0m" if codes else str(text)

def load_env(path):
    """🌙 Moon Dev - inline dotenv replacement: parse KEY=VALUE lines into os.environ."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# ============================================================================
# 🌙 MOON DEV - PATH / ENV / ACCOUNT (AUG14 — Gnosis Safe)
# ============================================================================
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BOT_DIR))
load_env(os.path.join(PROJECT_ROOT, '.env'))

ACCOUNT_SUFFIX = "_AUG14"
PRIVATE_KEY_ENV_NAME = f"PRIVATE_KEY{ACCOUNT_SUFFIX}"
PUBLIC_KEY_ENV_NAME = f"PUBLIC_KEY{ACCOUNT_SUFFIX}"
SIGNATURE_TYPE = 2  # AUG14 = Gnosis Safe
MOONDEV_API_KEY = os.getenv("MOONDEV_API_KEY")
```
Gotcha worth knowing: MOONDEV_API_KEY is read once at import time. If the key is missing, the bot exits at startup rather than silently running with no signal. The liq data *is* the bot — no data means no reason to exist.

## Step 3: The Hard Rule and Every Other Knob

This block is the entire personality of the bot, and it is worth reading line by line. The headline constant is DISCOUNT_PCT = 0.20. That is the hard rule shared by all five bots in the fleet: **we never pay the ask, and we never pay the bid.** We rest a maker buy 20% under the chosen side's best bid and wait for a pullback. If the book bid is 0.52, our bid sits at 0.41. If the pullback never comes, we get nothing and we risked nothing.

The timing constants define the shape of a window. PLACE_AFTER = 285 means do not even evaluate until 285 seconds remain — that first 15 seconds is when the book is thin and garbage-priced, so we let it form. PLACE_FLOOR = 60 means if we still could not get data plus a book by T-60, give up on this window entirely; a bid placed with a minute left has almost no chance of catching a pullback. CANCEL_AT = 20 pulls the unfilled order with 20 seconds to go so we are not carrying a live resting order into the resolution scramble.

LIQ_MAX_AGE_SEC = 1800 is the stale-data guard, and the comment next to it is real measurement, not a guess. The feed refresh is irregular — observed ages ranged from 0 to 918 seconds. Near-liq clusters move slowly, so 30 minutes is the honesty line. Anything older and the window is skipped and logged as NO_LIQ_DATA. This is one of those guards people skip and then spend a week wondering why the backtest and the live results diverge.

Then the two risk controls. DAILY_STOP_LOSS = -30 halts new entries once the realized P&L for the Eastern-time day hits negative thirty dollars. The kill switch is subtler and better: after 20 resolved trades, if the trailing 40-trade average P&L per trade drops below KILL_AVG_PNL = -0.40, the bot stops entering forever. A daily stop protects the account from a bad day. The kill switch protects the account from a bad *idea*. Both matter, and the second one is the one most people forget to build.

Finally the two CSV schemas. EVAL_FIELDS gets one row per window, whether we bet or not — including the skips, the reason, the full liq snapshot, and the book. That is the re-mining dataset; it is what lets you go back later and ask "what if I had weighted by distance?" without collecting data all over again. TRADE_FIELDS only gets a row when we actually fill.

The knobs — the hard rule, the timers, the risk controls, the schemas

```python
# ============================================================================
# 🌙 MOON DEV - BOT IDENTITY + THE BRAIN'S KNOBS (this is what differs per bot)
# ============================================================================
BOT_NAME = "LIQ MAGNET"
BOT_EMOJI = "🧲"
CSV_PREFIX = "liq_magnet"
# Bot #1 brain: RAW total near-liq value per side. No weighting at all — the
# purest form of the signal, the baseline every other bot is measured against.

# ============================================================================
# 🌙 MOON DEV - THE HARD RULE + SHARED FLEET MECHANICS (identical in all 5 bots)
# ============================================================================
DISCOUNT_PCT = 0.20          # 🧲 THE HARD RULE: our maker bid rests 20% UNDER the book bid
USD_SIZE = 5                 # 💰 flat stake per entry
DAILY_STOP_LOSS = -30        # 🛑 halt new entries if realized day P&L hits this
PAPER_MODE = False           # 🔴 LIVE on AUG14. True = paper (simulated pullback fills)

PLACE_AFTER = 285            # ⏱ don't evaluate before time_left <= this (let the book form)
PLACE_FLOOR = 60             # ⏱ if we still couldn't place by T-60, give up this window
CANCEL_AT = 20               # ✂️ cancel the unfilled resting bid at time_left <= this
FILL_POLL_SEC = 3.0          # 🔁 position poll cadence while the bid rests
LIQ_MAX_AGE_SEC = 1800       # 💀 skip the window if the liq snapshot is older than this
                             #    (measured live 2026-07-29: feed refresh is irregular,
                             #    age ranged 0s-918s — near-liq clusters move slowly, so
                             #    30 min is the honesty line, and every row logs the age)
MIN_SHARES = 5               # Polymarket 5-share minimum per order
MARKET_DURATION = 300        # 5-minute windows
RESOLVE_GRACE_SEC = 15       # first resolution poll this many sec after close

KILL_MIN_TRADES = 20         # 🔫 kill switch arms after this many resolved trades
KILL_TRAILING = 40           # 🔫 ...over the trailing N resolved trades
KILL_AVG_PNL = -0.40         # 🔫 avg realized P&L/trade below this -> stop entering

ET = timezone(timedelta(hours=-4))
DATA_DIR = os.path.join(BOT_DIR, "data")
EVAL_LOG = os.path.join(DATA_DIR, f"{CSV_PREFIX}_eval.csv")
TRADES_FILE = os.path.join(DATA_DIR, f"{CSV_PREFIX}_trades.csv")
EVAL_FIELDS = ["timestamp", "window_ts", "slug", "spot", "liq_age_sec",
               "long_n", "long_val", "short_n", "short_val",
               "closest_long_pct", "closest_short_pct", "signal_score",
               "side", "book_bid", "our_bid", "action", "why", "paper"]
TRADE_FIELDS = ["timestamp", "market_ts", "slug", "side", "signal_score",
                "long_val", "short_val", "book_bid", "our_bid", "discount_pct",
                "shares", "usd", "result", "resolved_winner", "pnl_usd", "paper"]

# ============================================================================
# 🌙 MOON DEV - SESSION STATS
# ============================================================================
SESSION_START = time.time()
S = {"placed": 0, "fills": 0, "no_fill": 0, "no_data": 0, "no_book": 0,
     "daily_pnl": 0.0, "day": None, "halted": False, "killed": False}
SPINNER = itertools.cycle(["◐", "◓", "◑", "◒"])
EVENT_LOG = deque(maxlen=9)

def log_event(msg, color="white"):
    EVENT_LOG.append((datetime.now().strftime("%H:%M:%S"), msg, color))
```
Tip: log the skips. Most people only log their trades, which means their dataset is silently conditioned on having traded. The eval log here records every window the bot ever saw, which is the only way to honestly measure how selective your filters are.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hyperliquid-liquidation-magnet-bot)

## Step 4: The Maker-Only Order Layer

The client is built lazily and cached in a module-level global. Building a CLOB client involves deriving or fetching API credentials, which is slow and rate-limited, so you do it once and hold onto it. Note the checksum-address dance with a try/except AttributeError: web3.py renamed toChecksumAddress between major versions, and handling both spellings means the file runs on whatever web3 the environment happens to have.

Now the important function. place_maker_buy() is where the hard rule actually lives, and it is two flags doing all the work: OrderType.GTC means the order rests on the book until cancelled, and post_only=True means the exchange will **reject** the order rather than let it cross the spread. Our price is always below the current best bid so it should never cross anyway, but if the book moves violently between reading it and sending the order, post-only is the seatbelt. It is impossible for this bot to accidentally pay taker fees. That is a guarantee enforced by the exchange, not by our arithmetic.

There is a lovely side effect of being the maker: **we know our fill price exactly.** A taker order can slip through multiple price levels and you have to reconstruct the average. A resting maker order fills at precisely the price you posted. That is why the rest of the bot can compute P&L from our_bid without ever querying an average price.

Then position_for_token(), which is quietly the most important function in the file. It asks the data API what we actually hold, and it returns a three-state answer. A real size means we hold that many shares. Zero means we are genuinely flat. And (None, None) means *we could not read the position* — an HTTP error, a timeout, a bad response. Most people collapse that third case into "flat" and then their bot decides it was never filled, cancels nothing, and quietly carries an unaccounted position. Returning None forces the caller to handle "I do not know" as its own case. A fill is never faked, and neither is a non-fill.

The CLOB V2 client, the post-only maker buy, and the fill detector

```python
# ============================================================================
# 🌙 MOON DEV - V2 CLOB CLIENT (V1 post_order throws PolyApiException — it is dead!)
# ============================================================================
_CLIENT_CACHE = None

def _build_client():
    """🌙 Moon Dev - cached CLOB V2 client for AUG14."""
    global _CLIENT_CACHE
    if _CLIENT_CACHE is not None:
        return _CLIENT_CACHE
    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import ApiCreds
    from py_clob_client_v2.constants import POLYGON
    from web3 import Web3

    key = os.getenv(PRIVATE_KEY_ENV_NAME)
    pub = os.getenv(PUBLIC_KEY_ENV_NAME)
    if not key or not pub:
        print(colored(f"❌ Moon Dev - Missing {PRIVATE_KEY_ENV_NAME}/{PUBLIC_KEY_ENV_NAME} in .env!", "red"))
        sys.exit(1)
    try:
        funder = Web3.toChecksumAddress(pub)
    except AttributeError:
        funder = Web3.to_checksum_address(pub)

    client = ClobClient(host="https://clob.polymarket.com", chain_id=POLYGON,
                        key=key, signature_type=SIGNATURE_TYPE, funder=funder)
    api_key = os.getenv(f"API_KEY{ACCOUNT_SUFFIX}")
    # 🌙 Moon Dev - AUG14's secret falls back to SECRET_AUG14
    api_secret = os.getenv(f"API_SECRET{ACCOUNT_SUFFIX}") or os.getenv(f"SECRET{ACCOUNT_SUFFIX}")
    passphrase = os.getenv(f"PASSPHRASE{ACCOUNT_SUFFIX}")
    if api_key and api_secret and passphrase:
        client.set_api_creds(ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=passphrase))
    else:
        client.set_api_creds(client.create_or_derive_api_creds())
    _CLIENT_CACHE = client
    return client

def place_maker_buy(token_id, price, size):
    """🌙 Moon Dev - THE HARD RULE lives here: rest a maker BUY 20% under the bid.

    GTC + post_only=True — it can ONLY sit on the book and wait for the
    pullback. Our price is always below the current best bid, so it can never
    cross; if the book somehow moved through us, post_only rejects instead of
    paying taker. We are the MAKER: a fill is at EXACTLY `price`."""
    from py_clob_client_v2.clob_types import OrderArgs, OrderType
    client = _build_client()
    order_args = OrderArgs(token_id=str(token_id), price=float(price), size=float(size), side="BUY")
    log_event(f"🪤 RESTING maker BUY @ ${price:.2f} x{size:.2f} (20% under bid)", "magenta")
    try:
        resp = client.create_and_post_order(order_args, order_type=OrderType.GTC, post_only=True)
        return resp or {}
    except Exception as e:
        log_event(f"❌ maker buy failed: {type(e).__name__}: {e}", "red")
        return {}

def cancel_token_orders(token_id):
    """🌙 Moon Dev - Cancel resting GTC remainders (T-20 cutoff / rollover)."""
    from py_clob_client_v2.clob_types import OrderMarketCancelParams
    try:
        _build_client().cancel_market_orders(OrderMarketCancelParams(asset_id=str(token_id)))
    except Exception as e:
        log_event(f"⚠️ cancel failed: {type(e).__name__}", "yellow")

def position_for_token(token_id):
    """🌙 Moon Dev - (size, avg_price) we hold of token_id on AUG14, else (0, 0).
    The position IS the fill detector — no trade-history guessing."""
    pub = os.getenv(PUBLIC_KEY_ENV_NAME)
    r = safe_get("https://data-api.polymarket.com/positions",
                 {'user': pub, 'limit': 500, 'sortBy': 'CURRENT', 'sortDirection': 'DESC'})
    if r is None or r.status_code != 200:
        return (None, None)  # 🌙 None = "couldn't read", NOT "flat" — never fake a fill
    for p in r.json():
        if str(p.get('asset')) == str(token_id):
            return (float(p.get('size', 0) or 0), float(p.get('avgPrice', 0) or 0))
    return (0.0, 0.0)
```
Note that the whole order path is wrapped in try/except that logs and returns an empty dict instead of raising. A trading bot that crashes on a single failed order is a trading bot that stops trading. Fail the order, log it, keep the loop alive.

## Step 5: Market Data and the Liquidation Snapshot

Everything that reads the outside world goes through safe_get(), which swallows network exceptions and returns None. Every caller then treats None as "no answer this tick" rather than crashing. Over a 24-hour run you will absolutely hit DNS blips, TLS resets, and 502s; the bot should shrug and try again in three seconds.

The window math is elegantly simple. Polymarket 5-minute BTC markets are slugged btc-updown-5m-{T} where T is a unix timestamp floored to the nearest 300 seconds. So get_current_window_ts() is literally integer division, and you can compute the current market slug offline without querying anything. Gamma then translates that slug into the two CLOB token IDs, one for Up and one for Down.

One easy-to-miss detail in get_book(): the best bid is the **last** element of the bids array, not the first. Polymarket returns the book sorted ascending. Get that backwards and you will compute your 20% discount off the worst bid on the book instead of the best one, which quietly changes your strategy into something else entirely. Always print a book once and eyeball the ordering before you trust it.

And here is the signal source. fetch_liq_snapshot() hits the Moon Dev API positions endpoint with the API key header and gets back top-level longs / shorts lists: the 50 positions per side closest to liquidation across all coins, minimum $75k value, priced off a live websocket. Each row carries address, coin, value, entry price, current price, liq price, distance percent, leverage, size, and unrealized P&L. We filter to BTC only, compute the snapshot age from updated_at, and return None on any failure. Real data or no bet.

Blip-tolerant reads, the window slug, the book, and the liq feed

```python
# ============================================================================
# 🌙 MOON DEV - MARKET DATA (read, blip-tolerant)
# ============================================================================
def safe_get(url, params=None, timeout=10, headers=None):
    hdrs = {'User-Agent': 'Mozilla/5.0 (moondev)'}
    if headers:
        hdrs.update(headers)
    try:
        return requests.get(url, params=params, timeout=timeout, headers=hdrs)
    except requests.exceptions.RequestException as e:
        log_event(f"🌐 net blip: {type(e).__name__}", "yellow")
        return None

def get_current_window_ts():
    return (int(time.time()) // MARKET_DURATION) * MARKET_DURATION

def get_market_tokens(window_ts):
    """🌙 Moon Dev - btc-updown-5m-{T} -> {"Up": token, "Down": token} via Gamma."""
    slug = f"btc-updown-5m-{window_ts}"
    r = safe_get("https://gamma-api.polymarket.com/markets", {'slug': slug, 'closed': 'false', 'active': 'true'})
    if r is None or r.status_code != 200:
        return None
    mk = r.json()
    if not mk:
        return None
    m = mk[0]
    try:
        outcomes = json.loads(m.get('outcomes', '[]'))
        tokens = json.loads(m.get('clobTokenIds', '[]'))
    except (ValueError, TypeError):
        return None
    if len(outcomes) != len(tokens) or not tokens:
        return None
    return {"slug": slug, "by_outcome": {o: t for o, t in zip(outcomes, tokens)}}

def get_book(token_id):
    """🌙 Moon Dev - (best_bid, best_ask) for a token. Best = LAST array element."""
    r = safe_get("https://clob.polymarket.com/book", {'token_id': token_id}, timeout=5)
    if r is None or r.status_code != 200:
        return (None, None)
    d = r.json()
    bids, asks = d.get('bids', []), d.get('asks', [])
    return (float(bids[-1]['price']) if bids else None,
            float(asks[-1]['price']) if asks else None)

def get_btc_spot():
    """🌙 Moon Dev - Binance last (dashboard context only — the brain is the liq data)."""
    r = safe_get("https://api.binance.com/api/v3/ticker/price", {'symbol': 'BTCUSDT'})
    if r is not None and r.status_code == 200:
        p = r.json().get('price')
        if p:
            return float(p)
    return None

def fetch_liq_snapshot():
    """🌙 Moon Dev - THE SIGNAL SOURCE: api.moondev.com/api/positions.json.

    Live shape (verified 2026-07-29 by probing): TOP-LEVEL `longs` / `shorts`
    lists — the top 50 positions closest to liquidation per side, ALL coins,
    min value $75k, priced off a live websocket. Each row: address, coin,
    value, entry_price, current_price, liq_price, distance_pct, leverage,
    size, pnl. We keep coin == 'BTC' only. Returns None on any failure —
    real data or no bet, NEVER faked."""
    r = safe_get("https://api.moondev.com/api/positions.json",
                 headers={'X-API-Key': MOONDEV_API_KEY}, timeout=10)
    if r is None or r.status_code != 200:
        return None
    d = r.json()
    longs = [p for p in d.get('longs', []) if p.get('coin') == 'BTC']
    shorts = [p for p in d.get('shorts', []) if p.get('coin') == 'BTC']
    age = None
    try:
        upd = datetime.fromisoformat(d.get('updated_at', ''))
        age = (datetime.now(timezone.utc) - upd).total_seconds()
    except (ValueError, TypeError):
        pass
    return {"longs": longs, "shorts": shorts, "age_sec": age,
            "updated_at": d.get('updated_at', '')}

def _val(p):
    return float(p.get('value', 0) or 0)

def _dist(p):
    return float(p.get('distance_pct', 100) or 100)
```
Notice that BTC spot from Binance is fetched purely for the dashboard. The brain never looks at it. That is a deliberate discipline: if a number does not feed a decision, label it as decoration so nobody later mistakes it for signal.

## Step 6: The Brain (All Fifteen Lines of It)

Here is the entire decision engine. Sum the dollar value of the near-liq longs. Sum the dollar value of the near-liq shorts. Subtract. If longs are heavier, the fuel pile is below spot, so we bet Down. If shorts are heavier, the fuel is above, so we bet Up. If both are zero, there is no magnet and we skip.

You will look at that and think "surely you should weight by distance — a position 0.1% from liquidation matters more than one 8% away." You are probably right! That is Bot #2. And leverage weighting is Bot #3, and whale filtering is Bot #4. But **you cannot know whether a refinement helped unless you measured the unrefined version first.** Bot #1 exists to be the number that every other bot has to beat. Building the sophisticated version first and skipping the baseline is the single most common way quant projects fool themselves.

The function returns a three-tuple of side, score, and a human-readable why string. That third element is not decoration. It gets written to the eval CSV on every window, so when you are reading a thousand rows six weeks from now you can see the reasoning that produced each row rather than reverse-engineering it from the numbers. Make your bots explain themselves in writing.

decide() — raw near-liq value imbalance, the purest read

```python
# ============================================================================
# 🧲 MOON DEV - THE BRAIN (Bot #1: RAW VALUE IMBALANCE — the baseline)
# ============================================================================
def decide(snap):
    """🌙 Moon Dev - purest read of the magnet: total near-liq $ per side.
    More LONG value at risk -> forced sells below -> Down.
    More SHORT value at risk -> forced buys above -> Up.
    Returns (side, score, why). signal_score = long_val - short_val (USD)."""
    long_val = sum(_val(p) for p in snap["longs"])
    short_val = sum(_val(p) for p in snap["shorts"])
    score = long_val - short_val
    if long_val == 0 and short_val == 0:
        return (None, 0.0, "🚫 zero BTC near-liq value on both sides — no magnet")
    side = "Down" if score > 0 else "Up"
    heavier = "LONGS" if score > 0 else "SHORTS"
    why = (f"🧲 {heavier} heavier: longs ${long_val/1e6:.2f}M vs shorts ${short_val/1e6:.2f}M "
           f"-> magnet {'below' if side == 'Down' else 'above'} -> {side}")
    return (side, score, why)
```
signal_score is stored as a signed dollar amount rather than a boolean, which means later you can re-mine the log and ask "did the big imbalances perform differently from the marginal ones?" Always persist the magnitude, not just the direction.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hyperliquid-liquidation-magnet-bot)

## Step 7: Honest Resolution and the Kill Switch

This section is where most homemade bots quietly lie to their owners, so read it carefully. When a fill happens, the trade is written to CSV with result PENDING. It stays PENDING until the market has definitively resolved. Nothing is ever assumed.

get_definitive_winner() carries a hard-won correction: you **must** pass closed=true to the Gamma query. The default markets query excludes closed markets, so a resolved 5-minute market simply does not appear and your trade would sit PENDING forever while you wonder why. Then the second guard: we only call a winner when outcomePrices is exactly 1 and 0. A price of 0.98 means the market is settling, not settled. Anything ambiguous returns None, the trade stays PENDING, and the resolver tries again on the next loop — forever if it has to. A trade that never resolves is annoying. A trade that resolves *wrong* corrupts every statistic you will ever compute from that file.

The P&L math is binary-market simple. We paid our_bid * shares for shares shares. A winner pays $1.00 per share, so profit is shares minus cost. A loser pays zero, so the loss is the whole cost. Because we are always the maker, our_bid is exactly what we paid — no slippage reconstruction needed.

And then check_kill_switch(), my favorite twenty lines in the file. It reads only *resolved* trades, waits until there are at least 20 of them, takes the trailing 40, and averages the realized P&L per trade. If that average is worse than negative forty cents, it flips a flag and the bot stops entering. Not the day. Permanently, until you restart it and look at why. Notice what it does **not** judge on: win rate, signal strength, gut feel, or how good the last trade felt. Realized dollars per trade, nothing else.

CSV logging, definitive resolution, and the kill switch

```python
# ============================================================================
# 🌙 MOON DEV - CSV LOGGING
# ============================================================================
def append_csv(path, fields, row):
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)

def read_csv_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def write_csv_rows(path, fields, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def record_trade(st, window_ts, shares):
    """🌙 Moon Dev - the pullback filled us — enter the trades file as PENDING."""
    append_csv(TRADES_FILE, TRADE_FIELDS, {
        "timestamp": datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S"),
        "market_ts": window_ts, "slug": st["slug"], "side": st["side"],
        "signal_score": f"{st['score']:.0f}",
        "long_val": f"{st['long_val']:.0f}", "short_val": f"{st['short_val']:.0f}",
        "book_bid": f"{st['book_bid']:.4f}", "our_bid": f"{st['our_bid']:.4f}",
        "discount_pct": f"{DISCOUNT_PCT:.2f}",
        "shares": f"{shares:.2f}", "usd": f"{st['our_bid'] * shares:.2f}",
        "result": "PENDING", "resolved_winner": "", "pnl_usd": "",
        "paper": int(PAPER_MODE)})

# ============================================================================
# 🌙 MOON DEV - HONEST RESOLUTION (Gamma closed=true ONLY — the July 24 correction)
# ============================================================================
def get_definitive_winner(slug):
    """🌙 Moon Dev - closed=true is REQUIRED: a closed 5-min market is excluded
    from the default Gamma query and would sit PENDING forever without it.
    'Up'/'Down' only when outcomePrices are exactly 1/0 — None otherwise."""
    r = safe_get("https://gamma-api.polymarket.com/markets", {'slug': slug, 'closed': 'true'})
    if r is not None and r.status_code == 200 and r.json():
        try:
            prices = json.loads(r.json()[0].get('outcomePrices', '[]') or '[]')
        except (ValueError, TypeError):
            prices = []
        if len(prices) == 2:
            up = float(prices[0])
            if up == 1.0:
                return "Up"
            if up == 0.0:
                return "Down"
    return None

def resolve_pending_trades():
    """🌙 Moon Dev - stamp WIN/LOSS + P&L when definitive. PENDING is NEVER faked."""
    if not os.path.exists(TRADES_FILE):
        return
    rows = read_csv_rows(TRADES_FILE)
    changed = False
    for r in rows:
        if r["result"] != "PENDING":
            continue
        close_ts = int(r["market_ts"]) + MARKET_DURATION
        if time.time() < close_ts + RESOLVE_GRACE_SEC:
            continue
        winner = get_definitive_winner(r["slug"])
        if winner is None:
            continue  # stays PENDING, retried forever — never faked
        won = r["side"] == winner
        shares = float(r["shares"] or 0)
        cost = float(r["our_bid"]) * shares
        pnl = (shares - cost) if won else -cost
        r["result"] = "WIN" if won else "LOSS"
        r["resolved_winner"] = winner
        r["pnl_usd"] = f"{pnl:+.2f}"
        changed = True
        S["daily_pnl"] += pnl
        tag = "🏆 WON" if won else "💀 LOST"
        log_event(f"{tag} {r['side']} vs {winner} ${pnl:+.2f} {r['slug']}",
                  "green" if won else "red")
    if changed:
        write_csv_rows(TRADES_FILE, TRADE_FIELDS, rows)

def check_kill_switch():
    """🌙 Moon Dev - trailing avg realized P&L judges the bot, nothing else."""
    if S["killed"] or not os.path.exists(TRADES_FILE):
        return
    resolved = [r for r in read_csv_rows(TRADES_FILE) if r["result"] in ("WIN", "LOSS")]
    if len(resolved) < KILL_MIN_TRADES:
        return
    tail = resolved[-KILL_TRAILING:]
    avg = sum(float(r["pnl_usd"] or 0) for r in tail) / len(tail)
    if avg < KILL_AVG_PNL:
        S["killed"] = True
        log_event(f"🔫 KILL SWITCH: trailing-{len(tail)} avg P&L ${avg:+.2f} < ${KILL_AVG_PNL:.2f} "
                  f"— no more entries", "red")
```
A subtle design choice: the trades CSV is the source of truth for the kill switch, not an in-memory counter. That means the risk controls survive a restart, a crash, or a redeploy. In-memory risk state is not risk state.

## Step 8: The Engine — Decide Once, Rest the Bid, Log the Window

fresh_state() is a plain dict holding everything about the current five-minute window, rebuilt from scratch on every rollover. No stale flags leaking across windows, no partially-reset objects. If you have ever debugged a bot that placed two orders because a boolean did not get cleared, you will appreciate how much grief a single fresh dict per window saves.

finalize_window() writes exactly one eval row per window, whether we bet or skipped, and it also records the closest long and closest short distance percentages — data the brain did not use but future bots will. That is the whole point of the eval log: **collect more than you consume,** because you cannot go back in time and collect it later.

evaluate_and_place() is the ordered gauntlet. Bail if we already placed or already decided to skip. Bail if it is too early or the market is not discovered yet. Mark TOO_LATE if we blew past the floor. Then fetch the liq snapshot exactly once per window and immediately check its age against the stale guard. Then run the brain once and cache the decision — the bot commits to a side and does not flip-flop as the feed updates mid-window.

Then the hard rule in three lines of arithmetic. Read the chosen side's best bid, multiply by 0.80, and math.floor it down to the penny tick — floor rather than round, so rounding error always works in our favor. Clamp into the legal 0.01 to 0.99 range. Size the order in shares as USD divided by our price, floored to two decimals, with the Polymarket five-share minimum as a floor.

And notice where the kill switch and daily stop are checked: **after** the full decision and pricing, right before placing. That is deliberate. Even when halted, the bot still computes and logs what it would have done, tagged KILLED or HALTED. Your paper trail keeps running while your money stays parked, so you can see whether the thing recovered before you turn it back on.

Window state, the eval row, and the placement gauntlet

```python
# ============================================================================
# 🌙 MOON DEV - WINDOW STATE + EVAL LOG
# ============================================================================
def fresh_state():
    return {"slug": None, "tokens": None, "spot": None, "snap": None,
            "side": None, "score": 0.0, "long_val": 0.0, "short_val": 0.0,
            "why": "", "token_id": None, "book_bid": None, "our_bid": None,
            "placed": False, "filled": False, "shares": 0.0,
            "action": None, "last_fill_poll": 0.0, "decided": False}

def finalize_window(st, window_ts):
    """🌙 Moon Dev - one eval row per window (bets AND skips) — the re-mining dataset."""
    if st["slug"] is None:
        return  # market never discovered — nothing real to log
    snap = st["snap"] or {"longs": [], "shorts": [], "age_sec": None}
    closest_l = min((_dist(p) for p in snap["longs"]), default=None)
    closest_s = min((_dist(p) for p in snap["shorts"]), default=None)
    append_csv(EVAL_LOG, EVAL_FIELDS, {
        "timestamp": datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S"),
        "window_ts": window_ts, "slug": st["slug"],
        "spot": "" if st["spot"] is None else f"{st['spot']:.2f}",
        "liq_age_sec": "" if snap["age_sec"] is None else f"{snap['age_sec']:.0f}",
        "long_n": len(snap["longs"]), "long_val": f"{st['long_val']:.0f}",
        "short_n": len(snap["shorts"]), "short_val": f"{st['short_val']:.0f}",
        "closest_long_pct": "" if closest_l is None else f"{closest_l:.2f}",
        "closest_short_pct": "" if closest_s is None else f"{closest_s:.2f}",
        "signal_score": f"{st['score']:.0f}",
        "side": st["side"] or "",
        "book_bid": "" if st["book_bid"] is None else f"{st['book_bid']:.4f}",
        "our_bid": "" if st["our_bid"] is None else f"{st['our_bid']:.4f}",
        "action": st["action"] or "NO_ACTION", "why": st["why"],
        "paper": int(PAPER_MODE)})

# ============================================================================
# 🌙 MOON DEV - THE ENGINE: decide once, rest the 20%-under bid, wait
# ============================================================================
def evaluate_and_place(st, window_ts, time_left):
    """🌙 Moon Dev - one decision + one resting order per window."""
    if st["placed"] or st["decided"] and st["action"] in ("NO_LIQ_DATA", "NO_SIGNAL"):
        return
    if time_left > PLACE_AFTER or st["tokens"] is None:
        return
    if time_left < PLACE_FLOOR:
        if st["action"] is None:
            st["action"] = "TOO_LATE"
            st["why"] = f"⏰ couldn't get data + book before T-{PLACE_FLOOR}"
        return

    # ---- 1. fresh liq snapshot (once per window) ----
    if st["snap"] is None:
        snap = fetch_liq_snapshot()
        if snap is None:
            st["why"] = "waiting for Moon Dev liq data..."
            return
        if snap["age_sec"] is not None and snap["age_sec"] > LIQ_MAX_AGE_SEC:
            st["snap"] = snap
            st["decided"] = True
            st["action"] = "NO_LIQ_DATA"
            st["why"] = f"💀 liq snapshot is {snap['age_sec']:.0f}s stale (> {LIQ_MAX_AGE_SEC}s) — no bet on old data"
            S["no_data"] += 1
            log_event(st["why"], "yellow")
            return
        st["snap"] = snap
        st["long_val"] = sum(_val(p) for p in snap["longs"])
        st["short_val"] = sum(_val(p) for p in snap["shorts"])

    # ---- 2. the brain ----
    if not st["decided"]:
        side, score, why = decide(st["snap"])
        st["decided"] = True
        st["side"], st["score"], st["why"] = side, score, why
        if side is None:
            st["action"] = "NO_SIGNAL"
            S["no_data"] += 1
            log_event(why, "yellow")
            return
        st["token_id"] = st["tokens"].get(side)
        log_event(why, "cyan")

    # ---- 3. the hard rule: rest the maker bid 20% under the book bid ----
    if st["side"] is None or st["token_id"] is None:
        return
    bid, ask = get_book(st["token_id"])
    if bid is None:
        st["why"] = f"📖 {st['side']} book has no bid yet — retrying"
        return
    our_bid = math.floor(bid * (1 - DISCOUNT_PCT) * 100) / 100
    our_bid = max(0.01, min(our_bid, 0.99))
    st["book_bid"], st["our_bid"] = bid, our_bid
    shares = math.floor((USD_SIZE / our_bid) * 100) / 100
    shares = max(float(MIN_SHARES), shares)
    st["shares"] = shares

    if S["killed"] or S["halted"]:
        st["action"] = "KILLED" if S["killed"] else "HALTED"
        st["why"] = "🔫 kill switch" if S["killed"] else "🛑 daily stop — watching only"
        st["placed"] = True  # block re-entry attempts this window
        return

    st["placed"] = True
    st["action"] = "ORDER_PLACED"
    S["placed"] += 1
    if PAPER_MODE:
        log_event(f"📝 PAPER bid resting: {st['side']} @ ${our_bid:.2f} (book bid ${bid:.2f})", "magenta")
        return
    place_maker_buy(st["token_id"], our_bid, shares)
```
One order per window, one decision per window, one CSV row per window. That triple invariant is what makes the resulting dataset analyzable instead of a tangle.

## Step 9: The Pullback Watch

Once the bid is resting, the bot polls every three seconds and asks one question: *do we hold any of this token yet?* Not "did an order event fire," not "does the trade history show something." Position size is the ground truth, because it is the number that determines whether you actually own risk. Everything else is a derived opinion about the number.

Look at the guard: if held is not None and held > 0. That None check is the payoff from returning three states earlier. A failed read gives us None, None is not greater than zero, and the bot correctly concludes nothing yet and tries again. If position_for_token() had returned zero on a read failure, this line would look identical and behave identically — but the very next block, the T-20 cancel, would have fired on bad information.

At T-20 with no fill, we cancel the resting order, mark NO_FILL, and stop watching. This is the outcome the bot expects *most* of the time, and that is fine. A stink bid that does not fill costs nothing. The whole risk profile of this strategy is "many free misses, occasional cheap entries."

Paper mode simulates the fill the honest way: the paper bid fills only when the real book bid actually trades down through our resting price. It does not assume, it does not fudge, it watches the same book the live bot would have been filled by. If your paper mode is more generous than reality, your paper results are fiction.

watch_fill() — position size is the ground truth

```python
def watch_fill(st, window_ts, time_left):
    """🌙 Moon Dev - the pullback watch: position size is the ground truth.
    Cancel the unfilled bid at T-CANCEL_AT; a fill holds to resolution."""
    if not st["placed"] or st["filled"] or st["action"] in ("KILLED", "HALTED"):
        return
    now = time.time()

    if PAPER_MODE:
        # 🌙 paper fill = the book bid traded DOWN through our resting price
        bid, _ = get_book(st["token_id"]) if now - st["last_fill_poll"] >= FILL_POLL_SEC else (None, None)
        if bid is not None:
            st["last_fill_poll"] = now
            if bid <= st["our_bid"]:
                st["filled"] = True
                st["action"] = "FILLED"
                S["fills"] += 1
                record_trade(st, window_ts, st["shares"])
                log_event(f"📝 PAPER FILL {st['side']} @ ${st['our_bid']:.2f} x{st['shares']:.1f} — pullback hit!", "green")
        if time_left <= CANCEL_AT and not st["filled"]:
            st["action"] = "NO_FILL"
            st["filled"] = True  # stop watching
            S["no_fill"] += 1
            log_event("🚫 paper: pullback never came — NO_FILL", "yellow")
        return

    if now - st["last_fill_poll"] < FILL_POLL_SEC:
        return
    st["last_fill_poll"] = now
    held, avg = position_for_token(st["token_id"])
    if held is not None and held > 0:
        st["filled"] = True
        st["action"] = "FILLED"
        st["shares"] = held
        S["fills"] += 1
        record_trade(st, window_ts, held)
        log_event(f"⚡ PULLBACK FILLED! {st['side']} @ ${st['our_bid']:.2f} x{held:.1f} — holding to resolution", "green")
        return
    if time_left <= CANCEL_AT:
        cancel_token_orders(st["token_id"])
        st["action"] = "NO_FILL"
        st["filled"] = True  # stop watching
        S["no_fill"] += 1
        log_event(f"✂️ T-{CANCEL_AT}: pullback never came — bid cancelled, NO_FILL", "yellow")
```
The st["filled"] = True assignment on the NO_FILL path is a small trick: reusing the filled flag as a "done watching" flag keeps the state machine to one boolean instead of two. Simple, and the action string already records which of the two outcomes actually happened.

## Step 10: The Dashboard and the Main Loop

The terminal dashboard is not vanity. When a bot is live with your money, you want to glance at a screen and instantly know whether it is seeing the world correctly. The near-liq panel does that in three lines: two bars sized by dollar value, each labeled with which direction that side's liquidations would push price, plus the three closest positions per side shown as value at distance. If those bars are both empty or the age is huge, you know instantly that the problem is the feed, not the logic.

The near-liq panel — the signal, drawn (excerpt from draw())

```python
    snap = st["snap"]
    if snap:
        lv, sv = st["long_val"], st["short_val"]
        bar_l = int(min(lv, 3e8) / 3e8 * 24)
        bar_s = int(min(sv, 3e8) / 3e8 * 24)
        age_s = f"{snap['age_sec']:.0f}s" if snap["age_sec"] is not None else "?"
        print(colored(f"\n  💀 BTC NEAR-LIQ (top-50/side, ≥$75k, age {age_s}):", "white", attrs=['bold']))
        print(colored(f"     📈 LONGS  ${lv/1e6:>7.1f}M {'█' * bar_l}", "green") + colored("  (liqs BELOW → Down fuel)", "white"))
        print(colored(f"     📉 SHORTS ${sv/1e6:>7.1f}M {'█' * bar_s}", "red") + colored("  (liqs ABOVE → Up fuel)", "white"))
        for tag, lst, col in (("closest longs", snap["longs"], "green"), ("closest shorts", snap["shorts"], "red")):
            close3 = sorted(lst, key=_dist)[:3]
            if close3:
                line = "  ".join(f"${_val(p)/1e3:.0f}k@{_dist(p):.2f}%" for p in close3)
                print(colored(f"     {tag:<15}: {line}", col))
    else:
        print(colored(f"\n  💀 {next(SPINNER)} waiting for Moon Dev near-liq data...", "white"))
```
The main loop runs at roughly 3 Hz and is deliberately boring. Compute the window and time remaining. Roll the Eastern-time day and check the daily stop. Resolve anything pending and re-check the kill switch. On a window rollover, cancel any resting bid, then — and this part matters — **check the position one more time before writing the window off.** A maker order can fill in the final second, and if you cancel and immediately assume NO_FILL you will end up holding a position your bot does not believe in. The buzzer-fill check catches that.

Then discover the market, refresh spot for the display, run the placement gauntlet, run the fill watch, redraw twice a second, sleep 300 milliseconds, repeat. The outermost wrapper catches any unhandled exception, prints it, clears the cached client, and restarts the whole thing in three seconds. Bots die at 4am for stupid reasons; the ones that make money are the ones that get back up.

The main loop, the rollover buzzer-fill catch, and the crash wrapper

```python
# ============================================================================
# 🌙 MOON DEV - MAIN
# ============================================================================
def main():
    if not MOONDEV_API_KEY:
        print(colored("❌ Moon Dev - MOONDEV_API_KEY missing from .env — the liq data IS the bot. Exiting.", "red"))
        sys.exit(1)
    if not PAPER_MODE and (not os.getenv(PRIVATE_KEY_ENV_NAME) or not os.getenv(PUBLIC_KEY_ENV_NAME)):
        print(colored(f"❌ Missing {PRIVATE_KEY_ENV_NAME}/{PUBLIC_KEY_ENV_NAME} in .env", "red"))
        sys.exit(1)

    st = fresh_state()
    current_window = None
    last_draw = 0.0
    last_spot = 0.0
    log_event(f"{BOT_EMOJI} {BOT_NAME} spinning up" + (" (PAPER)" if PAPER_MODE else " — LIVE on AUG14"), "cyan")
    log_event(f"🪤 hard rule: maker bid {DISCOUNT_PCT:.0%} under the book bid, wait for the pullback", "cyan")

    while True:
        now = time.time()
        window_ts = get_current_window_ts()
        time_left = MARKET_DURATION - (int(now) - window_ts)

        # 🌙 daily stop-loss bookkeeping (ET day)
        today = datetime.now(ET).strftime("%Y-%m-%d")
        if S["day"] != today:
            S["day"] = today
            S["daily_pnl"] = 0.0
            S["halted"] = False
        if not S["halted"] and S["daily_pnl"] <= DAILY_STOP_LOSS:
            S["halted"] = True
            log_event(f"🛑 DAILY STOP {S['daily_pnl']:+.2f} <= {DAILY_STOP_LOSS} — no new entries today", "red")

        resolve_pending_trades()
        check_kill_switch()

        # 🌙 window rollover: cancel any resting bid, log the window, reset
        if window_ts != current_window:
            if current_window is not None:
                if not PAPER_MODE and st["placed"] and st["token_id"] and not st["filled"]:
                    cancel_token_orders(st["token_id"])
                    held, _ = position_for_token(st["token_id"])
                    if held is not None and held > 0:  # 🌙 late fill caught at the buzzer
                        st["action"] = "FILLED"
                        st["shares"] = held
                        S["fills"] += 1
                        record_trade(st, current_window, held)
                        log_event(f"⚡ buzzer fill caught: {st['side']} x{held:.1f}", "green")
                    elif st["action"] == "ORDER_PLACED":
                        st["action"] = "NO_FILL"
                        S["no_fill"] += 1
                finalize_window(st, current_window)
                st = fresh_state()
            current_window = window_ts
            log_event(f"🔄 new window {datetime.fromtimestamp(window_ts, ET).strftime('%H:%M')} ET", "magenta")

        # 🌙 discover market
        if st["tokens"] is None:
            info = get_market_tokens(window_ts)
            if info:
                st["tokens"] = info["by_outcome"]
                st["slug"] = info["slug"]

        # 🌙 spot (dashboard context)
        if now - last_spot >= 5.0:
            last_spot = now
            px = get_btc_spot()
            if px:
                st["spot"] = px

        evaluate_and_place(st, window_ts, time_left)
        watch_fill(st, window_ts, time_left)

        if now - last_draw >= 0.5:
            last_draw = now
            draw(st, time_left)
        time.sleep(0.3)

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    tag = "PAPER MODE" if PAPER_MODE else "LIVE on AUG14 (real money, $5)"
    print(colored(f"{BOT_EMOJI} Moon Dev's {BOT_NAME} — {tag}...", "cyan", attrs=['bold']))
    print(colored(f"🪤 rest a maker bid {DISCOUNT_PCT:.0%} under the book bid, wait for the pullback", "cyan"))
    print(colored(f"📒 trades: {TRADES_FILE}\n📒 eval:   {EVAL_LOG}", "cyan"))
    time.sleep(0.4)
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print()
            print(colored(f"  {BOT_EMOJI} MOON DEV — {BOT_NAME} STOPPED", "yellow", attrs=['bold']))
            print(colored(f"  🎯 orders {S['placed']}  fills {S['fills']}  day P&L ${S['daily_pnl']:+.2f}", "green", attrs=['bold']))
            print(colored(f"  💾 {TRADES_FILE}", "cyan"))
            print(colored("  🌙 Moon Dev out — the magnet never sleeps.", "magenta"))
            print()
            break
        except Exception as e:
            print(colored(f"  💥 crashed: {type(e).__name__}: {e} — restarting in 3s", "red", attrs=['bold']))
            _CLIENT_CACHE = None
            time.sleep(3)
```
Notice the loop resolves pending trades and checks the kill switch on *every* iteration, not just at rollover. Cheap operations, and it means a bad streak shuts the bot down within seconds of the trade that broke the threshold rather than at some later checkpoint.

## Putting It All Together

Zoom out and it is one idea wrapped in careful plumbing. The idea: **whichever side of Hyperliquid has more dollars near liquidation is the direction with more guaranteed forced flow,** so bet the 5-minute Polymarket window toward that fuel. The plumbing: one liq snapshot per window with a staleness guard, one decision, one maker-only bid resting 20% under the book, a three-second position poll to detect the fill, a cancel at T-20, resolution that requires a definitive 1/0 print, and two independent risk controls backed by the trades file on disk.

And it is one experiment out of five. Bot #1 is the raw read, Bots #2 through #4 add distance, leverage, and whale weighting, and Bot #5 fades the whole thesis as a control. The eval CSV from all of them is the actual deliverable — the trades are just how you pay for the data.

Keep the honest caveat in view the entire time. A resting bid 20% under the market fills precisely when price is running the other way, which means the bot is systematically buying into short-term momentum against its own call. That is real adverse selection and no amount of clever code removes it. The only question worth asking is whether the liq-magnet edge is bigger than that cost, and the only way to answer it is a few hundred logged windows.

## How to Run It

One pip install, one .env, one file. Your repo-root .env needs MOONDEV_API_KEY for the liquidation feed plus the wallet keys named by whatever ACCOUNT_SUFFIX points at — for the AUG14 account that is PRIVATE_KEY_AUG14 and PUBLIC_KEY_AUG14. Never hardcode those into the file and never paste them into a chat window.

Before you run the loop at all, run the self-test. It walks the entire read path against a real live window — finds the market, pulls the liq snapshot, runs the brain, reads the book, and prints the exact order it *would* have rested — and places absolutely nothing. If any part of your setup is wrong, this tells you in five seconds instead of five minutes into a live session.

selftest() — the full read path, zero orders placed

```python
# ============================================================================
# 🌙 MOON DEV - SELFTEST (live read-only smoke check — places NOTHING)
# ============================================================================
def selftest():
    """🌙 Moon Dev - read a real live window end to end and print the decision.
    NO ORDER IS EVER PLACED."""
    print(colored(f"\n  {BOT_EMOJI} 🌙 MOON DEV's {BOT_NAME} — LIVE READ-ONLY SMOKE CHECK {BOT_EMOJI}", "cyan", attrs=['bold']))
    print(colored("  (no order will be placed — read path only)\n", "yellow"))
    if not MOONDEV_API_KEY:
        print(colored("  ❌ MOONDEV_API_KEY missing from .env", "red"))
        return
    window_ts = get_current_window_ts()
    time_left = MARKET_DURATION - (int(time.time()) - window_ts)
    print(colored(f"  window     : btc-updown-5m-{window_ts}  "
                  f"({datetime.fromtimestamp(window_ts, ET).strftime('%H:%M')} ET)  time_left {time_left}s", "white"))
    info = get_market_tokens(window_ts)
    if not info:
        print(colored("  ❌ market not found on Gamma yet", "red"))
        return
    print(colored(f"  slug       : {info['slug']}", "white"))
    snap = fetch_liq_snapshot()
    if snap is None:
        print(colored("  ❌ Moon Dev positions.json unreachable", "red"))
        return
    lv = sum(_val(p) for p in snap["longs"])
    sv = sum(_val(p) for p in snap["shorts"])
    age_s = f"{snap['age_sec']:.0f}s" if snap["age_sec"] is not None else "?"
    print(colored(f"  liq data   : {len(snap['longs'])} BTC longs (${lv/1e6:.2f}M) | "
                  f"{len(snap['shorts'])} BTC shorts (${sv/1e6:.2f}M) | age {age_s}", "cyan"))
    side, score, why = decide(snap)
    print(colored(f"  BRAIN      : {why}", "magenta", attrs=['bold']))
    if side is None:
        print(colored("  DECISION   : NO_SIGNAL — would skip this window", "yellow", attrs=['bold']))
        return
    token_id = info["by_outcome"].get(side)
    bid, ask = get_book(token_id)
    print(colored(f"  {side} book   : bid {bid}  ask {ask}", "white"))
    if bid is None:
        print(colored("  ❌ no bid on the book yet", "yellow"))
        return
    our_bid = max(0.01, min(math.floor(bid * (1 - DISCOUNT_PCT) * 100) / 100, 0.99))
    shares = max(float(MIN_SHARES), math.floor((USD_SIZE / our_bid) * 100) / 100)
    print(colored(f"\n  WOULD REST : maker BUY {side} {shares:.2f} sh @ ${our_bid:.2f} "
                  f"({DISCOUNT_PCT:.0%} under the ${bid:.2f} bid, GTC post_only)", "green", attrs=['bold']))
    print(colored(f"  WOULD WAIT : for the pullback, cancel at T-{CANCEL_AT}, hold fills to resolution", "white"))
    print(colored(f"\n  ✅ read path OK — NOTHING WAS PLACED. 🌙 Moon Dev out.\n", "green", attrs=['bold']))
```
Run it

```python
# 1) The one and only pip dependency
pip install py_clob_client_v2

# 2) Repo-root .env must contain (names only, never commit values):
#    MOONDEV_API_KEY=...
#    PRIVATE_KEY_AUG14=...
#    PUBLIC_KEY_AUG14=...

# 3) Read-only smoke check first. Places nothing.
python liq_magnet.py --selftest

# 4) PAPER FIRST. Open the file, set PAPER_MODE = True, let it run.
python liq_magnet.py

# 5) When the eval CSV convinces you, flip PAPER_MODE = False.
#    Ctrl+C to stop. data/liq_magnet_eval.csv is the real deliverable.
```
Start in paper mode with USD_SIZE = 5 and leave it there for at least a day. Then open data/liq_magnet_eval.csv and check the thing that actually matters: how often did the pullback come, and when it did, which way did the window resolve? If the fills are systematically losing, you have measured the adverse selection and the answer is no. That is a successful experiment too.

## Go Build Your Own Edge

Please do not just run this bot. Copy-pasting somebody else's strategy and hoping is the fastest way to donate money. What is actually worth taking from this file is the process: **state your thesis in writing, state its weakness in writing, build the dumbest version first, log every window including the skips, resolve honestly, and put a kill switch under the whole thing.** That process transfers to every strategy you will ever build. The specific liquidation-imbalance read is just this week's expression of it.

Fork it and try the refinements yourself — weight by distance to liquidation, weight by leverage, filter to whales only, or flip the sign entirely and see if fading the magnet does better. Then come tell the Moon Dev community what the numbers said. Built with love by Moon Dev 🌙

## Want to build trading bots with Moon Dev?

Join the community, get the full code from every video, and learn algorithmic trading, quantitative finance, and how to actually automate your trading.

[Explore the Roadmap](https://moondev.com/roadmap)

## Related Moon Dev Builds

[

### Polymarket × Hyperliquid Stat Arb

Another cross-venue edge built on Hyperliquid liquidation data.

[

### Strike-Cross Sniper

The taker cousin — crosses the spread when spot has already left the strike behind.

[

### Polymarket 95¢ Bid Sniper

The other maker-only build — same post-only discipline, different edge.

[

### Full Code-From-Videos Roadmap

Every open-source trading bot walkthrough in one place.

Built with love by Moon Dev 🌙
