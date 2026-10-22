<!-- source: https://moondev.com/polymarket-95-cent-bid-sniper -->
<!-- captured: 2026-10-07 -->
<!-- title: Polymarket 95-Cent Bid Sniper -->

Polymarket 95¢ Bid Sniper | Patient Maker Trading Bot | Algorithmic Trading | Moon Dev

Moon Dev Open Source

# Polymarket 95¢ Bid Sniper: A Patient, Maker-Only Trading Bot

A Python trading bot that waits until the last 60 seconds of a Polymarket BTC 5-minute market, finds the side that is already *decided* (ask ≥ $0.95), and rests a post-only limit on the bid — never paying more than 95¢. Every fill locks in roughly +5.3%.

By Moon Dev · June 7, 2026

## Why This Bot Exists

The first version of this idea was the **5-minute buzzer beater**. That bot waited for the last minute of a Polymarket 5-minute UP/DOWN market, found whichever side was "favored" (ask ≥ $0.70), and chased the ask as an aggressive taker. The logic sounded clean. The results were not. 70¢ is not decided — it is still very much a coin flip, and chasing the ask means paying spread plus fees on every single entry. Moon Dev got wrecked.

This rewrite fixes both mistakes at once. First, the threshold moves up to **0.95**. At 95¢, the market has essentially already resolved — the orderbook has called it. Second, the bot never takes. It places a **post-only** limit order that rests on the bid. The exchange will reject the order if it would cross the book and take liquidity. That means the bot can only ever be a maker — sitting, waiting, getting filled if someone hits it.

Cap the bid at 95¢ and the math is automatic: 1.00 / 0.95 − 1 = **+5.26% per win**. We are not trying to predict BTC. We are trying to harvest 5% every 5 minutes from markets the crowd has already decided. Let's walk through how it works.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-95-cent-bid-sniper)

## Step 1: The Header, the Story, and a Self-Healing Python Shebang

Every Moon Dev bot starts with a fat docstring that tells you exactly what the bot does, why it exists, and what mistake it is trying to avoid. This is not just documentation — it is the contract. If a future-you reads this header, you should immediately know whether this is the right tool for the job.

Right after the imports there is a small self-healing trick: if the script is launched with the wrong Python interpreter, it re-execs itself with the correct conda environment. This is a sneaky-good ergonomic win — no more "ModuleNotFoundError: py_clob_client_v2" because you forgot to conda activate tflow. The bot just fixes it for you.

Docstring + auto re-exec into the correct env

```python
#!/opt/anaconda3/envs/tflow/bin/python
"""
================================================================================
MOON DEV's 5-MINUTE 95¢ BID SNIPER v1.0  (AUG14 account)
================================================================================
A patient, last-60-second entry bot for BTC 5-minute UP/DOWN markets.

STRATEGY (the whole thing in 5 lines):
  - Wait until <= 60 seconds left in the current 5-min market.
  - Find the side whose ask >= 0.95 (the market has basically already decided).
  - Rest a BUY limit on the bid: price = min(best_bid, 0.95). Never above 0.95.
  - Re-place every few seconds to stay on the bid. Stand down if the side stops
    being decided (ask drops < 0.95). One fill per market, then hold to expiry.
  - 95c -> 100c = 5.26% per win. We just want 5% every 5 minutes.

Built by Moon Dev
================================================================================
"""

import sys
import os
import time
import random
import itertools
from collections import deque
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from termcolor import colored

# Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)
```
os.execv replaces the current process image — the running Python — with a new one. By the time the next line executes, you are inside the right environment with all your dependencies available.

## Step 2: Multi-Account Configuration

Moon Dev runs multiple Polymarket wallets in parallel — the OG account plus several Gnosis Safe sub-accounts (AUG14, MAY13, FEB19, etc.). Each one has its own PRIVATE_KEY_*, PUBLIC_KEY_*, and API credentials in the .env. To switch which wallet a bot runs against, you only change one variable.

One important Polymarket gotcha: the OG account uses signature_type=1 (browser wallet), but every Gnosis Safe sub-account uses signature_type=2. Get this wrong and every signed order will be rejected. The line that computes SIGNATURE_TYPE just toggles based on whether the suffix is empty or not.

Account selection (this bot = AUG14)

```python
# PATH / ENV SETUP
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples'))
from nice_funcs import calculate_shares, get_token_id

# ACCOUNT CONFIGURATION (this bot = AUG14)
# "" = OG account (signature_type=1)
# "_AUG14", "_MAY13", "_FEB19", etc. = other wallets (signature_type=2 / Gnosis Safe)
ACCOUNT_SUFFIX = "_AUG14"

PRIVATE_KEY_ENV_NAME = f"PRIVATE_KEY{ACCOUNT_SUFFIX}"
PUBLIC_KEY_ENV_NAME = f"PUBLIC_KEY{ACCOUNT_SUFFIX}"
API_KEY_ENV_NAME = f"API_KEY{ACCOUNT_SUFFIX}"
API_SECRET_ENV_NAME = f"API_SECRET{ACCOUNT_SUFFIX}" if ACCOUNT_SUFFIX else "SECRET"
PASSPHRASE_ENV_NAME = f"PASSPHRASE{ACCOUNT_SUFFIX}"

# OG uses signature_type=1, every other sub-account uses 2 (Gnosis Safe)
SIGNATURE_TYPE = 1 if ACCOUNT_SUFFIX == "" else 2
```
Building env-var names dynamically with f-strings (f"PRIVATE_KEY{ACCOUNT_SUFFIX}") means you can clone this file for a new wallet by changing exactly one line. That is the whole point of the multi-account scaffold.

## Step 3: The Strategy Knobs (and the Math)

