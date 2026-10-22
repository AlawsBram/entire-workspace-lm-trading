<!-- source: https://moondev.com/cvd-five-minute-bot -->
<!-- captured: 2026-10-07 -->
<!-- title: CVD 5-Minute Bot — Order Flow Alpha -->

CVD 5-Minute Bot | Order Flow Trading Bot | Polymarket + Hyperliquid | Moon Dev

Moon Dev Open Source

# CVD 5-Minute Bot: Order Flow Alpha

A fully automated bot that reads Cumulative Volume Delta divergences from Moon Dev API tick data, places stink bids on Polymarket BTC 5-minute Up/Down markets, and hedges the underlying on Hyperliquid. Order flow tells you what the crowd is actually doing — this bot listens.

By Moon Dev · March 16, 2026

## What Is This Bot?

[Unlike the [Easy Hyper Gambler](https://moondev.com/polymarket-five-minute-bot)

(which is keyboard-controlled — you press B to bet UP, S to bet DOWN), this bot is **fully automated**. It scans order flow data, makes its own decisions, places its own bets, and hedges itself. You start it and walk away.

The core idea is **CVD divergence**. CVD (Cumulative Volume Delta) tracks the net aggression of buyers vs sellers using tick-level trade data from the Moon Dev API. When price is moving one direction but order flow is moving the other, something interesting is happening — that's divergence, and it's the alpha signal.

The bot doesn't market-buy into positions. It places **stink bids** — limit orders at a 30% pullback below the current bid. You're fishing for a momentary dip to get filled at a discount. When the Polymarket stink bid fills, the bot immediately opens an inverse hedge on Hyperliquid at 40x leverage, creating a statistical arbitrage structure.

### How It Works — The 4 Signal Types

**BULLISH DIV** — Price DOWN but CVD positive: buyers are accumulating while price drops. The crowd is buying the dip quietly. Signal: BUY UP.

**BEARISH DIV** — Price UP but CVD negative: sellers are distributing while price rises. Smart money is selling into strength. Signal: BUY DOWN.

**STRONG BULL** — Price UP and CVD strongly positive: full momentum alignment. Everyone is buying and price is confirming. Signal: BUY UP.

**STRONG BEAR** — Price DOWN and CVD strongly negative: full momentum alignment to the downside. Signal: BUY DOWN.

The divergence signals are the high-conviction plays. Price and order flow disagreeing means someone is wrong — and the order flow usually knows first. Let me walk you through every piece of this bot.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/cvd-five-minute-bot)

## Step 1: Imports & Environment

The bot uses standard Python libraries plus a few key packages: pandas for trade logging and CSV tracking, eth_account for signing Hyperliquid transactions, requests for API calls, and the Moon Dev API client for tick data.

Shebang, docstring, and imports

```python
#!/opt/anaconda3/envs/tflow/bin/python
"""
================================================================================
MOON DEV's CVD 5-MINUTE BOT v1.0
================================================================================
Uses Moon Dev API CVD (Cumulative Volume Delta) data to trade BTC 5-minute
Up/Down markets on Polymarket with stink bid entries + Hyperliquid hedge.

STRATEGY (CVD Divergence):
  1. Pull BTC tick data from Moon Dev API across multiple timeframes
  2. Compute tick-level CVD using the tick rule:
     - Price ticks UP   = aggressive buy  -> CVD +1
     - Price ticks DOWN = aggressive sell -> CVD -1
  3. Detect divergence between price and CVD:
     - Price DOWN but CVD POSITIVE -> buyers accumulating -> BUY UP
     - Price UP but CVD NEGATIVE  -> sellers distributing -> BUY DOWN
  4. Place stink bid at PULLBACK_PCT below current bid
  5. On fill -> hedge inverse on Hyperliquid

Built by Moon Dev
================================================================================
"""

import sys
import os

# Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)

import time
import math
import requests
import json
import re
import pandas as pd
import eth_account
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from termcolor import colored

# Intraday timeframe slicing
TF_SECONDS = {"1m": 60, "3m": 180, "5m": 300, "10m": 600, "15m": 900}
```
The auto re-exec block is the same trick from the Easy bot — if you accidentally run the script with the wrong Python environment, it automatically restarts itself using the correct conda env. The TF_SECONDS dictionary maps timeframe labels to their duration in seconds. This is used later when slicing a single batch of tick data into multiple timeframe windows.

## Step 2: Path Setup & Helper Functions

This bot bridges **two exchanges** — Polymarket for the prediction market bets and Hyperliquid for the hedge. That means importing helper functions from both ecosystems. The nice_funcs module handles Polymarket operations, while the Hyperliquid helpers handle leverage trading.

Path setup and cross-exchange imports

```python
# PATH SETUP
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HYPER_BOTS_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid"
MOON_DEV_API_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots"

# Load env from project root
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Import Polymarket functions
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples'))
from nice_funcs import (
    cancel_token_orders,
    calculate_shares,
    get_all_positions,
    get_token_id,
)

def place_limit_order(token_id, side, price, size, neg_risk=False):
    """Embedded order function - uses signature_type=1 + pre-set API creds from .env"""
    # ... (full implementation in complete source below)
    pass
```
Notice how place_limit_order is defined inline rather than imported — this gives the bot full control over order construction. It uses signature_type=1 for Polymarket's browser wallet signing scheme and reads all credentials from .env.

The Hyperliquid imports use importlib to dynamically load the HL helper module from a separate path. The Moon Dev API client is imported for tick data access. Three different systems, one bot.

## Step 3: Configuration

All tunable parameters live at the top of the file. The CVD thresholds control how sensitive the divergence detection is, the stink bid pullback controls how aggressively you fish for dips, and the sizing split controls how much goes to Polymarket vs Hyperliquid.

Configuration block

```python
# --- Bot Speed ---
BOT_POLL_INTERVAL = 10              # Seconds between each cycle check

# --- CVD Signal Thresholds ---
CVD_DIVERGENCE_PRICE_THRESH = 0.02  # Price must move > 0.02% for divergence
CVD_DIVERGENCE_CVD_THRESH = 10      # CVD must be > 10 (opposite direction)
CVD_STRONG_PRICE_THRESH = 0.05      # Price must move > 0.05% for strong signal
CVD_STRONG_CVD_THRESH = 20          # CVD must be > 20 (same direction)

# --- CVD Timeframes to Check ---
CVD_SIGNAL_TIMEFRAMES = ["1m", "3m", "5m", "10m", "15m"]
CVD_PRIMARY_TF = "5m"               # Primary signal timeframe (matches market duration)

# --- Stink Bid Entry ---
PULLBACK_PCT = 0.30                 # 30% pullback from signal price

# --- Polymarket Sizing (60% of total exposure) ---
POLY_USD_PER_POSITION = 15.0        # USD per Polymarket position

# --- Hyperliquid Hedge (40% of total exposure) ---
HEDGE_USD = 100.0                   # $100 margin on Hyperliquid
HEDGE_LEVERAGE = 40                 # 40x leverage
HEDGE_SYMBOL = "BTC"
```
Let's break down the key parameters. CVD_DIVERGENCE_PRICE_THRESH at 0.02% means price needs to have moved at least that much for a divergence to register — this filters out noise. CVD_DIVERGENCE_CVD_THRESH at 10 means the cumulative tick delta needs to be at least 10 ticks in the opposite direction — that's 10 more aggressive trades against the price move.

The PULLBACK_PCT at 30% is aggressive — if the bid on an UP token is $0.50, the stink bid goes in at $0.35. You won't always get filled, but when you do, the risk/reward is excellent.

The 60/40 split means $15 goes on Polymarket (binary bet, max loss is $15) and $100 margin at 40x goes on Hyperliquid (controlling $4,000 notional of BTC). The Polymarket bet is directional alpha; the Hyperliquid leg is the hedge that reduces your net directional exposure.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/cvd-five-minute-bot)

## Step 4: CVD Core Logic

This is the heart of the bot. CVD (Cumulative Volume Delta) is computed using the **tick rule**: every time price ticks up, that trade is classified as an aggressive buy (+1). Every time price ticks down, that's an aggressive sell (-1). The CVD accumulates these across all ticks in a window.

CVD computation and divergence detection