Every parameter that defines the strategy lives in one block at the top. ENTRY_THRESHOLD = 0.95 is the floor for what counts as "decided." MAX_BUY_PRICE = 0.95 is the hard ceiling on what we will ever bid. These are intentionally the same number — they enforce the same rule from two directions.

The time-based knobs say: do nothing until there are 60 seconds left in the market (ENTRY_WINDOW_SEC), and stop trying / cancel any resting order with 5 seconds left (STOP_THRESHOLD_SEC) so we don't end up holding a half-filled order into expiry. The bot re-evaluates its bid every 3 seconds, and considers a bid "already at target" if it's within half a cent.

One non-obvious gotcha at the bottom of the block: Polymarket enforces a **5-share minimum** per order. At 95¢ a share, that's a $4.75 floor — so even though BET_SIZE_USD = 1.0, the actual minimum entry is closer to $5. You can't bet smaller than that on Polymarket.

Strategy parameters

```python
# STRATEGY CONFIGURATION
BET_SIZE_USD = 1.0           # Bet per market (NOTE: 5-share min => ~$4.75 floor at 95c)
ENTRY_THRESHOLD = 0.95       # A side must have ask >= this to count as "decided"
MAX_BUY_PRICE = 0.95         # NEVER bid above this — guarantees >= ~5.3% / win
ENTRY_WINDOW_SEC = 60        # Only act in the last 60 seconds (decided by then)
STOP_THRESHOLD_SEC = 5       # Stop placing / cancel any resting order at this point
ORDER_UPDATE_INTERVAL = 3    # Re-evaluate our resting bid every X seconds
PRICE_HOLD_TOLERANCE = 0.005 # If our resting price is within this of target, don't re-place

MARKET_DURATION = 300        # 5-minute markets
ET = timezone(timedelta(hours=-5))

# Implied gain at the cap, for display
TARGET_GAIN_PCT = (1.0 / MAX_BUY_PRICE - 1.0) * 100.0  # 0.95 -> ~5.26%
```
The line that computes TARGET_GAIN_PCT is more than display sugar — it's the whole edge of the strategy expressed as a single arithmetic. Move the cap to 0.97 and the gain drops to ~3.1%. Move it to 0.90 and you get +11.1% per win but far fewer markets qualify. The cap is the dial.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-95-cent-bid-sniper)

## Step 4: The Polymarket CLOB V2 Client

Polymarket migrated their Python SDK from py_clob_client to py_clob_client_v2. The old SDK now throws PolyApiException on post_order — that single change broke a lot of old bots. If your entries are silently failing, this is the first thing to check.

The builder is wrapped in a module-level _CLIENT_CACHE so the heavy signing setup only happens once per process. It also handles a real-world env-var quirk: AUG14's API secret is stored as SECRET_AUG14, not API_SECRET_AUG14, so the fallback chain tries both. Little things like this are what separates a bot that runs in production from one that runs in a tutorial.

Account-aware CLOB V2 client

```python
_CLIENT_CACHE = None

def _build_client():
    """Build (and cache) a CLOB V2 client for the configured account.

    Polymarket migrated to the V2 SDK (py_clob_client_v2). The old V1 SDK throws
    PolyApiException on post_order now — that's the bug that was killing entries.
    """
    global _CLIENT_CACHE
    if _CLIENT_CACHE is not None:
        return _CLIENT_CACHE

    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import ApiCreds
    from py_clob_client_v2.constants import POLYGON
    from web3 import Web3

    key = os.getenv(PRIVATE_KEY_ENV_NAME)
    browser_address = os.getenv(PUBLIC_KEY_ENV_NAME)

    if not key or not browser_address:
        print(colored(
            f"Missing {PRIVATE_KEY_ENV_NAME} or {PUBLIC_KEY_ENV_NAME} in .env!",
            "red",
        ))
        sys.exit(1)

    try:
        browser_wallet = Web3.toChecksumAddress(browser_address)
    except AttributeError:
        browser_wallet = Web3.to_checksum_address(browser_address)

    client = ClobClient(
        host="https://clob.polymarket.com",
        chain_id=POLYGON,
        key=key,
        signature_type=SIGNATURE_TYPE,
        funder=browser_wallet,
    )

    api_key = os.getenv(API_KEY_ENV_NAME)
    # AUG14's secret lives in SECRET_AUG14 (not API_SECRET_AUG14).
    api_secret = (
        os.getenv(API_SECRET_ENV_NAME)
        or os.getenv(f"SECRET{ACCOUNT_SUFFIX}")
        or os.getenv("SECRET")
    )
    passphrase = os.getenv(PASSPHRASE_ENV_NAME)

    if api_key and api_secret and passphrase:
        creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=passphrase)
        client.set_api_creds(creds=creds)
    else:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds=creds)

    _CLIENT_CACHE = client
    return client
```
The Web3.toChecksumAddress / to_checksum_address try/except handles a web3.py API rename between versions. Both names point to the same function — the address-format-normalization step that Polymarket requires for the funder wallet.

## Step 5: The Two Core Order Functions

These two functions are the spine of the bot. place_limit_order creates a **post-only** resting BUY. The post_only=True flag is the exchange-enforced version of Moon Dev's "never take liquidity" rule — if the limit would cross the book, the API rejects it. The bot literally cannot turn into an aggressive taker, even by accident.

get_order_status_for_id is the partner function. It asks the exchange "what happened to this exact order ID?" and returns a normalized dict. The retry loop with backoff handles transient 5xx errors, and the sentinel return value "ERROR" tells the caller "don't make decisions right now — the exchange is flaky." That sentinel is critical for the anti-duplicate flow you'll see in the main loop.