```python
def compute_tick_cvd(ticks):
    """
    Compute CVD from tick data using the tick rule.
    Every price tick UP = aggressive buy (+1)
    Every price tick DOWN = aggressive sell (-1)
    Returns (cvd_value, price_change_pct, deltas_list, prices_list)
    """
    if not ticks or len(ticks) < 2:
        return 0, 0, [], []

    prices = [t.get('p', t.get('price', 0)) for t in ticks]
    cvd = 0
    deltas = []
    last_direction = 0

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            last_direction = 1
            delta = 1
        elif diff < 0:
            last_direction = -1
            delta = -1
        else:
            delta = last_direction    # unchanged price inherits last direction
        cvd += delta
        deltas.append(delta)

    price_change = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0
    return cvd, price_change, deltas, prices

def detect_divergence(price_change, cvd_value):
    """
    Detect CVD divergence signals.
    Returns: (signal_type, signal_text, direction, strength)
    """
    if abs(price_change) < 0.01 and abs(cvd_value) < 5:
        return "NEUTRAL", "NEUTRAL", "FLAT", 0

    # BEARISH DIVERGENCE: price going up but sellers aggressive
    if price_change > CVD_DIVERGENCE_PRICE_THRESH and cvd_value < -CVD_DIVERGENCE_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) * 2 + abs(price_change) * 100))
        return "BEARISH_DIV", "BEARISH DIV", "DOWN", strength

    # BULLISH DIVERGENCE: price going down but buyers aggressive
    if price_change < -CVD_DIVERGENCE_PRICE_THRESH and cvd_value > CVD_DIVERGENCE_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) * 2 + abs(price_change) * 100))
        return "BULLISH_DIV", "BULLISH DIV", "UP", strength

    # STRONG BULL: price and CVD both strongly positive
    if price_change > CVD_STRONG_PRICE_THRESH and cvd_value > CVD_STRONG_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) + abs(price_change) * 50))
        return "STRONG_BULL", "STRONG BULL", "UP", strength

    # STRONG BEAR: price and CVD both strongly negative
    if price_change < -CVD_STRONG_PRICE_THRESH and cvd_value < -CVD_STRONG_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) + abs(price_change) * 50))
        return "STRONG_BEAR", "STRONG BEAR", "DOWN", strength

    return "NEUTRAL", "NEUTRAL", "FLAT", 0
```
The tick rule is beautifully simple. If a trade happens at a higher price than the previous trade, the buyer was the aggressor — they lifted the ask. If it happens at a lower price, the seller was the aggressor — they hit the bid. When price stays the same, we inherit the last known direction.

Divergence detection is where the magic happens. Imagine BTC drops 0.05% in 5 minutes, but the CVD is +15. That means despite the price decline, there were 15 more aggressive buys than sells. Buyers are quietly accumulating — the price drop might be a trap. That's a **BULLISH DIV** signal, and the bot buys UP.

## Step 5: Multi-Timeframe CVD Scanner

The scanner is efficient — it fetches 1 hour of tick data from the Moon Dev API in a single call, then slices that data into 1m, 3m, 5m, 10m, and 15m windows. Each window gets its own CVD computation and divergence check. The strongest signal wins.

Multi-timeframe CVD signal scanner

```python
def check_cvd_signal():
    """
    Check CVD across intraday timeframes for a trade signal.
    Fetches 1h of ticks ONCE, then slices into 1m/3m/5m/10m/15m windows.
    Returns: (direction, signal_type, details_str) or (None, None, "")
    """
    signals = []

    tick_response = api.get_ticks("BTC", "1h", limit=10000)
    if not tick_response or not isinstance(tick_response, dict):
        return None, None, ""

    all_ticks = tick_response.get('ticks', [])
    if len(all_ticks) < 10:
        return None, None, ""

    # Slice into timeframe windows from the same data
    tick_data = {}
    for tf in CVD_SIGNAL_TIMEFRAMES:
        tick_data[tf] = slice_ticks_by_time(all_ticks, TF_SECONDS[tf])

    for tf in CVD_SIGNAL_TIMEFRAMES:
        ticks = tick_data.get(tf, [])
        if len(ticks) < 5:
            continue

        cvd_val, price_chg, deltas, prices = compute_tick_cvd(ticks)
        signal_type, signal_text, direction, strength = detect_divergence(price_chg, cvd_val)

        if signal_type in ("BULLISH_DIV", "BEARISH_DIV", "STRONG_BULL", "STRONG_BEAR"):
            detail = ""
            if "DIV" in signal_type:
                if direction == "UP":
                    detail = f"[{tf}] Price DOWN but buyers aggressive (CVD +{cvd_val}) = accumulation"
                else:
                    detail = f"[{tf}] Price UP but sellers aggressive (CVD {cvd_val}) = distribution"
            else:
                detail = f"[{tf}] Strong momentum {direction}"

            # Primary timeframe gets a 1.5x strength boost
            if tf == CVD_PRIMARY_TF:
                strength = int(strength * 1.5)

            signals.append((direction, signal_type, detail, strength, tf))

    if not signals:
        return None, None, ""

    # Pick strongest signal
    signals.sort(key=lambda x: x[3], reverse=True)
    best = signals[0]
    direction, signal_type, detail, strength, tf = best
    return direction, signal_type, detail
```
The key insight: one API call, five timeframes. The slice_ticks_by_time helper chops the 1-hour tick buffer into windows by filtering on the timestamp field. This is much more efficient than making 5 separate API calls.

The 5m timeframe (CVD_PRIMARY_TF) gets a 1.5x strength multiplier because it matches the market duration — a 5m divergence signal is the most relevant for a 5m market. The bot also checks dollar imbalance divergence between 5m and 15m windows: if 5m is buying while 15m is selling, that's a short-term reversal attempt.

Strength scoring ensures the bot picks the best signal when multiple timeframes fire at once. A strong divergence on the 5m timeframe with a strength of 80 beats a weak divergence on the 1m timeframe with a strength of 30.

## Step 6: Market Discovery

Every 5 minutes a new BTC Up/Down market opens on Polymarket. The bot needs to find it, get the UP and DOWN token IDs, and know how much time is left. This is the same market discovery logic as the Easy bot.

Market discovery functions

```python
def get_current_market_timestamp():
    """Get the timestamp for the current active 5-minute market"""
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    """Seconds remaining in current market"""
    now = int(time.time())
    elapsed = now - market_ts
    return MARKET_DURATION - elapsed

def get_market_info(market_ts):
    """
    Get market ID and token IDs for a BTC 5-min market.
    Market slug format: btc-updown-5m-{timestamp}
    """
    market_slug = f"btc-updown-5m-{market_ts}"
    url = "https://gamma-api.polymarket.com/markets"
    params = {'slug': market_slug, 'closed': 'false', 'active': 'true'}

    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        return None

    markets = response.json()
    if not markets or len(markets) == 0:
        return None

    market = markets[0]
    market_id = market['id']
    token_data = get_token_id(market_id)
    if len(token_data) != 3:
        return None

    return {
        'market_id': market_id,
        'up_token_id': token_data[1],
        'down_token_id': token_data[2],
        'question': market['question'],
        'slug': market_slug,
        'neg_risk': market.get('negRisk', False),
    }
```
The timestamp math is the same clever trick: (now // 300) * 300 rounds down to the nearest 300-second boundary. At 2:07 PM, the current market started at 2:05 PM. The market slug btc-updown-5m-{timestamp} is how Polymarket names these markets.

Each market has two outcome tokens: UP and DOWN. The bot queries the Gamma API to find the market, then calls get_token_id to resolve the specific token IDs needed for placing orders.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/cvd-five-minute-bot)

## Step 7: Stink Bid Entry

Instead of buying at market price, the bot places a limit order at a significant discount — the stink bid. The idea is that prediction market prices are volatile, and momentary dips happen frequently. By placing an order 30% below the current bid, you only get filled when there's a panic dip in your favor.

Stink bid placement

```python
def place_stink_bid(self):
    """Place stink bid at PULLBACK_PCT below signal price"""
    token_id = self.target_token_id
    outcome = self.target_outcome

    book = get_order_book(token_id)
    if not book:
        return False

    # Use the bid as our signal price
    self.signal_price = book['best_bid']

    # Stink bid = 30% below the bid
    self.stink_bid_price = round(self.signal_price * (1 - PULLBACK_PCT), 4)
    if self.stink_bid_price < 0.01:
        self.stink_bid_price = 0.01

    self.stink_bid_shares = calculate_shares(POLY_USD_PER_POSITION, self.stink_bid_price)
    if self.stink_bid_shares <= 0:
        return False

    # Cancel existing orders, place new stink bid
    cancel_token_orders(token_id)
    time.sleep(0.5)

    neg_risk = self.market_info.get('neg_risk', False)
    response = place_limit_order(
        token_id=token_id,
        side="BUY",
        price=self.stink_bid_price,
        size=self.stink_bid_shares,
        neg_risk=neg_risk,
    )

    if response and 'orderID' in response:
        self.order_placed = True
        return True
    return False
```
If the best bid on an UP token is $0.50, the stink bid goes in at $0.35. At that price, calculate_shares figures out that $15 buys about 42 shares. If the market resolves YES, those shares are worth $1 each — a $42 payout on a $15 bet.

The tradeoff is clear: you won't always get filled. But when you do, you're entering at a price that gives you much better risk/reward than a market buy. The bot cancels any existing orders before placing a new one to avoid stacking multiple positions.

## Step 8: Hyperliquid Hedge

This is what makes the strategy a statistical arbitrage rather than just a directional bet. When the Polymarket stink bid fills, the bot immediately opens an inverse position on Hyperliquid. If you bet UP on Polymarket, you go SHORT on Hyperliquid — and vice versa.

Hyperliquid hedge execution

```python
def fill_hyperliquid_hedge(poly_outcome):
    """
    Market order hedge on Hyperliquid (instant fill).
    If Polymarket outcome is "UP" -> SHORT BTC on HL
    If Polymarket outcome is "DOWN" -> LONG BTC on HL
    Returns (success, hedge_side, hedge_size_btc, hedge_price)
    """
    if poly_outcome.upper() == "UP":
        is_buy = False
        hedge_side = "SHORT"
    elif poly_outcome.upper() == "DOWN":
        is_buy = True
        hedge_side = "LONG"
    else:
        return False, "UNKNOWN", 0, 0

    # Cancel any existing orders, check for existing position
    hl.cancel_all_orders(hl_account)
    positions, in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = hl.get_position(HEDGE_SYMBOL, hl_account)
    if in_pos and abs(pos_size) > 0:
        return True, "LONG" if is_long else "SHORT", abs(pos_size), entry_px

    # Set leverage and calculate size
    exchange = Exchange(hl_account, constants.MAINNET_API_URL)
    exchange.update_leverage(HEDGE_LEVERAGE, HEDGE_SYMBOL, is_cross=False)

    ask, bid, l2_data = hl.ask_bid(HEDGE_SYMBOL)
    mid_price = (ask + bid) / 2
    btc_size = (HEDGE_USD * HEDGE_LEVERAGE) / mid_price

    # Round up to valid size
    sz_decimals, px_decimals = hl.get_sz_px_decimals(HEDGE_SYMBOL)
    factor = 10 ** sz_decimals
    btc_size = math.ceil(btc_size * factor) / factor

    # Cross the spread for instant fill
    market_px = ask if is_buy else bid
    result = hl.limit_order(HEDGE_SYMBOL, is_buy, btc_size, market_px, False, hl_account)

    # Verify fill
    time.sleep(1)
    positions, in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = hl.get_position(HEDGE_SYMBOL, hl_account)
    if in_pos and abs(pos_size) > 0:
        return True, "LONG" if is_long else "SHORT", abs(pos_size), entry_px

    hl.cancel_all_orders(hl_account)
    return False, hedge_side, 0, 0
```
The logic is straightforward: if you bet UP on Polymarket (expecting BTC price to rise in 5 minutes), you SHORT BTC on Hyperliquid. Why? Because you're isolating the **prediction market edge** from the **underlying price risk**.

At 40x leverage, $100 margin controls $4,000 notional of BTC. The hedge uses a market order (crossing the spread) for instant fill — you don't want to be unhedged while waiting for a limit order. The bot verifies the fill by checking the position after a 1-second delay.

When the 5-minute market expires, the bot calls close_hyperliquid_hedge() which sends an IOC (Immediate or Cancel) market order to flatten the position. The hedge only needs to last 5 minutes.

## Step 9: Trade Logging

Every signal gets logged to CSV using pandas — whether it filled or not. This is crucial for backtesting your parameters. You can analyze which signal types perform best, what fill rate your pullback percentage achieves, and whether the hedge is adding or destroying value.

Trade logging with pandas

```python
def log_trade(signal_type, direction, cvd_detail, poly_price, stink_price,
              poly_shares, hedge_side, hedge_size, hedge_price, result, reason=""):
    """Log trade to CSV using pandas"""
    os.makedirs(DATA_DIR, exist_ok=True)

    new_row = pd.DataFrame([{
        'timestamp': datetime.now().isoformat(),
        'signal_type': signal_type,
        'direction': direction,
        'cvd_detail': cvd_detail,
        'signal_price': round(poly_price, 4) if poly_price else 0,
        'stink_bid_price': round(stink_price, 4) if stink_price else 0,
        'pullback_pct': PULLBACK_PCT,
        'poly_shares': round(poly_shares, 2) if poly_shares else 0,
        'hedge_side': hedge_side,
        'hedge_size_btc': round(hedge_size, 6) if hedge_size else 0,
        'hedge_price': round(hedge_price, 2) if hedge_price else 0,
        'result': result,
        'reason': reason,
    }])

    if os.path.exists(TRADE_LOG_FILE):
        existing = pd.read_csv(TRADE_LOG_FILE)
        df = pd.concat([existing, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(TRADE_LOG_FILE, index=False)

def print_trade_summary():
    """Print summary of all tracked trades"""
    if not os.path.exists(TRADE_LOG_FILE):
        return

    df = pd.read_csv(TRADE_LOG_FILE)
    total = len(df)
    both_filled = len(df[df['result'] == 'BOTH_FILLED'])
    poly_only = len(df[df['result'] == 'POLY_ONLY'])
    no_fill = len(df[df['result'].isin(['NO_FILL', 'CANCELLED', 'TIME_EXPIRED'])])
    div_trades = len(df[df['signal_type'].str.contains('DIV', na=False)])
    strong_trades = len(df[df['signal_type'].str.contains('STRONG', na=False)])
```
The CSV tracks everything: signal type, direction, the CVD detail string, signal price, stink bid price, shares, hedge details, and the result (BOTH_FILLED, POLY_ONLY, NO_FILL, CANCELLED, TIME_EXPIRED). The print_trade_summary function gives you a quick breakdown at startup.

Over time, this data tells you whether divergence signals outperform momentum signals, what your optimal pullback percentage should be, and whether the Hyperliquid hedge is net positive or negative. Data-driven iteration.

## Step 10: Main Bot Loop

The bot runs as a state machine that processes one market cycle at a time. Each cycle: find market, scan CVD, place stink bid, monitor for fill, hedge on fill, hold to expiry, close hedge, repeat. The bot runs 24/7, processing a new market every 5 minutes — that's 288 opportunities per day.

Main bot loop and state machine

```python
class CVDStinkBot:
    def __init__(self):
        self.current_market_ts = None
        self.market_info = None
        self.signal_fired = False
        self.order_placed = False
        self.poly_filled = False
        self.hedge_filled = False
        # ... (full state in complete source)

    def run_market_cycle(self, market_ts):
        """Run one complete 5-minute market cycle"""
        # 1. Find the market
        self.market_info = get_market_info(market_ts)
        if not self.market_info:
            return

        while True:
            time_remaining = get_time_remaining(market_ts)
            if time_remaining <= 0:
                self.cancel_orders()
                if self.hedge_filled:
                    close_hyperliquid_hedge()
                break

            # 2. If filled, just hold
            if self.poly_filled:
                time.sleep(2)
                continue

            # 3. If order placed, check for fill -> hedge
            if self.order_placed and not self.poly_filled:
                if self.check_for_fill():
                    hedge_ok, hedge_side, hedge_size, hedge_price = fill_hyperliquid_hedge(self.target_outcome)
                    self.hedge_filled = hedge_ok
                    log_trade(...)
                time.sleep(2)
                continue

            # 4. Scan CVD and place stink bid
            if not self.signal_fired:
                direction, signal_type, detail = check_cvd_signal()
                if direction:
                    self.signal_fired = True
                    self.target_outcome = direction  # "UP" or "DOWN"
                    self.place_stink_bid()

            time.sleep(BOT_POLL_INTERVAL)

def main():
    bot = CVDStinkBot()
    while True:
        market_ts = get_current_market_timestamp()
        bot.reset()
        bot.run_market_cycle(market_ts)
```
The state machine is clean: signal_fired prevents scanning twice per market, order_placed tracks whether we have a stink bid out, poly_filled triggers the hedge, and hedge_filled means both legs are on and we just hold to expiry.