Notice the timeout-handling block in place_limit_order: if the HTTP request times out, the order may or may not have actually landed on the book. Rather than guessing, we mark it as 'timeout-assumed-live' and lock the market for the rest of this 5-minute window. Better to skip one entry than double up by accident.

get_order_status_for_id — authoritative status check

```python
def get_order_status_for_id(order_id):
    """
    Authoritative order status check by orderID.
    Returns dict {status, size_matched, original_size, price, is_filled},
    None if not ours/queryable, or "ERROR" sentinel if the API is down.
    """
    if not order_id or order_id == 'timeout-assumed-live':
        return None
    client = _build_client()
    for attempt in range(3):
        try:
            order = client.get_order(order_id)
            if not order:
                return {
                    'status': 'NOT_FOUND',
                    'size_matched': 0.0,
                    'original_size': 0.0,
                    'price': 0.0,
                    'is_filled': False,
                }
            if isinstance(order, dict):
                size_matched = float(order.get('size_matched', 0) or 0)
                original_size = float(order.get('original_size', 0) or 0)
                status = str(order.get('status', 'unknown'))
                price = float(order.get('price', 0) or 0)
            else:
                size_matched = float(getattr(order, 'size_matched', 0) or 0)
                original_size = float(getattr(order, 'original_size', 0) or 0)
                status = str(getattr(order, 'status', 'unknown'))
                price = float(getattr(order, 'price', 0) or 0)
            return {
                'status': status.upper(),
                'size_matched': size_matched,
                'original_size': original_size,
                'price': price,
                'is_filled': size_matched > 0,
            }
        except Exception as e:
            err = str(e)
            if any(code in err for code in ['500', '502', '503', '504', 'timeout', 'Timeout']):
                time.sleep(0.5 * (attempt + 1))
                continue
            log_event(f"get_order failed: {type(e).__name__}", "yellow")
            return "ERROR"
    return "ERROR"
```
place_limit_order — POST-ONLY (maker only)

```python
def place_limit_order(token_id, side, price, size, neg_risk=False):
    """Place a POST-ONLY limit order (CLOB V2 SDK).

    post_only=True makes this maker-only: the API REJECTS it if it would cross the
    book and take. That's Moon Dev's "never market order, sit on the bid" rule
    enforced at the exchange — we can only ever rest, never sweep.
    """
    from py_clob_client_v2.clob_types import OrderArgs, OrderType, PartialCreateOrderOptions

    client = _build_client()

    order_args = OrderArgs(
        token_id=str(token_id),
        price=float(price),
        size=float(size),
        side=side.upper(),
    )

    log_event(f"Resting {side} @ ${price:.4f} x {size} shares (post-only)", "cyan")

    options = PartialCreateOrderOptions(neg_risk=True) if neg_risk else None

    try:
        response = client.create_and_post_order(
            order_args,
            options=options,
            order_type=OrderType.GTC,
            post_only=True,
        )
        if response and (response.get('orderID') or response.get('success')):
            oid = response.get('orderID', '')
            log_event(f"Order LIVE — id {str(oid)[:10]}...", "green")
            return response
        log_event(f"Order rejected: {response}", "red")
        return response if response else {}
    except Exception as e:
        err = str(e)
        if 'Request exception' in err or 'Duplicated' in err or 'ReadTimeout' in err or 'timeout' in err.lower():
            log_event("post_order timed out — assuming it landed", "yellow")
            return {'orderID': 'timeout-assumed-live', 'status': 'LIVE'}
        log_event(f"post_order failed: {type(e).__name__}: {e}", "red")
        return {}

def cancel_token_orders_acct(token_id):
    """Cancel all orders for a token on the configured account (V2)."""
    from py_clob_client_v2.clob_types import OrderMarketCancelParams
    client = _build_client()
    try:
        client.cancel_market_orders(OrderMarketCancelParams(asset_id=str(token_id)))
        log_event(f"Cancelled orders on {str(token_id)[:10]}...", "yellow")
        return True
    except Exception as e:
        log_event(f"Cancel failed: {type(e).__name__}: {e}", "yellow")
        return False
```
OrderType.GTC means "good til cancelled" — the order stays on the book until it fills, expires with the market, or we explicitly cancel it. Combined with post_only=True, this is the textbook maker order.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-95-cent-bid-sniper)

## Step 6: Market Data — Books, Timestamps, and Positions

Polymarket BTC 5-minute markets are perfectly aligned to wall-clock time. Every market starts at a UNIX timestamp divisible by 300 (5 × 60 seconds), so finding the "current" market is just integer division. The slug is always btc-updown-5m-{timestamp}. No search required — just compute it.

The orderbook helper has one easy-to-miss subtlety: Polymarket returns **both bids and asks sorted worst-to-best**. That means bids[-1] is the highest bid (best for sellers), and asks[-1] is the lowest ask (best for buyers). Get this index wrong and your bot will think the book is much tighter than it actually is.

position_shares_for_token is our fill-detection short-circuit. The Polymarket data API tells us exactly how many shares of a given token this wallet currently holds. If that number is > 0, we're in — no need to chase the orderID through get_order.

Market data helpers

```python
def get_current_market_timestamp():
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    return MARKET_DURATION - (int(time.time()) - market_ts)

def get_order_book(token_id):
    """Best bid/ask from Polymarket CLOB."""
    response = requests.get(
        "https://clob.polymarket.com/book",
        params={'token_id': token_id},
        timeout=10,
    )
    if response.status_code != 200:
        return None
    data = response.json()
    bids = data.get('bids', [])
    asks = data.get('asks', [])
    if not bids or not asks:
        return None
    # Polymarket returns BOTH bids and asks sorted worst->best.
    # So bids[-1] = highest bid = best bid, and asks[-1] = lowest ask = best ask.
    return {
        'best_bid': float(bids[-1]['price']),
        'best_ask': float(asks[-1]['price']),
    }

def get_market_info(market_ts):
    """Resolve the btc-updown-5m market for this timestamp."""
    market_slug = f"btc-updown-5m-{market_ts}"
    response = requests.get(
        "https://gamma-api.polymarket.com/markets",
        params={'slug': market_slug, 'closed': 'false', 'active': 'true'},
        timeout=10,
    )
    if response.status_code != 200:
        return None
    markets = response.json()
    if not markets:
        return None

    market = markets[0]
    token_data = get_token_id(market['id'])
    if len(token_data) != 3:
        return None

    return {
        'market_id': market['id'],
        'up_token_id': token_data[1],
        'down_token_id': token_data[2],
        'question': market['question'],
        'slug': market_slug,
        'neg_risk': market.get('negRisk', False),
    }

def position_shares_for_token(token_id):
    """How many shares do we hold of token_id on THIS account."""
    user_address = os.getenv(PUBLIC_KEY_ENV_NAME)
    if not user_address:
        return 0.0
    try:
        resp = requests.get(
            "https://data-api.polymarket.com/positions",
            params={'user': user_address, 'limit': 500, 'sortBy': 'CURRENT', 'sortDirection': 'DESC'},
            timeout=8,
        )
        if resp.status_code != 200:
            return 0.0
        for pos in resp.json():
            if str(pos.get('asset')) == str(token_id):
                size = float(pos.get('size', 0) or 0)
                if size > 0:
                    return size
        return 0.0
    except Exception as e:
        log_event(f"positions fetch failed: {e}", "yellow")
        return 0.0
```
We have two independent fill-detection paths: the positions API and get_order_status_for_id. The positions API is authoritative when it's caught up, but it can lag by a second or two. The orderID check is immediate but requires us to still have the orderID in hand. Belt and suspenders.

## Step 7: Pick the Decided Side, Compute the Bid Target

These two functions are tiny but they are the whole strategy. pick_decided_side looks at both UP and DOWN books and returns the side whose ask is at or above 0.95 — or (None, None) if neither qualifies. That early return is what keeps the bot patient: if no side is decided yet, we simply don't act. We never lower our standards.

compute_bid_target answers the question "where should we rest?" The answer: min(best_bid, 0.95). If the bid is at 0.92, we rest at 0.92 (try to get a better fill). If the bid spiked to 0.97, we rest at 0.95 (refuse to chase). And if the side stopped being decided mid-flight — say the ask dropped back to 0.93 — we return None and the caller stands down. This is exactly the 70¢ trap from the old buzzer-beater, and we refuse to fall into it.

The whole strategy in two functions

```python
def pick_decided_side(up_book, down_book):
    """
    Pick the side the market has ALREADY decided.
    A side qualifies only when its best_ask >= ENTRY_THRESHOLD (0.95).
    Returns ("UP"|"DOWN", book) or (None, None). If both somehow qualify
    (shouldn't at 0.95), take the higher ask.
    """
    up_ask = up_book['best_ask'] if up_book else None
    down_ask = down_book['best_ask'] if down_book else None

    up_qualifies = up_ask is not None and up_ask >= ENTRY_THRESHOLD
    down_qualifies = down_ask is not None and down_ask >= ENTRY_THRESHOLD

    if up_qualifies and down_qualifies:
        return ("UP", up_book) if up_ask >= down_ask else ("DOWN", down_book)
    if up_qualifies:
        return "UP", up_book
    if down_qualifies:
        return "DOWN", down_book
    return None, None

def compute_bid_target(favored_book):
    """
    Where to rest our passive BUY.
    We SIT ON THE BID but never pay above MAX_BUY_PRICE (0.95) so every win is
    >= ~5.3%. If the side is no longer decided (ask dropped < ENTRY_THRESHOLD),
    return None => stand down (do NOT buy a market that's no longer decided —
    this is exactly the 70c trap we're avoiding).
    """
    if not favored_book:
        return None
    if favored_book['best_ask'] < ENTRY_THRESHOLD:
        return None
    target = min(favored_book['best_bid'], MAX_BUY_PRICE)
    return round(target, 3)
```
These eight lines of real logic encode the entire thesis. Everything else in the bot — the loop, the dashboard, the verification flow — exists to execute these two functions safely, repeatedly, and without double-firing.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-95-cent-bid-sniper)

## Step 8: The Main Loop and the Anti-Duplicate Order Flow

The main loop runs every ~0.2 seconds. Each tick it: refreshes the orderbook (every 2s), checks the clock, and — if we are inside the 60-to-5-second snipe window — runs the trading logic. Outside that window, the bot just draws the dashboard and waits.

The part that took the most engineering is the **anti-duplicate verification flow**. The naive version of this bot would do something like "cancel old order, place new order" on every tick. But network requests can race: a cancel might be in-flight while a fill is happening, or a post_order might time out without us knowing whether it landed. Place a second order in any of those windows and you can end up with two live bids — and if the market closes with both filled, you just doubled your bet without meaning to.

The rule the bot enforces: **never place a new order unless the previous one is proven non-live.** Proof comes from one of three sources — the positions API says we hold shares (filled), get_order says CANCELED/NOT_FOUND, or we explicitly cancelled and re-verified. If any of those checks return ERROR or null, the bot *refuses to place*. A skipped entry is recoverable; a duplicate entry is not.

Special case: a 'timeout-assumed-live' order locks the market entirely. We can't verify it (we don't have an orderID), so the bot treats the market as "entered" for the rest of this window and stands down. You might miss one fill; you will never accidentally place two.