When the market expires (time remaining hits 0), the bot cancels any unfilled orders, closes the Hyperliquid hedge if active, logs the trade result, resets its state, and waits for the next market. The main() function handles the outer loop and graceful shutdown on Ctrl+C.

If the bot encounters an error mid-cycle, it catches the exception, logs a warning, and retries after 5 seconds. This makes it resilient to temporary API failures and network hiccups — important for a bot that needs to run continuously.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/cvd-five-minute-bot)

## Full Source Code

Here's the complete bot in a single file. , save it, set up your .env, and run it. The bot starts scanning CVD immediately and will place its first stink bid as soon as it detects a divergence signal.

cvd_5min_bot.py — Complete source

```python
#!/opt/anaconda3/envs/tflow/bin/python
"""
================================================================================
MOON DEV's CVD 5-MINUTE BOT v1.0
================================================================================
Uses Moon Dev API CVD (Cumulative Volume Delta) data to trade BTC 5-minute
Up/Down markets on Polymarket with stink bid entries + Hyperliquid hedge.

STRATEGY (CVD Divergence):
  1. Pull BTC tick data from Moon Dev API across multiple timeframes
  2. Compute tick-level CVD using the tick rule:
     - Price ticks UP   = aggressive buy  -> CVD +1
     - Price ticks DOWN = aggressive sell -> CVD -1
  3. Detect divergence between price and CVD:
     - Price DOWN but CVD POSITIVE -> buyers accumulating -> BUY UP
     - Price UP but CVD NEGATIVE  -> sellers distributing -> BUY DOWN
  4. Place stink bid at PULLBACK_PCT below current bid
  5. On fill -> hedge inverse on Hyperliquid

SIGNALS:
  BULLISH DIV: Price < -0.02% but CVD > +10  -> accumulation -> EXPECT UP
  BEARISH DIV: Price > +0.02% but CVD < -10  -> distribution -> EXPECT DOWN
  STRONG BULL: Price > +0.05% AND CVD > +20  -> full momentum UP
  STRONG BEAR: Price < -0.05% AND CVD < -20  -> full momentum DOWN

Built by Moon Dev
================================================================================
"""

import sys
import os

# Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)

import time
import math
import requests
import json
import re
import pandas as pd
import eth_account
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from termcolor import colored

# Intraday timeframe slicing (same as updated CVD scanner)
TF_SECONDS = {"1m": 60, "3m": 180, "5m": 300, "10m": 600, "15m": 900}

# ============================================================================
# PATH SETUP
# ============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HYPER_BOTS_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid"
MOON_DEV_API_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots"

# Load env from project root
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Import Polymarket functions
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples'))
from nice_funcs import (
    cancel_token_orders,
    calculate_shares,
    get_all_positions,
    get_token_id,
)

def place_limit_order(token_id, side, price, size, neg_risk=False):
    """
    Embedded order function (same approach as liq_stink_bot)
    Uses signature_type=1 + pre-set API creds from .env
    """
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions, ApiCreds
    from py_clob_client.constants import POLYGON
    from web3 import Web3

    key = os.getenv("PRIVATE_KEY")
    browser_address = os.getenv("PUBLIC_KEY")
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("SECRET")
    passphrase = os.getenv("PASSPHRASE")

    if not key or not browser_address:
        print(colored("Missing PRIVATE_KEY or PUBLIC_KEY in .env!", "red"))
        return {}

    try:
        browser_wallet = Web3.toChecksumAddress(browser_address)
    except AttributeError:
        browser_wallet = Web3.to_checksum_address(browser_address)

    client = ClobClient(
        host="https://clob.polymarket.com",
        key=key,
        chain_id=POLYGON,
        funder=browser_wallet,
        signature_type=1,
    )

    if api_key and api_secret and passphrase:
        creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=passphrase)
        client.set_api_creds(creds=creds)
    else:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds=creds)

    order_args = OrderArgs(
        token_id=str(token_id),
        price=price,
        size=size,
        side=side.upper(),
        fee_rate_bps=1000,
    )

    print(colored(f"Placing {side} limit order...", "cyan"))
    print(colored(f"   Token: {str(token_id)[:20]}...", "white"))
    print(colored(f"   Price: ${price:.4f} | Size: {size} shares | Neg Risk: {neg_risk}", "white"))

    if neg_risk:
        signed_order = client.create_order(order_args, options=PartialCreateOrderOptions(neg_risk=True))
        response = client.post_order(signed_order)
        if response and response.get('orderID'):
            print(colored(f"Order placed! ID: {response['orderID'][:20]}...", "green"))
            return response

    signed_order = client.create_order(order_args)
    response = client.post_order(signed_order)

    if response and response.get('orderID'):
        print(colored(f"Order placed! ID: {response['orderID'][:20]}...", "green"))
        return response
    else:
        print(colored(f"Order failed: {response}", "red"))
        return response if response else {}

# Import Moon Dev API
sys.path.insert(0, MOON_DEV_API_PATH)
from api import MoonDevAPI

# Import Hyperliquid functions
import importlib.util
_hl_spec = importlib.util.spec_from_file_location(
    "hl_nice_funcs",
    os.path.join(HYPER_BOTS_PATH, "nice_funcs.py")
)
hl = importlib.util.module_from_spec(_hl_spec)
_hl_spec.loader.exec_module(hl)

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# ============================================================================
# CONFIGURATION
# ============================================================================

# --- Bot Speed ---
BOT_POLL_INTERVAL = 10              # Seconds between each cycle check

# --- CVD Signal Thresholds ---
CVD_DIVERGENCE_PRICE_THRESH = 0.02  # Price must move > 0.02% for divergence
CVD_DIVERGENCE_CVD_THRESH = 10      # CVD must be > 10 (opposite direction) for divergence
CVD_STRONG_PRICE_THRESH = 0.05      # Price must move > 0.05% for strong signal
CVD_STRONG_CVD_THRESH = 20          # CVD must be > 20 (same direction) for strong signal

# --- CVD Timeframes to Check ---
CVD_SIGNAL_TIMEFRAMES = ["1m", "3m", "5m", "10m", "15m"]
CVD_PRIMARY_TF = "5m"               # Primary signal timeframe (matches market duration)
CVD_CONFIRM_TIMEFRAMES = ["10m", "15m"]  # Confirmation timeframes (slightly higher)
REQUIRE_CONFIRMATION = False         # If True, need signal + confirmation alignment

# --- Dollar Imbalance Divergence (5m vs 15m) ---
IMBALANCE_DIVERGENCE_ENABLED = True
IMBALANCE_SHORT_TF = "5m"
IMBALANCE_LONG_TF = "15m"
IMBALANCE_SHORT_RATIO_THRESH = 0.3
IMBALANCE_LONG_RATIO_THRESH = 0.2

# --- Stink Bid Entry ---
PULLBACK_PCT = 0.30                 # 30% pullback from signal price
MIN_TIME_LEFT = 60                  # Cancel orders if < 60 seconds left on market

# --- Polymarket Sizing (60% of total exposure) ---
POLY_USD_PER_POSITION = 15.0       # USD per Polymarket position

# --- Hyperliquid Hedge (40% of total exposure) ---
HEDGE_USD = 100.0                  # $100 margin on Hyperliquid
HEDGE_LEVERAGE = 40                # 40x leverage
HEDGE_SYMBOL = "BTC"
HEDGE_FILL_WAIT = 2
HEDGE_MAX_ATTEMPTS = 10
HEDGE_PRICE_BUMP_PCT = 0.001

# --- Market Timing ---
MARKET_DURATION = 300               # 5-minute markets = 300 seconds

# --- Files ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TRADE_LOG_FILE = os.path.join(DATA_DIR, "cvd_5min_trades.csv")

# ET timezone (UTC-5)
ET = timezone(timedelta(hours=-5))

# ============================================================================
# HYPERLIQUID SETUP
# ============================================================================
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')
if not HYPER_LIQUID_KEY:
    print(colored("HYPER_LIQUID_KEY not found in .env!", "red"))
    sys.exit(1)

hl_account = eth_account.Account.from_key(HYPER_LIQUID_KEY)
print(colored(f"Hyperliquid account loaded!", "green"))

# ============================================================================
# MOON DEV API SETUP
# ============================================================================
api = MoonDevAPI()
if not api.api_key:
    print(colored("MOONDEV_API_KEY not found in .env!", "red"))
    sys.exit(1)
print(colored(f"Moon Dev API loaded!", "green"))

# ============================================================================
# CVD CORE LOGIC
# ============================================================================

def compute_tick_cvd(ticks):
    """
    Compute CVD from tick data using the tick rule.
    Every price tick UP = aggressive buy (+1)
    Every price tick DOWN = aggressive sell (-1)
    Returns (cvd_value, price_change_pct, deltas_list, prices_list)
    """
    if not ticks or len(ticks) < 2:
        return 0, 0, [], []

    prices = [t.get('p', t.get('price', 0)) for t in ticks]
    cvd = 0
    deltas = []
    last_direction = 0

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            last_direction = 1
            delta = 1
        elif diff < 0:
            last_direction = -1
            delta = -1
        else:
            delta = last_direction
        cvd += delta
        deltas.append(delta)

    price_change = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0
    return cvd, price_change, deltas, prices

def slice_ticks_by_time(ticks, seconds):
    """Chop tick data to last N seconds using timestamp field 't'"""
    if not ticks:
        return ticks
    now_ms = time.time() * 1000
    cutoff = now_ms - (seconds * 1000)
    return [t for t in ticks if t.get('t', 0) >= cutoff]

def compute_tick_imbalance(ticks):
    """Build buy/sell dollar imbalance from raw ticks using tick rule"""
    if not ticks or len(ticks) < 2:
        return {'buy_volume_usd': 0, 'sell_volume_usd': 0, 'net_imbalance_usd': 0, 'imbalance_ratio': 0}
    buy_vol = 0
    sell_vol = 0
    last_direction = 0
    for i in range(1, len(ticks)):
        p = ticks[i].get('p', ticks[i].get('price', 0))
        prev_p = ticks[i-1].get('p', ticks[i-1].get('price', 0))
        diff = p - prev_p
        if diff > 0:
            last_direction = 1
        elif diff < 0:
            last_direction = -1
        if last_direction >= 0:
            buy_vol += p
        else:
            sell_vol += p
    total = buy_vol + sell_vol
    net = buy_vol - sell_vol
    ratio = (net / total) if total > 0 else 0
    return {'buy_volume_usd': buy_vol, 'sell_volume_usd': sell_vol, 'net_imbalance_usd': net, 'imbalance_ratio': ratio}

def detect_divergence(price_change, cvd_value):
    """
    Detect CVD divergence signals.
    Returns: (signal_type, signal_text, direction, strength)
    """
    if abs(price_change) < 0.01 and abs(cvd_value) < 5:
        return "NEUTRAL", "NEUTRAL", "FLAT", 0

    if price_change > CVD_DIVERGENCE_PRICE_THRESH and cvd_value < -CVD_DIVERGENCE_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) * 2 + abs(price_change) * 100))
        return "BEARISH_DIV", "BEARISH DIV", "DOWN", strength

    if price_change < -CVD_DIVERGENCE_PRICE_THRESH and cvd_value > CVD_DIVERGENCE_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) * 2 + abs(price_change) * 100))
        return "BULLISH_DIV", "BULLISH DIV", "UP", strength

    if price_change > CVD_STRONG_PRICE_THRESH and cvd_value > CVD_STRONG_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) + abs(price_change) * 50))
        return "STRONG_BULL", "STRONG BULL", "UP", strength

    if price_change < -CVD_STRONG_PRICE_THRESH and cvd_value < -CVD_STRONG_CVD_THRESH:
        strength = min(100, int(abs(cvd_value) + abs(price_change) * 50))
        return "STRONG_BEAR", "STRONG BEAR", "DOWN", strength

    if price_change > 0 and cvd_value > 0:
        return "BULLISH", "BULLISH", "UP", 20
    if price_change < 0 and cvd_value < 0:
        return "BEARISH", "BEARISH", "DOWN", 20

    return "NEUTRAL", "NEUTRAL", "FLAT", 0

# ============================================================================
# CVD SIGNAL SCANNER
# ============================================================================

def check_cvd_signal():
    """
    Check CVD across intraday timeframes for a trade signal.
    Fetches 1h of ticks ONCE, then slices into 1m/3m/5m/10m/15m windows.
    Returns: (direction, signal_type, details_str) or (None, None, "")
    """
    signals = []

    tick_response = api.get_ticks("BTC", "1h", limit=10000)
    if not tick_response or not isinstance(tick_response, dict):
        print(colored(f"   No tick data from API", "yellow"))
        return None, None, ""

    all_ticks = tick_response.get('ticks', [])
    if len(all_ticks) < 10:
        print(colored(f"   Not enough ticks ({len(all_ticks)})", "yellow"))
        return None, None, ""

    print(colored(f"   Fetched {len(all_ticks)} ticks, slicing into intraday windows...", "white"))

    tick_data = {}
    for tf in CVD_SIGNAL_TIMEFRAMES:
        tick_data[tf] = slice_ticks_by_time(all_ticks, TF_SECONDS[tf])

    for tf in CVD_SIGNAL_TIMEFRAMES:
        ticks = tick_data.get(tf, [])
        if len(ticks) < 5:
            continue

        cvd_val, price_chg, deltas, prices = compute_tick_cvd(ticks)
        signal_type, signal_text, direction, strength = detect_divergence(price_chg, cvd_val)

        print(colored(f"   CVD [{tf}] Price: {price_chg:+.3f}% | CVD: {cvd_val:+d} | Signal: {signal_text} | Ticks: {len(ticks)}", "cyan"))

        if signal_type in ("BULLISH_DIV", "BEARISH_DIV", "STRONG_BULL", "STRONG_BEAR"):
            detail = ""
            if "DIV" in signal_type:
                if direction == "UP":
                    detail = f"[{tf}] Price DOWN {price_chg:+.3f}% but buyers aggressive (CVD +{cvd_val}) = accumulation"
                else:
                    detail = f"[{tf}] Price UP {price_chg:+.3f}% but sellers aggressive (CVD {cvd_val}) = distribution"
            else:
                detail = f"[{tf}] Strong momentum {direction} (Price {price_chg:+.3f}%, CVD {cvd_val:+d})"

            if tf == CVD_PRIMARY_TF:
                strength = int(strength * 1.5)

            signals.append((direction, signal_type, detail, strength, tf))

    confirm_direction = None
    if REQUIRE_CONFIRMATION and signals:
        for tf in CVD_CONFIRM_TIMEFRAMES:
            ticks = tick_data.get(tf, [])
            if len(ticks) < 5:
                continue
            cvd_val, price_chg, deltas, prices = compute_tick_cvd(ticks)
            signal_type, signal_text, direction, strength = detect_divergence(price_chg, cvd_val)
            if direction in ("UP", "DOWN"):
                confirm_direction = direction

    if IMBALANCE_DIVERGENCE_ENABLED:
        imb_short = api.get_imbalance(IMBALANCE_SHORT_TF)
        imb_long = api.get_imbalance(IMBALANCE_LONG_TF)

        if not imb_short or not imb_short.get('by_coin', {}).get('BTC', {}):
            short_ticks = tick_data.get(IMBALANCE_SHORT_TF, [])
            if short_ticks:
                computed = compute_tick_imbalance(short_ticks)
                imb_short = {'by_coin': {'BTC': computed}}

        if not imb_long or not imb_long.get('by_coin', {}).get('BTC', {}):
            long_ticks = tick_data.get(IMBALANCE_LONG_TF, [])
            if long_ticks:
                computed = compute_tick_imbalance(long_ticks)
                imb_long = {'by_coin': {'BTC': computed}}

        if imb_short and imb_long:
            short_btc = imb_short.get('by_coin', {}).get('BTC', {})
            long_btc = imb_long.get('by_coin', {}).get('BTC', {})
            short_ratio = short_btc.get('imbalance_ratio', 0)
            long_ratio = long_btc.get('imbalance_ratio', 0)

            if short_ratio > IMBALANCE_SHORT_RATIO_THRESH and long_ratio < -IMBALANCE_LONG_RATIO_THRESH:
                detail = f"[{IMBALANCE_SHORT_TF} vs {IMBALANCE_LONG_TF}] 5m buying against 15m selling = reversal attempt"
                signals.append(("UP", "IMBALANCE_DIV", detail, 60, f"{IMBALANCE_SHORT_TF}v{IMBALANCE_LONG_TF}"))
            elif short_ratio < -IMBALANCE_SHORT_RATIO_THRESH and long_ratio > IMBALANCE_LONG_RATIO_THRESH:
                detail = f"[{IMBALANCE_SHORT_TF} vs {IMBALANCE_LONG_TF}] 5m selling against 15m buying = pullback"
                signals.append(("DOWN", "IMBALANCE_DIV", detail, 60, f"{IMBALANCE_SHORT_TF}v{IMBALANCE_LONG_TF}"))

    if not signals:
        return None, None, ""

    signals.sort(key=lambda x: x[3], reverse=True)
    best = signals[0]
    direction, signal_type, detail, strength, tf = best

    if REQUIRE_CONFIRMATION and confirm_direction and confirm_direction != direction:
        return None, None, ""

    return direction, signal_type, detail

# ============================================================================
# TRADE LOGGING (Pandas CSV)
# ============================================================================

def log_trade(signal_type, direction, cvd_detail, poly_price, stink_price,
              poly_shares, hedge_side, hedge_size, hedge_price, result, reason=""):
    """Log trade to CSV using pandas"""
    os.makedirs(DATA_DIR, exist_ok=True)

    poly_usd = round(stink_price * poly_shares, 4) if stink_price and poly_shares else 0
    hedge_usd = round(hedge_size * hedge_price, 4) if hedge_size and hedge_price else 0

    new_row = pd.DataFrame([{
        'timestamp': datetime.now().isoformat(),
        'signal_type': signal_type,
        'direction': direction,
        'cvd_detail': cvd_detail,
        'signal_price': round(poly_price, 4) if poly_price else 0,
        'stink_bid_price': round(stink_price, 4) if stink_price else 0,
        'pullback_pct': PULLBACK_PCT,
        'poly_shares': round(poly_shares, 2) if poly_shares else 0,
        'poly_usd': poly_usd,
        'hedge_side': hedge_side,
        'hedge_size_btc': round(hedge_size, 6) if hedge_size else 0,
        'hedge_price': round(hedge_price, 2) if hedge_price else 0,
        'hedge_usd': hedge_usd,
        'result': result,
        'reason': reason,
    }])

    if os.path.exists(TRADE_LOG_FILE):
        existing = pd.read_csv(TRADE_LOG_FILE)
        df = pd.concat([existing, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(TRADE_LOG_FILE, index=False)
    print(colored(f"   Trade logged to CSV", "green"))

def print_trade_summary():
    """Print summary of all tracked trades"""
    if not os.path.exists(TRADE_LOG_FILE):
        print(colored(f"   No trade history yet (first run)", "yellow"))
        return

    df = pd.read_csv(TRADE_LOG_FILE)
    if df.empty:
        print(colored(f"   Trade log is empty", "yellow"))
        return

    total = len(df)
    both_filled = len(df[df['result'] == 'BOTH_FILLED'])
    poly_only = len(df[df['result'] == 'POLY_ONLY'])
    no_fill = len(df[df['result'].isin(['NO_FILL', 'CANCELLED', 'TIME_EXPIRED'])])
    total_poly_usd = df['poly_usd'].sum()
    total_hedge_usd = df['hedge_usd'].sum()

    div_trades = len(df[df['signal_type'].str.contains('DIV', na=False)])
    strong_trades = len(df[df['signal_type'].str.contains('STRONG', na=False)])

    print(colored(f"\nCVD BOT TRADE HISTORY", "cyan", attrs=['bold']))
    print(colored(f"   Total signals:    {total}", "white"))
    print(colored(f"   Divergence:       {div_trades}", "magenta"))
    print(colored(f"   Strong momentum:  {strong_trades}", "cyan"))
    print(colored(f"   Both filled:      {both_filled}", "green"))
    print(colored(f"   Poly only:        {poly_only}", "yellow"))
    print(colored(f"   No fill:          {no_fill}", "white"))
    print(colored(f"   Total Poly USD:   ${total_poly_usd:,.2f}", "white"))
    print(colored(f"   Total Hedge USD:  ${total_hedge_usd:,.2f}", "white"))

    if total > 0:
        print(colored(f"\n   Last 5 trades:", "cyan"))
        recent = df.tail(5)
        for _, row in recent.iterrows():
            ts = str(row['timestamp'])[:19]
            print(colored(f"   {ts} | {row['signal_type']:<14} | {row['direction']:<5} | stink ${row['stink_bid_price']:.3f} | {row['result']}", "white"))
    print()

# ============================================================================
# MARKET DISCOVERY
# ============================================================================

def get_current_market_timestamp():
    """Get the timestamp for the current active 5-minute market"""
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    """Seconds remaining in current market"""
    now = int(time.time())
    elapsed = now - market_ts
    return MARKET_DURATION - elapsed

def get_market_info(market_ts):
    """
    Get market ID and token IDs for a BTC 5-min market.
    Market slug format: btc-updown-5m-{timestamp}
    """
    market_slug = f"btc-updown-5m-{market_ts}"
    print(colored(f"   Looking for market: {market_slug}", "cyan"))

    url = "https://gamma-api.polymarket.com/markets"
    params = {
        'slug': market_slug,
        'closed': 'false',
        'active': 'true'
    }

    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        return None

    markets = response.json()
    if not markets or len(markets) == 0:
        return None

    market = markets[0]
    market_id = market['id']

    token_data = get_token_id(market_id)
    if len(token_data) != 3:
        print(colored(f"   Unexpected token data format", "yellow"))
        return None

    up_token_id = token_data[1]
    down_token_id = token_data[2]

    print(colored(f"   Found market: {market['question']}", "green"))

    neg_risk = market.get('negRisk', False)

    return {
        'market_id': market_id,
        'up_token_id': up_token_id,
        'down_token_id': down_token_id,
        'question': market['question'],
        'slug': market_slug,
        'neg_risk': neg_risk,
    }

# ============================================================================
# ORDER BOOK
# ============================================================================

def get_order_book(token_id):
    """Get best bid/ask from CLOB"""
    url = "https://clob.polymarket.com/book"
    params = {'token_id': token_id}
    response = requests.get(url, params=params, timeout=10)

    if response.status_code != 200:
        return None

    data = response.json()
    bids = data.get('bids', [])
    asks = data.get('asks', [])

    if not bids or not asks:
        return None

    best_bid = float(bids[-1]['price'])
    best_ask = float(asks[0]['price'])

    return {'best_bid': best_bid, 'best_ask': best_ask, 'spread': best_ask - best_bid}

def _get_portfolio_quiet():
    """Get portfolio without print spam"""
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    portfolio = get_all_positions()
    sys.stdout = old_stdout
    return portfolio

def check_poly_filled(token_id):
    """Check if we have a filled position for this token"""
    portfolio = _get_portfolio_quiet()
    if portfolio and 'positions' in portfolio:
        for pos in portfolio['positions']:
            if pos.get('asset_id') == token_id and pos.get('position_size', 0) > 0:
                return True
    return False

# ============================================================================
# HYPERLIQUID HEDGE
# ============================================================================

def fill_hyperliquid_hedge(poly_outcome):
    """
    Market order hedge on Hyperliquid (instant fill).
    If Polymarket outcome is "UP" -> SHORT BTC on HL
    If Polymarket outcome is "DOWN" -> LONG BTC on HL
    Returns (success, hedge_side, hedge_size_btc, hedge_price)
    """
    if poly_outcome.upper() == "UP":
        is_buy = False
        hedge_side = "SHORT"
    elif poly_outcome.upper() == "DOWN":
        is_buy = True
        hedge_side = "LONG"
    else:
        print(colored(f"   Unknown outcome '{poly_outcome}'", "red"))
        return False, "UNKNOWN", 0, 0

    hedge_usd = HEDGE_USD
    print(colored(f"\n   HEDGE LEG: {hedge_side} ${hedge_usd:.2f} BTC @ {HEDGE_LEVERAGE}x on Hyperliquid", "magenta", attrs=['bold']))

    hl.cancel_all_orders(hl_account)
    time.sleep(0.5)

    positions, in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = hl.get_position(HEDGE_SYMBOL, hl_account)
    if in_pos and abs(pos_size) > 0:
        actual_side = "LONG" if is_long else "SHORT"
        print(colored(f"   Already have HL position: {actual_side} {abs(pos_size)} BTC -- skipping new hedge", "yellow"))
        return True, actual_side, abs(pos_size), entry_px

    exchange = Exchange(hl_account, constants.MAINNET_API_URL)
    exchange.update_leverage(HEDGE_LEVERAGE, HEDGE_SYMBOL, is_cross=False)
    print(colored(f"   Leverage set to {HEDGE_LEVERAGE}x isolated", "magenta"))

    ask, bid, l2_data = hl.ask_bid(HEDGE_SYMBOL)
    mid_price = (ask + bid) / 2
    btc_size = (hedge_usd * HEDGE_LEVERAGE) / mid_price

    sz_decimals, px_decimals = hl.get_sz_px_decimals(HEDGE_SYMBOL)
    factor = 10 ** sz_decimals
    btc_size = math.ceil(btc_size * factor) / factor

    if btc_size <= 0:
        print(colored(f"   Size too small to hedge", "yellow"))
        return False, hedge_side, 0, 0

    if is_buy:
        market_px = ask
    else:
        market_px = bid

    print(colored(f"   MARKET {hedge_side} {btc_size} BTC @ ${market_px:.1f} (crossing spread)", "magenta"))

    result = hl.limit_order(HEDGE_SYMBOL, is_buy, btc_size, market_px, False, hl_account)

    filled = False
    if result and 'response' in result:
        statuses = result['response'].get('data', {}).get('statuses', [])
        if statuses:
            status = statuses[0]
            if 'filled' in status:
                filled = True
            elif 'error' in status:
                print(colored(f"   HL order error: {status['error']}", "red"))
                return False, hedge_side, 0, 0

    time.sleep(1)
    positions, in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = hl.get_position(HEDGE_SYMBOL, hl_account)

    if in_pos and abs(pos_size) > 0:
        actual_side = "LONG" if is_long else "SHORT"
        print(colored(f"   HEDGE FILLED! {actual_side} {abs(pos_size)} BTC @ ${entry_px:.1f}", "green", attrs=['bold']))
        return True, actual_side, abs(pos_size), entry_px

    hl.cancel_all_orders(hl_account)
    print(colored(f"   Hedge not filled, cancelled. No retry to avoid stacking.", "yellow"))
    return False, hedge_side, 0, 0

def close_hyperliquid_hedge():
    """
    Close any open Hyperliquid hedge with IOC market order.
    """
    for attempt in range(5):
        positions, in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = hl.get_position(HEDGE_SYMBOL, hl_account)

        if not in_pos or abs(pos_size) == 0:
            print(colored(f"   HEDGE CLOSED!", "green", attrs=['bold']))
            return

        is_buy = not is_long
        close_size = abs(pos_size)

        hl.cancel_all_orders(hl_account)
        time.sleep(0.3)

        ask, bid, _ = hl.ask_bid(HEDGE_SYMBOL)

        if is_buy:
            close_px = round(ask + 50.0, 0)
        else:
            close_px = round(bid - 50.0, 0)

        side_str = "LONG" if is_long else "SHORT"
        close_side = "BUY" if is_buy else "SELL"
        print(colored(f"\n   CLOSING HEDGE (attempt {attempt+1}): {close_side} {close_size} BTC @ ${close_px:.0f} IOC (was {side_str})", "magenta", attrs=['bold']))

        exchange = Exchange(hl_account, constants.MAINNET_API_URL)
        result = exchange.order(HEDGE_SYMBOL, is_buy, close_size, close_px,
                               {"limit": {"tif": "Ioc"}}, reduce_only=True)

        if result and 'response' in result:
            statuses = result['response'].get('data', {}).get('statuses', [])
            if statuses and 'filled' in statuses[0]:
                print(colored(f"   HEDGE CLOSED!", "green", attrs=['bold']))
                return

        time.sleep(1)

    print(colored(f"   Could not close hedge after 5 attempts!", "red"))

# ============================================================================
# MAIN BOT CLASS
# ============================================================================

class CVDStinkBot:
    def __init__(self):
        self.current_market_ts = None
        self.market_info = None
        self.signal_fired = False
        self.signal_type = None
        self.signal_direction = None
        self.signal_detail = ""
        self.target_outcome = None
        self.target_token_id = None
        self.signal_price = 0
        self.stink_bid_price = 0
        self.stink_bid_shares = 0
        self.order_placed = False
        self.poly_filled = False
        self.hedge_filled = False

    def reset(self):
        """Reset state for next market"""
        self.current_market_ts = None
        self.market_info = None
        self.signal_fired = False
        self.signal_type = None
        self.signal_direction = None
        self.signal_detail = ""
        self.target_outcome = None
        self.target_token_id = None
        self.signal_price = 0
        self.stink_bid_price = 0
        self.stink_bid_shares = 0
        self.order_placed = False
        self.poly_filled = False
        self.hedge_filled = False

    def place_stink_bid(self):
        """Place stink bid at PULLBACK_PCT below signal price"""
        token_id = self.target_token_id
        outcome = self.target_outcome

        book = get_order_book(token_id)
        if not book:
            print(colored(f"   No order book for {outcome}, market may be closed", "yellow"))
            return False

        self.signal_price = book['best_bid']
        self.stink_bid_price = round(self.signal_price * (1 - PULLBACK_PCT), 4)

        if self.stink_bid_price < 0.01:
            self.stink_bid_price = 0.01

        self.stink_bid_shares = calculate_shares(POLY_USD_PER_POSITION, self.stink_bid_price)
        if self.stink_bid_shares <= 0:
            return False

        print(colored(f"\n   CVD STINK BID: {outcome}", "yellow", attrs=['bold']))
        print(colored(f"   Signal:         {self.signal_type}", "magenta"))
        print(colored(f"   Signal price:   ${self.signal_price:.4f}", "white"))
        print(colored(f"   Pullback:       {PULLBACK_PCT*100:.0f}%", "white"))
        print(colored(f"   Stink bid at:   ${self.stink_bid_price:.4f}", "green", attrs=['bold']))
        print(colored(f"   Shares:         {self.stink_bid_shares}", "white"))

        cancel_token_orders(token_id)
        time.sleep(0.5)

        neg_risk = self.market_info.get('neg_risk', False)
        response = place_limit_order(
            token_id=token_id,
            side="BUY",
            price=self.stink_bid_price,
            size=self.stink_bid_shares,
            neg_risk=neg_risk,
        )

        if response and 'orderID' in response:
            print(colored(f"   CVD stink bid placed!", "green"))
            self.order_placed = True
            return True
        return False

    def check_for_fill(self):
        """Check if stink bid filled"""
        if self.poly_filled:
            return True
        if not self.target_token_id:
            return False

        if check_poly_filled(self.target_token_id):
            print(colored(f"\n   CVD STINK BID FILLED! {self.target_outcome} @ ${self.stink_bid_price:.4f}", "green", attrs=['bold']))
            self.poly_filled = True
            return True
        return False

    def cancel_orders(self):
        """Cancel unfilled stink bids"""
        if self.target_token_id and self.order_placed and not self.poly_filled:
            cancel_token_orders(self.target_token_id)

    def run_market_cycle(self, market_ts):
        """Run one complete 5-minute market cycle"""
        self.current_market_ts = market_ts
        market_dt = datetime.fromtimestamp(market_ts, tz=timezone.utc)
        market_et = datetime.fromtimestamp(market_ts, tz=ET)

        print(colored(f"\n{'='*70}", "cyan"))
        print(colored(f"CVD 5-MIN MARKET CYCLE", "cyan", attrs=['bold']))
        print(colored(f"   Market time: {market_et.strftime('%I:%M:%S%p ET')}", "white"))
        print(colored(f"{'='*70}", "cyan"))

        time_remaining = get_time_remaining(market_ts)
        if time_remaining > MARKET_DURATION - 10:
            time.sleep(3)

        self.market_info = None
        for attempt in range(5):
            self.market_info = get_market_info(market_ts)
            if self.market_info:
                break
            time.sleep(2)

        if not self.market_info:
            return

        while True:
            time_remaining = get_time_remaining(market_ts)

            if time_remaining <= 0:
                self.cancel_orders()
                if self.hedge_filled:
                    close_hyperliquid_hedge()
                if self.order_placed and not self.poly_filled:
                    log_trade(self.signal_type or "NONE", self.target_outcome or "NONE",
                              self.signal_detail, self.signal_price, self.stink_bid_price,
                              self.stink_bid_shares, "", 0, 0, "TIME_EXPIRED", "Market ended before fill")
                break

            if time_remaining < MIN_TIME_LEFT and self.order_placed and not self.poly_filled:
                self.cancel_orders()
                log_trade(self.signal_type or "NONE", self.target_outcome or "NONE",
                          self.signal_detail, self.signal_price, self.stink_bid_price,
                          self.stink_bid_shares, "", 0, 0, "CANCELLED", f"< {MIN_TIME_LEFT}s remaining")
                break

            if self.poly_filled:
                time.sleep(2)
                continue

            if self.order_placed and not self.poly_filled:
                if self.check_for_fill():
                    hedge_ok, hedge_side, hedge_size, hedge_price = fill_hyperliquid_hedge(self.target_outcome)

                    if hedge_ok:
                        result = "BOTH_FILLED"
                        self.hedge_filled = True
                    else:
                        result = "POLY_ONLY"

                    log_trade(self.signal_type, self.target_outcome, self.signal_detail,
                              self.signal_price, self.stink_bid_price, self.stink_bid_shares,
                              hedge_side if hedge_ok else "", hedge_size, hedge_price, result)
                    continue

                time.sleep(2)
                continue

            if not self.signal_fired and time_remaining > MIN_TIME_LEFT:
                direction, signal_type, detail = check_cvd_signal()

                if direction:
                    self.signal_fired = True
                    self.signal_type = signal_type
                    self.signal_direction = direction
                    self.signal_detail = detail

                    if direction == "UP":
                        self.target_outcome = "UP"
                        self.target_token_id = self.market_info['up_token_id']
                    else:
                        self.target_outcome = "DOWN"
                        self.target_token_id = self.market_info['down_token_id']

                    self.place_stink_bid()

            time.sleep(BOT_POLL_INTERVAL)

# ============================================================================
# MAIN ENTRY
# ============================================================================

def main():
    print(colored("""
+==============================================================================+
|     MOON DEV's CVD 5-MINUTE BOT v1.0                                         |
|     CVD Divergence -> Polymarket Stink Bids + Hyperliquid Hedge              |
|     BTC 5-Min Markets | Order Flow Alpha | Pullback Entry                    |
+==============================================================================+
    """, "cyan", attrs=['bold']))

    print(colored(f"CVD Configuration:", "yellow", attrs=['bold']))
    print(colored(f"   Signal TFs:        {', '.join(CVD_SIGNAL_TIMEFRAMES)}", "white"))
    print(colored(f"   Primary TF:        {CVD_PRIMARY_TF}", "white"))
    print(colored(f"   Pullback:          {PULLBACK_PCT*100:.0f}%", "white"))
    print(colored(f"   Polymarket:        ${POLY_USD_PER_POSITION}/position", "white"))
    print(colored(f"   Hyperliquid:       ${HEDGE_USD} inverse hedge ({HEDGE_LEVERAGE}x leverage)", "white"))
    print()

    print_trade_summary()

    hl_info = Info(constants.MAINNET_API_URL, skip_ws=True)
    hl_state = hl_info.user_state(hl_account.address)
    hl_balance = float(hl_state["marginSummary"]["accountValue"])
    print(colored(f"   Hyperliquid:     ${hl_balance:,.2f}", "green"))

    tick_response = api.get_ticks("BTC", "1h", limit=10000)
    if tick_response and isinstance(tick_response, dict):
        all_ticks = tick_response.get('ticks', [])
        print(colored(f"   Fetched {len(all_ticks)} ticks from 1h window", "cyan"))
        for tf in CVD_SIGNAL_TIMEFRAMES:
            sliced = slice_ticks_by_time(all_ticks, TF_SECONDS[tf])
            cvd_val, price_chg, _, _ = compute_tick_cvd(sliced)
            print(colored(f"   BTC CVD [{tf}]: {cvd_val:+d} | Price: {price_chg:+.3f}%", "cyan"))
    print()

    print(colored(f"CVD 5-MINUTE BOT LIVE!", "green", attrs=['bold']))

    bot = CVDStinkBot()

    while True:
        try:
            market_ts = get_current_market_timestamp()
            time_remaining = get_time_remaining(market_ts)

            if time_remaining < MIN_TIME_LEFT + 30:
                next_ts = market_ts + MARKET_DURATION
                wait_time = next_ts - int(time.time())
                if wait_time > 0:
                    next_dt = datetime.fromtimestamp(next_ts, tz=ET)
                    print(colored(f"\nWaiting {wait_time}s for next market ({next_dt.strftime('%I:%M:%S%p ET')})...", "yellow"))
                    time.sleep(wait_time + 1)
                market_ts = get_current_market_timestamp()

            bot.reset()
            bot.run_market_cycle(market_ts)

        except KeyboardInterrupt:
            print(colored(f"\nCVD Bot stopped!", "yellow", attrs=['bold']))
            bot.cancel_orders()
            break
        except Exception as e:
            print(colored(f"\n   Hiccup: {str(e)[:80]}, back in 5s...", "yellow"))
            time.sleep(5)

if __name__ == "__main__":
    print("Moon Dev's CVD 5-Minute Bot - Order flow alpha, let's go!")
    main()
```
## Prerequisites & Setup