Main loop — book refresh, snipe window, verification flow

```python
def _place_fresh_bid(state, token_id, target_price):
    """Place a fresh resting BUY on the bid. Updates state tracking."""
    global SESSION_ATTEMPTS
    shares = calculate_shares(BET_SIZE_USD, target_price)
    if shares <= 0:
        return
    SESSION_ATTEMPTS += 1
    resp = place_limit_order(token_id, "BUY", target_price, shares, neg_risk=state['neg_risk'])
    if resp:
        oid = resp.get('orderID')
        if oid and oid != 'timeout-assumed-live':
            state['last_order_id'] = oid
            state['last_order_price'] = target_price
            state['open_order_price'] = target_price
        elif oid == 'timeout-assumed-live':
            state['last_order_id'] = 'timeout-assumed-live'
            state['last_order_price'] = target_price
            state['open_order_price'] = target_price

# Inside main() — the trading block (only runs in the snipe window)
if (
    state['market_info']
    and not state['entered']
    and time_left <= ENTRY_WINDOW_SEC
    and time_left > STOP_THRESHOLD_SEC
    and up_book
    and down_book
    and now - state['last_order_update'] >= ORDER_UPDATE_INTERVAL
):
    state['last_order_update'] = now

    # Lock on the decided side the first time one appears
    if state['favored_side'] is None:
        side, book = pick_decided_side(up_book, down_book)
        if side is not None:
            state['favored_side'] = side
            state['favored_token_id'] = (
                state['market_info']['up_token_id'] if side == "UP"
                else state['market_info']['down_token_id']
            )

    if state['favored_side'] is not None:
        token_id = state['favored_token_id']
        favored_book = up_book if state['favored_side'] == "UP" else down_book

        # Short-circuit: positions API (definitive when it catches up)
        shares_held = position_shares_for_token(token_id)
        if shares_held > 0:
            state['entered'] = True
            state['entry_fill_price'] = state['last_order_price'] or 0.0
            SESSION_ENTRIES += 1

        elif state['last_order_id'] == 'timeout-assumed-live':
            # Can't verify — lock the market, refuse new orders.
            state['entered'] = True
            state['entry_fill_price'] = state['last_order_price'] or 0.0

        elif state['last_order_id'] is not None:
            status_info = get_order_status_for_id(state['last_order_id'])

            if status_info == "ERROR" or status_info is None:
                # API can't confirm — refuse to place another order.
                pass

            elif status_info['is_filled']:
                state['entered'] = True
                state['entry_fill_price'] = status_info['price'] or 0.0
                SESSION_ENTRIES += 1

            elif status_info['status'] == 'LIVE':
                existing_price = status_info['price'] or state['last_order_price']
                target_price = compute_bid_target(favored_book)

                if target_price is None:
                    # Side no longer decided — cancel and stand down.
                    cancel_token_orders_acct(token_id)
                    state['last_order_id'] = None
                elif abs(existing_price - target_price) > PRICE_HOLD_TOLERANCE:
                    # Bid moved — cancel, re-verify, then place.
                    cancel_token_orders_acct(token_id)
                    time.sleep(1.5)
                    post_info = get_order_status_for_id(state['last_order_id'])
                    if post_info and post_info.get('status') in ('CANCELED', 'CANCELLED', 'NOT_FOUND'):
                        state['last_order_id'] = None
                        _place_fresh_bid(state, token_id, target_price)
                    # else: cancel didn't settle, hold off

            elif status_info['status'] in ('CANCELED', 'CANCELLED', 'NOT_FOUND'):
                state['last_order_id'] = None

        else:
            # No previous order this market — fresh placement
            target_price = compute_bid_target(favored_book)
            if target_price is not None:
                _place_fresh_bid(state, token_id, target_price)
```
This is the abridged trading block — the real file has more logging and edge-case handling, but the shape is identical. Every branch ends in either "we placed a single order" or "we placed nothing." There is no branch that can place two.

## Step 9: Market Rollover and the Final-Five-Seconds Stand-Down

At the top of every loop tick, the bot computes the current market timestamp. If that timestamp doesn't match the one we've been tracking, a new 5-minute market has started — we cancel any leftover orders, reset all the per-market state, and look up the new market's info (retrying up to 8 times in case the Gamma API hasn't indexed it yet).

At the bottom of the tick, the inverse: if we're past the 5-second stop threshold and still haven't filled, we kill any resting bid. We don't want a stray order hanging around when the market resolves — it could fill at the worst possible moment with no time to react.

Rollover at the top, stand-down at the bottom

```python
# Market rollover — new 5-minute market started
if market_ts != state['market_ts']:
    if state['last_order_id'] is not None and state['favored_token_id'] and not state['entered']:
        cancel_token_orders_acct(state['favored_token_id'])
    reset_market_state()
    state['market_ts'] = market_ts
    up_book = None
    down_book = None

    for attempt in range(8):
        info = get_market_info(market_ts)
        if info:
            state['market_info'] = info
            state['neg_risk'] = info.get('neg_risk', False)
            break
        time.sleep(1.0)

# ... trading logic happens here ...

# Past the stop threshold — kill any stale order
if (
    not state['entered']
    and time_left <= STOP_THRESHOLD_SEC
    and state['last_order_id'] is not None
    and state['favored_token_id']
):
    cancel_token_orders_acct(state['favored_token_id'])
    state['open_order_price'] = None
    state['last_order_id'] = None
    state['last_order_price'] = None
```
Together these two blocks give the bot a clean lifecycle per market: spin up at second 0, do nothing for 4 minutes, snipe window opens at second 240, attempt entries with verification, force-cancel at second 295, and start over at second 300. Repeat 288 times a day.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-95-cent-bid-sniper)

## Putting It All Together

Zoom out and the shape is simple. The strategy is two pure functions: pick_decided_side and compute_bid_target. The plumbing is the Polymarket V2 client and the data helpers. The discipline is the post-only flag at the exchange and the anti-duplicate verification flow in the loop.

Edge comes from refusing to play markets that aren't decided and refusing to pay more than 95¢ even when they are. The dashboard, hype messages, and event log are just UX — they exist so you can watch the bot reason in real time, but the bot would trade the same way with all of it stripped out.

## How to Run It

The bot expects a conda env called tflow with py_clob_client_v2, web3, requests, python-dotenv, and termcolor. Your .env needs the keys for whichever account you point ACCOUNT_SUFFIX at — for AUG14 that means PRIVATE_KEY_AUG14, PUBLIC_KEY_AUG14, optional API credentials, and the SECRET_AUG14 quirk.

Run the bot

```python
# 1) Activate the env (the bot will self-heal if you forget)
conda activate tflow

# 2) Confirm your .env has at minimum:
#    PRIVATE_KEY_AUG14=0x...
#    PUBLIC_KEY_AUG14=0x...

# 3) Fire it up
python 5min_95_bid_sniper.py

# Ctrl+C to bail. The bot will print a clean game-over scoreboard.
```
Start with BET_SIZE_USD = 1.0 (which the 5-share minimum will floor at ~$4.75). Watch a few markets roll through. Make sure your dashboard shows the snipe window opening, the lock-on happening, and at least a few resting orders before you scale up.

## The Full Source — Verbatim

For reference and copy-paste convenience, here is the entire file as it ships. If you only skimmed the chunks above, scroll back up — this file makes a lot more sense once you understand each section in isolation.

5min_95_bid_sniper.py — complete source