This bot requires accounts on two exchanges and a Moon Dev API key. Here's everything you need:

### Required Setup

**1. Polymarket Account** — Funded with USDC on Polygon. Set up API credentials at polymarket.com.

**2. Hyperliquid Account** — Funded with USDC margin for the hedge leg. You need an API key (ETH private key) for programmatic trading.

**3. Moon Dev API Key** — For tick data and order flow signals. Get one at moondev.com.

**4. Python Environment** — Python 3.10+ with conda (or venv). Install deps: pip install requests pandas python-dotenv termcolor web3 py-clob-client eth-account hyperliquid-python-sdk

**5. .env File** — Create a .env file with all required keys (see template below)

.env file template

```python
PRIVATE_KEY=your_polymarket_private_key_here
PUBLIC_KEY=your_polygon_wallet_address_here
API_KEY=your_polymarket_api_key
SECRET=your_polymarket_api_secret
PASSPHRASE=your_polymarket_api_passphrase
HYPER_LIQUID_KEY=your_hyperliquid_eth_private_key
MOONDEV_API_KEY=your_moondev_api_key
```
## Want to learn more?

Join the live Zoom calls where Moon Dev walks through these bots in real time and answers your questions.

[Join the Live Zoom Call](https://moondev.com/t/blog/cvd-five-minute-bot)

Built with love by Moon Dev

### Related Resources

[Polymarket 5-Minute Bot — Easy Hyper Gambler](https://moondev.com/polymarket-five-minute-bot)

— The keyboard-controlled version for manual BTC 5-minute market trading

[Polymarket Hyperliquid Liquidation Statistical Arbitrage](https://moondev.com/polymarket-hyperliquid-liquidation-statistical-arbitrage)

— Advanced bot that uses liquidation data to trade Polymarket and hedge on Hyperliquid

[HIP3 Liquidation Trading Bot](https://moondev.com/hip-3-liquidation-trading-bot)

— Trade liquidation cascades on HIP3 automatically

[HIP3 Funding Rate Scanner](https://moondev.com/hip-3-funding-rate-scanner)

— Scan every funding rate on Hyperliquid including HIP3 tokenized assets

[Moon Dev API Documentation](https://moondev.com/docs)

— Tick data, liquidation data, funding rates, position snapshots, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations across exchanges