```python
#!/opt/anaconda3/envs/tflow/bin/python
"""
================================================================================
MOON DEV's 5-MINUTE 95c BID SNIPER v1.0  (AUG14 account)
================================================================================
A patient, last-60-second entry bot for BTC 5-minute UP/DOWN markets.

WHY THIS IS DIFFERENT FROM THE BUZZER BEATER:
  The old 5min_buzzer_beater.py entered at a 0.70 "favored" ask and CHASED THE
  ASK (aggressive taker). 70c is NOT decided — Moon Dev got wrecked. This bot
  fixes both mistakes:
    1. Only acts when a side is genuinely DECIDED — its ask is >= 0.95.
    2. We DO NOT market order / chase the ask. We SIT ON THE BID (passive maker)
       and see if we can get filled. We never pay more than 0.95 a share, which
       locks in a >= ~5.3% gain if the side resolves to $1.00.

STRATEGY (the whole thing in 5 lines):
  - Wait until <= 60 seconds left in the current 5-min market.
  - Find the side whose ask >= 0.95 (the market has basically already decided).
  - Rest a BUY limit on the bid: price = min(best_bid, 0.95). Never above 0.95.
  - Re-place every few seconds to stay on the bid. Stand down if the side stops
    being decided (ask drops < 0.95). One fill per market, then hold to expiry.
  - 95c -> 100c = 5.26% per win. We just want 5% every 5 minutes.

NOTE ON SIZE: Polymarket enforces a 5-share minimum per order. At 0.95 that is
  ~$4.75, so BET_SIZE_USD=1.0 will be bumped up to that floor — can't go lower.

MULTI-ACCOUNT:
  Set to the AUG14 wallet (signature_type=2 / Gnosis Safe). Change ACCOUNT_SUFFIX
  to run elsewhere.

Built by Moon Dev
================================================================================
"""

import sys
import os
import time
import random
import itertools
from collections import deque
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from termcolor import colored

# Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)

# ============================================================================
# PATH / ENV SETUP
# ============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples'))
from nice_funcs import calculate_shares, get_token_id

# ============================================================================
# ACCOUNT CONFIGURATION (this bot = AUG14)
# ============================================================================
ACCOUNT_SUFFIX = "_AUG14"

PRIVATE_KEY_ENV_NAME = f"PRIVATE_KEY{ACCOUNT_SUFFIX}"
PUBLIC_KEY_ENV_NAME = f"PUBLIC_KEY{ACCOUNT_SUFFIX}"
API_KEY_ENV_NAME = f"API_KEY{ACCOUNT_SUFFIX}"
API_SECRET_ENV_NAME = f"API_SECRET{ACCOUNT_SUFFIX}" if ACCOUNT_SUFFIX else "SECRET"
PASSPHRASE_ENV_NAME = f"PASSPHRASE{ACCOUNT_SUFFIX}"

SIGNATURE_TYPE = 1 if ACCOUNT_SUFFIX == "" else 2

# ============================================================================
# STRATEGY CONFIGURATION
# ============================================================================
BET_SIZE_USD = 1.0
ENTRY_THRESHOLD = 0.95
MAX_BUY_PRICE = 0.95
ENTRY_WINDOW_SEC = 60
STOP_THRESHOLD_SEC = 5
ORDER_UPDATE_INTERVAL = 3
PRICE_HOLD_TOLERANCE = 0.005

MARKET_DURATION = 300
ET = timezone(timedelta(hours=-5))

TARGET_GAIN_PCT = (1.0 / MAX_BUY_PRICE - 1.0) * 100.0

# ============================================================================
# SESSION STATS
# ============================================================================
SESSION_ENTRIES = 0
SESSION_SKIPS = 0
SESSION_ATTEMPTS = 0
SESSION_START = time.time()

# ============================================================================
# FUN ZONE
# ============================================================================
HYPE_MESSAGES = [
    "LFG Moon Dev!",
    "5% every 5 minutes",
    "We don't chase, we rest on the bid",
    "Only the decided ones, only 95c+",
    "Patience pays the maker",
    "No market orders. Ever.",
    "Sniping the last nickel",
    "Let the gamblers fight at 50c",
    "Decided = our zone",
    "Sit. Wait. Fill. Hold.",
    "AUG14 stays winning",
    "Ice in the veins",
    "The bid is our friend",
    "Built different",
    "Cook mode: PATIENT",
    "5.3% per win, stack em",
    "One bullet per market",
    "Moon Dev = the closer",
]

SPINNER_FRAMES = itertools.cycle(["o", "O", "0", "."])
ROCKET_FRAMES = itertools.cycle(["^   ", " ^  ", "  ^ ", "   ^", "  ^ ", " ^  "])

EVENT_LOG = deque(maxlen=6)

def log_event(msg, color="white"):
    ts = datetime.now().strftime("%H:%M:%S")
    EVENT_LOG.append((ts, msg, color))

# ============================================================================
# POLYMARKET CLIENT HELPERS (account-aware)
# ============================================================================
_CLIENT_CACHE = None

def _build_client():
    global _CLIENT_CACHE
    if _CLIENT_CACHE is not None:
        return _CLIENT_CACHE

    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import ApiCreds
    from py_clob_client_v2.constants import POLYGON
    from web3 import Web3

    key = os.getenv(PRIVATE_KEY_ENV_NAME)
    browser_address = os.getenv(PUBLIC_KEY_ENV_NAME)

    if not key or not browser_address:
        print(colored(
            f"Missing {PRIVATE_KEY_ENV_NAME} or {PUBLIC_KEY_ENV_NAME} in .env!",
            "red",
        ))
        sys.exit(1)

    try:
        browser_wallet = Web3.toChecksumAddress(browser_address)
    except AttributeError:
        browser_wallet = Web3.to_checksum_address(browser_address)

    client = ClobClient(
        host="https://clob.polymarket.com",
        chain_id=POLYGON,
        key=key,
        signature_type=SIGNATURE_TYPE,
        funder=browser_wallet,
    )

    api_key = os.getenv(API_KEY_ENV_NAME)
    api_secret = (
        os.getenv(API_SECRET_ENV_NAME)
        or os.getenv(f"SECRET{ACCOUNT_SUFFIX}")
        or os.getenv("SECRET")
    )
    passphrase = os.getenv(PASSPHRASE_ENV_NAME)

    if api_key and api_secret and passphrase:
        creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=passphrase)
        client.set_api_creds(creds=creds)
    else:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds=creds)

    _CLIENT_CACHE = client
    return client

def get_order_status_for_id(order_id):
    if not order_id or order_id == 'timeout-assumed-live':
        return None
    client = _build_client()
    for attempt in range(3):
        try:
            order = client.get_order(order_id)
            if not order:
                return {
                    'status': 'NOT_FOUND',
                    'size_matched': 0.0,
                    'original_size': 0.0,
                    'price': 0.0,
                    'is_filled': False,
                }
            if isinstance(order, dict):
                size_matched = float(order.get('size_matched', 0) or 0)
                original_size = float(order.get('original_size', 0) or 0)
                status = str(order.get('status', 'unknown'))
                price = float(order.get('price', 0) or 0)
            else:
                size_matched = float(getattr(order, 'size_matched', 0) or 0)
                original_size = float(getattr(order, 'original_size', 0) or 0)
                status = str(getattr(order, 'status', 'unknown'))
                price = float(getattr(order, 'price', 0) or 0)
            return {
                'status': status.upper(),
                'size_matched': size_matched,
                'original_size': original_size,
                'price': price,
                'is_filled': size_matched > 0,
            }
        except Exception as e:
            err = str(e)
            if any(code in err for code in ['500', '502', '503', '504', 'timeout', 'Timeout']):
                time.sleep(0.5 * (attempt + 1))
                continue
            log_event(f"get_order failed: {type(e).__name__}", "yellow")
            return "ERROR"
    return "ERROR"

def place_limit_order(token_id, side, price, size, neg_risk=False):
    from py_clob_client_v2.clob_types import OrderArgs, OrderType, PartialCreateOrderOptions

    client = _build_client()

    order_args = OrderArgs(
        token_id=str(token_id),
        price=float(price),
        size=float(size),
        side=side.upper(),
    )

    log_event(f"Resting {side} @ \${price:.4f} x {size} shares (post-only)", "cyan")

    options = PartialCreateOrderOptions(neg_risk=True) if neg_risk else None

    try:
        response = client.create_and_post_order(
            order_args,
            options=options,
            order_type=OrderType.GTC,
            post_only=True,
        )
        if response and (response.get('orderID') or response.get('success')):
            oid = response.get('orderID', '')
            log_event(f"Order LIVE — id {str(oid)[:10]}...", "green")
            return response
        log_event(f"Order rejected: {response}", "red")
        return response if response else {}
    except Exception as e:
        err = str(e)
        if 'Request exception' in err or 'Duplicated' in err or 'ReadTimeout' in err or 'timeout' in err.lower():
            log_event("post_order timed out — assuming it landed", "yellow")
            return {'orderID': 'timeout-assumed-live', 'status': 'LIVE'}
        log_event(f"post_order failed: {type(e).__name__}: {e}", "red")
        return {}

def cancel_token_orders_acct(token_id):
    from py_clob_client_v2.clob_types import OrderMarketCancelParams
    client = _build_client()
    try:
        client.cancel_market_orders(OrderMarketCancelParams(asset_id=str(token_id)))
        log_event(f"Cancelled orders on {str(token_id)[:10]}...", "yellow")
        return True
    except Exception as e:
        log_event(f"Cancel failed: {type(e).__name__}: {e}", "yellow")
        return False

# ============================================================================
# MARKET DATA HELPERS
# ============================================================================
def get_current_market_timestamp():
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    return MARKET_DURATION - (int(time.time()) - market_ts)

def get_order_book(token_id):
    response = requests.get(
        "https://clob.polymarket.com/book",
        params={'token_id': token_id},
        timeout=10,
    )
    if response.status_code != 200:
        return None
    data = response.json()
    bids = data.get('bids', [])
    asks = data.get('asks', [])
    if not bids or not asks:
        return None
    return {
        'best_bid': float(bids[-1]['price']),
        'best_ask': float(asks[-1]['price']),
    }

def get_market_info(market_ts):
    market_slug = f"btc-updown-5m-{market_ts}"
    response = requests.get(
        "https://gamma-api.polymarket.com/markets",
        params={'slug': market_slug, 'closed': 'false', 'active': 'true'},
        timeout=10,
    )
    if response.status_code != 200:
        return None
    markets = response.json()
    if not markets:
        return None

    market = markets[0]
    token_data = get_token_id(market['id'])
    if len(token_data) != 3:
        return None

    return {
        'market_id': market['id'],
        'up_token_id': token_data[1],
        'down_token_id': token_data[2],
        'question': market['question'],
        'slug': market_slug,
        'neg_risk': market.get('negRisk', False),
    }

def position_shares_for_token(token_id):
    user_address = os.getenv(PUBLIC_KEY_ENV_NAME)
    if not user_address:
        return 0.0
    try:
        resp = requests.get(
            "https://data-api.polymarket.com/positions",
            params={'user': user_address, 'limit': 500, 'sortBy': 'CURRENT', 'sortDirection': 'DESC'},
            timeout=8,
        )
        if resp.status_code != 200:
            return 0.0
        for pos in resp.json():
            if str(pos.get('asset')) == str(token_id):
                size = float(pos.get('size', 0) or 0)
                if size > 0:
                    return size
        return 0.0
    except Exception as e:
        log_event(f"positions fetch failed: {e}", "yellow")
        return 0.0

# ============================================================================
# CORE 95c BID SNIPER LOGIC
# ============================================================================
def pick_decided_side(up_book, down_book):
    up_ask = up_book['best_ask'] if up_book else None
    down_ask = down_book['best_ask'] if down_book else None

    up_qualifies = up_ask is not None and up_ask >= ENTRY_THRESHOLD
    down_qualifies = down_ask is not None and down_ask >= ENTRY_THRESHOLD

    if up_qualifies and down_qualifies:
        return ("UP", up_book) if up_ask >= down_ask else ("DOWN", down_book)
    if up_qualifies:
        return "UP", up_book
    if down_qualifies:
        return "DOWN", down_book
    return None, None

def compute_bid_target(favored_book):
    if not favored_book:
        return None
    if favored_book['best_ask'] < ENTRY_THRESHOLD:
        return None
    target = min(favored_book['best_bid'], MAX_BUY_PRICE)
    return round(target, 3)

def _place_fresh_bid(state, token_id, target_price):
    global SESSION_ATTEMPTS
    shares = calculate_shares(BET_SIZE_USD, target_price)
    if shares <= 0:
        return
    SESSION_ATTEMPTS += 1
    resp = place_limit_order(token_id, "BUY", target_price, shares, neg_risk=state['neg_risk'])
    if resp:
        oid = resp.get('orderID')
        if oid and oid != 'timeout-assumed-live':
            state['last_order_id'] = oid
            state['last_order_price'] = target_price
            state['open_order_price'] = target_price
        elif oid == 'timeout-assumed-live':
            state['last_order_id'] = 'timeout-assumed-live'
            state['last_order_price'] = target_price
            state['open_order_price'] = target_price

# (See the chunks above for the full dashboard drawing functions and main loop.
# The full version of this file includes: draw_banner, draw_scoreboard,
# draw_timer, draw_books, draw_status, draw_event_log, draw_footer,
# draw_dashboard, and the main() loop with rollover + verification flow.)
```
The complete file with dashboard rendering and the full main loop weighs in around 600 lines. Everything load-bearing for the strategy is in the chunks above — the rest is presentation.

## Want to See It Run Live?

Moon Dev streams these bots — build sessions, live trades, bugs and all — every weekday on the algo trading channel. Come hang out, ask questions, and steal ideas.

[Join the Moon Dev community](https://moondev.com)

## The Takeaway

The original buzzer-beater chased the ask at 70¢ and got punished by spread, fees, and false positives. This rewrite changes two things — the threshold (0.95) and the order type (post-only on the bid) — and the entire risk profile flips. We're no longer paying for the privilege of being wrong. We're getting paid to be right, in the markets the crowd has already called.

That's the lesson worth carrying past this one bot: most "edge" in algo trading is just discipline expressed in code. Pick a rule the market makes hard to break (post-only at the exchange), encode the math you actually want (cap at 0.95 = +5.3%), and refuse to do anything you can't prove is safe (the anti-duplicate flow). Build with love. Built by Moon Dev.

## More Moon Dev Open Source

[

### Polymarket 5-Minute Bot

The keyboard-driven manual version of this same market.

[

### CVD 5-Minute Bot

Cumulative volume delta as an entry signal for the same markets.

[

### HIP-3 Liquidation Trading Bot

Hyperliquid liquidation-cascade scalping bot.

[

### Smart Money Whale Scanner

Live $2K+ buys from profitable Polymarket traders.

Built with love by Moon Dev
