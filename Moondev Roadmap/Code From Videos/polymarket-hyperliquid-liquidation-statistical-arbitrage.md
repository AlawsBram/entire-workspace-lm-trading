<!-- source: https://moondev.com/polymarket-hyperliquid-liquidation-statistical-arbitrage -->
<!-- captured: 2026-10-07 -->
<!-- title: Polymarket Hyperliquid Liquidation Statistical Arbitrage -->

Polymarket Hyperliquid Liquidation Statistical Arbitrage Bot | Open Source Python Tool | Moon Dev

Moon Dev Open Source

# Liquidation Stink Bids on Polymarket, Hedged on Hyperliquid

This bot watches BTC liquidations across every exchange via the Moon Dev API. When a liquidation cascade hits the sweet spot, it places a pullback stink bid on Polymarket's 5-minute BTC Up/Down markets — then hedges 40% inverse on Hyperliquid. Statistical arbitrage between a prediction market and a perpetual futures exchange.

By Moon Dev · March 11, 2026

## The Strategy: Liquidation Cascades Meet Prediction Markets

When a wave of BTC long positions gets liquidated, the price drops. When a wave of shorts gets liquidated, price rips up. These cascades are visible in real time through liquidation data. The question is: how do you trade it?

This bot uses a two-leg approach. **Leg 1** is Polymarket — specifically their BTC 5-minute Up/Down binary markets. When $25K+ of BTC longs get liquidated (bearish), the bot places a stink bid on the DOWN outcome. When $25K+ of shorts get liquidated (bullish), it bids on UP. But it doesn't chase — it places the bid at a **30% pullback** from the current price, waiting for a flash wick to fill it.

**Leg 2** is the hedge. Once the Polymarket position fills, the bot immediately opens an inverse position on Hyperliquid. If it bought DOWN on Polymarket, it goes LONG BTC on Hyperliquid. If it bought UP, it goes SHORT. This creates a statistical arbitrage — you're hedged across two completely different venues.

### Why This Works

Polymarket binary options and Hyperliquid perpetual futures price the same event differently. During a liquidation cascade, Polymarket's 5-minute markets can misprice wildly — the stink bid catches those flash dislocations. The Hyperliquid hedge means you're not naked if the market reverses. You're exploiting the **pricing gap between two venues** during high-volatility liquidation events. The 60/40 split (Polymarket/Hyperliquid) keeps the exposure balanced while maximizing the prediction market edge.

Let me walk you through every piece of this bot so you understand exactly how it works.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

## Step 1: The Imports

This bot connects to three different systems — the Moon Dev API for liquidation data, Polymarket for binary options, and Hyperliquid for perpetual futures hedging. That means we need SDKs for both exchanges plus standard libraries for HTTP, data handling, and wallet management.

Imports and SDK setup

```python
import sys
import os
import io
import time
import math
import json
import requests
import pandas as pd
import eth_account
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from termcolor import colored
from web3 import Web3

# Hyperliquid SDK
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Polymarket SDK
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
from py_clob_client.constants import POLYGON

# Load .env from same directory or parent
load_dotenv()
```
The py_clob_client is Polymarket's official Python SDK for their Central Limit Order Book. The hyperliquid SDK handles order placement and position management on Hyperliquid. Both exchanges use Ethereum-style private keys for authentication, which is why we need eth_account and web3.

## Step 2: The Configuration

This is where the strategy lives. Every tunable parameter is right here — liquidation thresholds, pullback percentage, position sizing, hedge ratios. These are the knobs you turn to adapt the strategy.

Configuration block

```python
# --- Bot Speed ---
BOT_POLL_INTERVAL = 10              # Seconds between each cycle check

# --- Liquidation Signal ---
LIQUIDATION_THRESHOLD_MIN = 25_000  # $25K minimum - front end of momentum
LIQUIDATION_THRESHOLD_MAX = 100_000 # $100K maximum - above this we missed the wave
LIQUIDATION_TIMEFRAME = "10m"       # Check 10-minute window from Moon Dev API

# --- Stink Bid Entry ---
PULLBACK_PCT = 0.30                 # 30% pullback from signal price (THE KEY VARIABLE)
MIN_TIME_LEFT = 60                  # Cancel orders if < 60 seconds left on market

# --- Polymarket Sizing (60% of total exposure) ---
POLY_USD_PER_POSITION = 15.0       # USD per Polymarket position

# --- Hyperliquid Hedge (40% of total exposure) ---
HEDGE_USD = 10.0                   # Fixed $10 USD on Hyperliquid
HEDGE_LEVERAGE = 3                 # Leverage on Hyperliquid
HEDGE_SYMBOL = "BTC"               # Only hedging BTC

# --- Market Timing ---
MARKET_DURATION = 300               # 5-minute markets = 300 seconds
```
PULLBACK_PCT is the most important variable. At 0.30 (30%), if the DOWN outcome is trading at $0.50 when the signal fires, the bot places a stink bid at $0.35. This means you only get filled on a flash wick — a momentary price dislocation that snaps back. Most stink bids won't fill, and that's the point. You're fishing for mispriced entries.

The liquidation thresholds define a **sweet spot window**. Below $25K, there's not enough momentum to signal a directional move. Above $100K, the cascade already happened and you missed the front of the wave. The bot only fires when liquidations are between these bounds.

The 60/40 split — $15 on Polymarket, $10 on Hyperliquid — keeps the hedge proportional. Total exposure per trade is $25. Adjust these up or down based on your risk appetite.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

## Step 3: Account Setup and API Keys

The bot needs four credentials: a Hyperliquid private key, a Moon Dev API key for liquidation data, and a Polymarket private key plus public address. All stored securely in your .env file.

Account initialization

```python
# Hyperliquid account
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')
hl_account = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Moon Dev API
MOONDEV_API_KEY = os.getenv('MOONDEV_API_KEY')

# Polymarket credentials
POLY_PRIVATE_KEY = os.getenv('PRIVATE_KEY')
POLY_PUBLIC_KEY = os.getenv('PUBLIC_KEY')
```
Each credential is validated on startup — if any key is missing, the bot exits immediately with a clear error message. The Hyperliquid key gets converted into an eth_account.Account object that the SDK uses to sign transactions. Polymarket requires both the private key (for signing orders) and the public address (for querying positions).

## Step 4: Moon Dev API — Liquidation Data

The liquidation data comes from the Moon Dev API, which aggregates liquidations across all major exchanges — Binance, Bybit, OKX, and Hyperliquid — into a single feed. Two simple functions handle the API calls.

Moon Dev API functions

```python
def moondev_api_get(endpoint):
    """Make authenticated GET request to Moon Dev API"""
    url = f"https://api.moondev.com{endpoint}"
    headers = {'X-API-Key': MOONDEV_API_KEY}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def get_all_liquidations(timeframe="10m"):
    """Get combined liquidations from ALL exchanges"""
    return moondev_api_get(f"/api/all_liquidations/{timeframe}.json")
```
The /api/all_liquidations/10m.json endpoint returns all liquidation events from the last 10 minutes, combined across every exchange. This is critical — a liquidation on Binance affects BTC price globally, not just on Binance. You need the aggregate view.

[If you don't have a Moon Dev API key yet, get one at [moondev.com](https://moondev.com)

. The liquidation endpoints require authentication.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

## Step 5: Polymarket — Orders, Positions, and Market Discovery

The Polymarket integration handles four things: authenticating with the CLOB, looking up token IDs for specific markets, calculating share sizes, and placing limit orders. Here's the client setup and the share calculator.

Polymarket client and share calculator

```python
def _get_poly_client():
    """Create authenticated Polymarket CLOB client"""
    wallet = Web3.to_checksum_address(POLY_PUBLIC_KEY)
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=POLY_PRIVATE_KEY,
        chain_id=POLYGON,
        funder=wallet,
        signature_type=1
    )
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds=creds)
    return client

def calculate_shares(dollar_amount, price):
    """Calculate shares from dollar amount and price.
    Enforces Polymarket minimums: $1.00 order size AND 5 shares minimum"""
    if price <= 0:
        return 0.0

    shares = dollar_amount / price
    shares_rounded = round(shares, 1)

    # Enforce 5 share minimum (Polymarket requirement)
    if shares_rounded < 5.0:
        shares_rounded = 5.0

    total_cost = shares_rounded * price

    # If total cost is under $1, increase shares to meet $1 minimum
    if total_cost < 1.0:
        shares_for_dollar = 1.0 / price
        shares_rounded = max(shares_for_dollar, 5.0)
        shares_rounded = round(shares_rounded, 1)

    return shares_rounded
```
Polymarket has two minimums that catch people: orders must be at least **$1.00 total** and at least **5 shares**. The calculate_shares function handles both constraints automatically. If you're buying at $0.10 per share, you need at least 10 shares to meet the $1 minimum.

The CLOB client authenticates using your Ethereum private key and derives API credentials on the fly. Polymarket runs on Polygon, which is why you see chain_id=POLYGON in the setup.

## Step 6: Finding the Active 5-Minute Market

Polymarket's BTC 5-minute Up/Down markets roll continuously — a new one starts every 5 minutes. The bot needs to find the currently active market, get its token IDs for the UP and DOWN outcomes, and track how much time is left.

Market discovery

```python
def get_current_market_timestamp():
    """Get the timestamp for the current active 5-minute market"""
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    """Seconds remaining in current market"""
    now = int(time.time())
    return MARKET_DURATION - (now - market_ts)

def get_market_info(market_ts):
    """Get market ID and token IDs for a BTC 5-min market.
    Market slug format: btc-updown-5m-{timestamp}"""
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

    # For BTC UP/DOWN markets:
    # UP = NO token, DOWN = YES token (swapped on Polymarket!)
    up_token_id = token_data[2]    # NO token = UP
    down_token_id = token_data[1]  # YES token = DOWN

    return {
        'market_id': market_id,
        'up_token_id': up_token_id,
        'down_token_id': down_token_id,
        'question': market['question'],
        'slug': market_slug,
    }
```
The get_current_market_timestamp function uses integer division to snap to the current 5-minute boundary. If it's 14:07:32, the market timestamp is the one that started at 14:05:00. This is how Polymarket's rolling markets work — each one is identified by its start timestamp.

Watch the token mapping: on Polymarket's BTC Up/Down markets, the YES token is actually DOWN and the NO token is UP. The bot handles this swap so you don't have to think about it.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

## Step 7: The Liquidation Scanner

This is the signal engine. It pulls BTC liquidation data from the Moon Dev API, separates longs from shorts, and checks if the amounts fall within the sweet spot window. The "front of the wave" filter is what makes this work — you want to catch the start of a cascade, not the end.

Liquidation signal detection

```python
def get_btc_liquidations():
    """Get BTC liquidations from Moon Dev API (all exchanges combined).
    Returns (btc_long_liq_usd, btc_short_liq_usd)"""
    data = get_all_liquidations(LIQUIDATION_TIMEFRAME)
    if not data:
        return 0, 0

    liqs = data.get('liquidations', data.get('data', []))
    if isinstance(liqs, list):
        long_total = 0
        short_total = 0
        for liq in liqs:
            coin = str(liq.get('coin', liq.get('symbol', ''))).upper()
            if coin != 'BTC':
                continue
            value = float(liq.get('value_usd', liq.get('value', liq.get('usd_value', 0))))
            side = str(liq.get('side', liq.get('direction', ''))).upper()
            if side in ('LONG', 'SELL', 'B'):
                long_total += value
            elif side in ('SHORT', 'BUY', 'S'):
                short_total += value
        return long_total, short_total

    return 0, 0

def check_liquidation_signal():
    """Check for new BTC liquidation signal.
    Returns: ('LONG_LIQ', amount) or ('SHORT_LIQ', amount) or (None, 0)

    LONG liquidations = bearish = we want DOWN
    SHORT liquidations = bullish = we want UP"""
    long_liq, short_liq = get_btc_liquidations()

    # FRONT END OF MOMENTUM FILTER
    # Signal only fires when liquidations are BETWEEN min and max
    if (long_liq >= LIQUIDATION_THRESHOLD_MIN
        and long_liq <= LIQUIDATION_THRESHOLD_MAX
        and long_liq > short_liq):
        return 'LONG_LIQ', long_liq

    elif (short_liq >= LIQUIDATION_THRESHOLD_MIN
          and short_liq <= LIQUIDATION_THRESHOLD_MAX
          and short_liq > long_liq):
        return 'SHORT_LIQ', short_liq

    return None, 0
```
The signal logic is straightforward: **$25K+ in long liquidations** means longs are getting rekt, price is dropping, so the bot wants to buy DOWN. **$25K+ in short liquidations** means shorts are getting squeezed, price is pumping, so it wants UP.

The upper bound at $100K is the "missed the wave" filter. If you're seeing $200K in liquidations, that cascade already moved the market — the opportunity window has passed. You want to catch it when it's $25K-$100K, the front end of the momentum.

The function also requires that the dominant side's liquidations exceed the other side. If longs and shorts are getting liquidated equally, there's no directional signal — the market is choppy, not cascading.

## Step 8: Placing the Stink Bid

When a liquidation signal fires, the bot doesn't market buy. It places a limit order at a 30% discount to the current price — the stink bid. This is the core edge: you only get filled when the market flash-wicks in your favor.

Stink bid placement

```python
def place_stink_bid(self):
    """Place stink bid at PULLBACK_PCT below signal price"""
    token_id = self.target_token_id
    outcome = self.target_outcome

    book = get_order_book(token_id)
    if not book:
        return False

    self.signal_price = book['best_ask']

    # Stink bid at PULLBACK_PCT below current price
    self.stink_bid_price = round(self.signal_price * (1 - PULLBACK_PCT), 4)
    if self.stink_bid_price < 0.01:
        self.stink_bid_price = 0.01

    self.stink_bid_shares = calculate_shares(POLY_USD_PER_POSITION, self.stink_bid_price)
    if self.stink_bid_shares <= 0:
        return False

    # Cancel any existing orders, then place the stink bid
    cancel_token_orders(token_id)
    time.sleep(0.5)

    response = place_limit_order(
        token_id=token_id,
        side="BUY",
        price=self.stink_bid_price,
        size=self.stink_bid_shares,
    )

    if response and 'orderID' in response:
        self.order_placed = True
        return True

    return False
```
Here's the math: if DOWN is trading at $0.50 and PULLBACK_PCT is 0.30, the stink bid goes in at $0.35. That's a 30% discount. The bot is saying: "I'll only buy this if the market panics hard enough to give me a 30% better price."

Most of these bids won't fill. And that's fine — with 288 five-minute markets per day, you're casting a wide net. When a flash wick does hit your bid, you're getting an entry price that's significantly mispriced relative to fair value.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

## Step 9: The Hyperliquid Hedge

Once the Polymarket stink bid fills, the bot immediately opens an inverse position on Hyperliquid. This is the hedge leg — it protects you if the market moves against your Polymarket position.

Hyperliquid hedge execution

```python
def fill_hyperliquid_hedge(poly_outcome):
    """Place inverse hedge on Hyperliquid. Loops until filled.
    If Polymarket outcome is "UP"   -> SHORT BTC on HL
    If Polymarket outcome is "DOWN" -> LONG BTC on HL"""
    if poly_outcome.upper() == "UP":
        is_buy = False
        hedge_side = "SHORT"
    elif poly_outcome.upper() == "DOWN":
        is_buy = True
        hedge_side = "LONG"
    else:
        return False, "UNKNOWN", 0, 0

    exchange = Exchange(hl_account, constants.MAINNET_API_URL)
    exchange.update_leverage(HEDGE_LEVERAGE, HEDGE_SYMBOL, is_cross=False)

    for attempt in range(1, HEDGE_MAX_ATTEMPTS + 1):
        ask, bid, _ = hl_ask_bid(HEDGE_SYMBOL)
        mid_price = (ask + bid) / 2
        btc_size = (HEDGE_USD * HEDGE_LEVERAGE) / mid_price

        sz_decimals = hl_get_sz_px_decimals(HEDGE_SYMBOL)[0]
        factor = 10 ** sz_decimals
        btc_size = math.ceil(btc_size * factor) / factor

        # Walk the price toward market each attempt
        if is_buy:
            limit_px = bid + (ask - bid) * HEDGE_PRICE_BUMP_PCT * attempt
            limit_px = min(limit_px, ask)
        else:
            limit_px = ask - (ask - bid) * HEDGE_PRICE_BUMP_PCT * attempt
            limit_px = max(limit_px, bid)

        hl_cancel_all_orders(hl_account)
        result = hl_limit_order(HEDGE_SYMBOL, is_buy, btc_size, limit_px, False, hl_account)

        # Check if filled
        if result and 'response' in result:
            statuses = result['response'].get('data', {}).get('statuses', [])
            if statuses and 'filled' in statuses[0]:
                return True, hedge_side, btc_size, limit_px

        time.sleep(HEDGE_FILL_WAIT)

        # Also check position directly
        positions, in_pos, pos_size, _, entry_px, _, is_long = hl_get_position(HEDGE_SYMBOL, hl_account)
        if in_pos and abs(pos_size) > 0:
            actual_side = "LONG" if is_long else "SHORT"
            return True, actual_side, abs(pos_size), entry_px

    return False, hedge_side, 0, 0
```
The hedge uses a **progressive limit order** approach. On each attempt, the price bumps 0.1% closer to the market. This avoids paying unnecessary spread while ensuring the hedge fills quickly. Up to 10 attempts over ~20 seconds.

The inverse logic is key: if you bought **UP on Polymarket** (you think price goes up), you **SHORT on Hyperliquid**. If you bought **DOWN on Polymarket** (you think price drops), you **LONG on Hyperliquid**. This creates the statistical arbitrage — you're expressing the same view on two different venues with different pricing.

Leverage is set to 3x isolated on Hyperliquid. Isolated margin means only the $10 hedge is at risk, not your entire Hyperliquid account.

## Step 10: The Main Bot Loop

The bot runs in a continuous loop, cycling through one 5-minute market at a time. Each cycle follows the same flow: find the market, poll for liquidation signals, place stink bids on signal, monitor for fills, hedge on fill, cancel if time runs out.

Main bot cycle

```python
def run_market_cycle(self, market_ts):
    """Run one complete 5-minute market cycle"""
    self.current_market_ts = market_ts

    # Find market
    self.market_info = get_market_info(market_ts)
    if not self.market_info:
        return

    # Main polling loop
    while True:
        time_remaining = get_time_remaining(market_ts)

        if time_remaining <= 0:
            self.cancel_orders()
            break

        if time_remaining < MIN_TIME_LEFT and self.order_placed and not self.poly_filled:
            self.cancel_orders()
            break

        # If already filled, hold to expiry
        if self.poly_filled:
            time.sleep(2)
            continue

        # Check if stink bid filled
        if self.order_placed and not self.poly_filled:
            if self.check_for_fill():
                # HEDGE LEG
                hedge_ok, hedge_side, hedge_size, hedge_price = fill_hyperliquid_hedge(self.target_outcome)
                log_trade(...)
                continue

        # Poll for liquidation signal
        if not self.signal_fired and time_remaining > MIN_TIME_LEFT:
            signal_type, signal_amount = check_liquidation_signal()
            if signal_type:
                self.signal_fired = True
                if signal_type == 'LONG_LIQ':
                    self.target_outcome = "DOWN"
                    self.target_token_id = self.market_info['down_token_id']
                else:
                    self.target_outcome = "UP"
                    self.target_token_id = self.market_info['up_token_id']
                self.place_stink_bid()

        time.sleep(BOT_POLL_INTERVAL)
```
The state machine is clean: **no signal yet** → poll for liquidations → **signal fired** → place stink bid → **bid placed** → monitor for fill → **filled** → hedge on Hyperliquid → **hedged** → hold to expiry. If time runs out at any point before the fill, cancel and move to the next market.

The MIN_TIME_LEFT guard at 60 seconds prevents the bot from placing orders that can't reasonably fill and hedge before the market expires. No point placing a stink bid with 30 seconds left.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

## Step 11: Trade Logging

Every signal, fill, and hedge gets logged to a CSV file using pandas. This gives you a complete audit trail to analyze your strategy's performance over time.

Trade logging

```python
def log_trade(signal_type, signal_amount, outcome, poly_price, stink_price,
              poly_shares, hedge_side, hedge_size, hedge_price, result, reason=""):
    """Log trade to CSV using pandas"""
    os.makedirs(DATA_DIR, exist_ok=True)

    new_row = pd.DataFrame([{
        'timestamp': datetime.now().isoformat(),
        'signal_type': signal_type,
        'signal_amount_usd': round(signal_amount, 2),
        'outcome': outcome,
        'signal_price': round(poly_price, 4) if poly_price else 0,
        'stink_bid_price': round(stink_price, 4) if stink_price else 0,
        'pullback_pct': PULLBACK_PCT,
        'poly_shares': round(poly_shares, 2) if poly_shares else 0,
        'poly_usd': round(stink_price * poly_shares, 4) if stink_price and poly_shares else 0,
        'hedge_side': hedge_side,
        'hedge_size_btc': round(hedge_size, 6) if hedge_size else 0,
        'hedge_price': round(hedge_price, 2) if hedge_price else 0,
        'hedge_usd': round(hedge_size * hedge_price, 4) if hedge_size and hedge_price else 0,
        'result': result,
        'reason': reason,
    }])

    if os.path.exists(TRADE_LOG_FILE):
        existing = pd.read_csv(TRADE_LOG_FILE)
        df = pd.concat([existing, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(TRADE_LOG_FILE, index=False)
```
Each row captures the full context: what signal triggered the trade, what price you bid at versus the signal price, whether both legs filled or just Polymarket, and the hedge details. The result column tracks outcomes like BOTH_FILLED, POLY_ONLY, TIME_EXPIRED, or CANCELLED. Over time, you can analyze fill rates, average pullback depths, and hedge success rates to tune the strategy.

## Running the Bot

Set up your .env file with all four keys and you're ready to go.

.env file

```python
PRIVATE_KEY=your_polymarket_private_key
PUBLIC_KEY=your_polymarket_public_address
HYPER_LIQUID_KEY=your_hyperliquid_private_key
MOONDEV_API_KEY=your_moondev_api_key
```
Install dependencies and run

```python
pip install requests pandas python-dotenv termcolor eth-account web3 py-clob-client hyperliquid-python-sdk
python liq_stink_bot.py
```
On startup, the bot validates all credentials, checks your Hyperliquid balance and existing positions, tests the Moon Dev API connection, then enters the main loop. Every 5 minutes it picks up a new market and starts scanning for liquidation signals.

Most cycles will be quiet — no liquidation signal fires, and the bot waits for the next market. When a signal does fire, you'll see the stink bid placed with full details: signal price, pullback percentage, stink bid price, and share count. If the stink bid fills, the hedge leg kicks in immediately on Hyperliquid.

## Full Source Code

Here's the complete bot in one block if you just want to grab it and go.

liq_stink_bot.py (full)

```python
#!/usr/bin/env python3
"""
================================================================================
MOON DEV's LIQUIDATION STINK BID BOT v1.0 (STANDALONE)
================================================================================
Uses Moon Dev API liquidation data to trade BTC 5-minute Up/Down markets
on Polymarket with a pullback (stink bid) entry, then hedges 40% on Hyperliquid.

STRATEGY:
  1. Watch Moon Dev API for BTC liquidations (all exchanges combined)
  2. $25K+ BTC LONG liquidations  -> bearish signal -> buy DOWN on Polymarket
     $25K+ BTC SHORT liquidations -> bullish signal -> buy UP on Polymarket
  3. DON'T chase -- place a stink bid at PULLBACK_PCT below the signal price
     Example: DOWN is $0.50 at signal -> stink bid at $0.35 (30% discount)
  4. Cancel orders if < MIN_TIME_LEFT seconds remain on the market
  5. Once Polymarket leg fills -> hedge 40% inverse on Hyperliquid

REQUIRED PACKAGES:
  pip install requests pandas python-dotenv termcolor eth-account web3
  pip install py-clob-client hyperliquid-python-sdk

REQUIRED .ENV FILE:
  PRIVATE_KEY=your_polymarket_private_key
  PUBLIC_KEY=your_polymarket_public_address
  HYPER_LIQUID_KEY=your_hyperliquid_private_key
  MOONDEV_API_KEY=your_moondev_api_key

GET YOUR MOON DEV API KEY: https://moondev.com

Built by Moon Dev
================================================================================
"""

import sys
import os
import io
import time
import math
import json
import requests
import pandas as pd
import eth_account
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from termcolor import colored
from web3 import Web3

# Hyperliquid SDK
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Polymarket SDK
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
from py_clob_client.constants import POLYGON

# Load .env from same directory or parent
load_dotenv()

# ============================================================================
# CONFIGURATION (CHANGE THESE!)
# ============================================================================

# --- Bot Speed (CHANGE THIS IF NEEDED) ---
BOT_POLL_INTERVAL = 10              # Seconds between each cycle check (10s = fast)

# --- Liquidation Signal ---
LIQUIDATION_THRESHOLD_MIN = 25_000  # $25K minimum - front end of momentum
LIQUIDATION_THRESHOLD_MAX = 100_000 # $100K maximum - if above this we missed the wave
LIQUIDATION_TIMEFRAME = "10m"       # Check 10-minute window from Moon Dev API

# --- Stink Bid Entry ---
PULLBACK_PCT = 0.30                 # 30% pullback from signal price (THE KEY VARIABLE)
MIN_TIME_LEFT = 60                  # Cancel orders if < 60 seconds left on market

# --- Polymarket Sizing (60% of total exposure) ---
POLY_USD_PER_POSITION = 15.0       # USD per Polymarket position

# --- Hyperliquid Hedge (40% of total exposure) ---
HEDGE_USD = 10.0                   # Fixed $10 USD on Hyperliquid
HEDGE_LEVERAGE = 3                 # Leverage on Hyperliquid
HEDGE_SYMBOL = "BTC"               # Only hedging BTC
HEDGE_FILL_WAIT = 2                # Seconds between fill checks (fast!)
HEDGE_MAX_ATTEMPTS = 10            # Max attempts to fill hedge
HEDGE_PRICE_BUMP_PCT = 0.001       # Bump 0.1% per attempt toward market

# --- Market Timing ---
MARKET_DURATION = 300               # 5-minute markets = 300 seconds

# --- Files ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TRADE_LOG_FILE = os.path.join(DATA_DIR, "liq_stink_trades.csv")

# ET timezone (UTC-5) - Moon Dev
ET = timezone(timedelta(hours=-5))

# ============================================================================
# ACCOUNT SETUP
# ============================================================================

# Hyperliquid account
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')
if not HYPER_LIQUID_KEY:
    print(colored("HYPER_LIQUID_KEY not found in .env!", "red"))
    sys.exit(1)

hl_account = eth_account.Account.from_key(HYPER_LIQUID_KEY)
print(colored(f"Hyperliquid account loaded!", "green"))

# Moon Dev API
MOONDEV_API_KEY = os.getenv('MOONDEV_API_KEY')
if not MOONDEV_API_KEY:
    print(colored("MOONDEV_API_KEY not found in .env!", "red"))
    sys.exit(1)
print(colored(f"Moon Dev API key loaded!", "green"))

# Polymarket credentials
POLY_PRIVATE_KEY = os.getenv('PRIVATE_KEY')
POLY_PUBLIC_KEY = os.getenv('PUBLIC_KEY')
if not POLY_PRIVATE_KEY or not POLY_PUBLIC_KEY:
    print(colored("PRIVATE_KEY or PUBLIC_KEY not found in .env!", "red"))
    sys.exit(1)
print(colored(f"Polymarket credentials loaded!", "green"))

# ============================================================================
# MOON DEV API
# ============================================================================

def moondev_api_get(endpoint):
    """Make authenticated GET request to Moon Dev API"""
    url = f"https://api.moondev.com{endpoint}"
    headers = {'X-API-Key': MOONDEV_API_KEY}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def get_all_liquidations(timeframe="10m"):
    """Get combined liquidations from ALL exchanges (Binance, Bybit, OKX, Hyperliquid)"""
    return moondev_api_get(f"/api/all_liquidations/{timeframe}.json")

# ============================================================================
# POLYMARKET FUNCTIONS
# ============================================================================

def _get_poly_client():
    """Create authenticated Polymarket CLOB client"""
    wallet = Web3.to_checksum_address(POLY_PUBLIC_KEY)
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=POLY_PRIVATE_KEY,
        chain_id=POLYGON,
        funder=wallet,
        signature_type=1
    )
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds=creds)
    return client

def get_token_id(market_id):
    """Get token IDs for a Polymarket market.
    Returns [market_id, yes_token_id, no_token_id]"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {'closed': 'false', 'limit': 5000}
    response = requests.get(url, params=params, timeout=10)

    if response.status_code == 200:
        df = pd.DataFrame(response.json())
        market_row = df[df['id'].astype(str) == str(market_id)]

        if not market_row.empty:
            clob_token_ids = market_row['clobTokenIds'].iloc[0]
            if not pd.isna(clob_token_ids):
                token_list = json.loads(clob_token_ids)
                if len(token_list) >= 2:
                    return [market_id, token_list[0], token_list[1]]

    # Fallback: direct market lookup
    direct_url = f"https://gamma-api.polymarket.com/markets/{market_id}"
    direct_response = requests.get(direct_url, timeout=10)
    if direct_response.status_code == 200:
        market_data = direct_response.json()
        clob_token_ids = market_data.get('clobTokenIds')
        if clob_token_ids and not pd.isna(clob_token_ids):
            token_list = json.loads(clob_token_ids)
            if len(token_list) >= 2:
                return [market_id, token_list[0], token_list[1]]

    return ['', '', '']

def calculate_shares(dollar_amount, price):
    """Calculate shares from dollar amount and price.
    Enforces Polymarket minimums: $1.00 order size AND 5 shares minimum"""
    if price <= 0:
        return 0.0

    shares = dollar_amount / price
    shares_rounded = round(shares, 1)

    if shares_rounded < 5.0:
        shares_rounded = 5.0

    total_cost = shares_rounded * price

    if total_cost < 1.0:
        shares_for_dollar = 1.0 / price
        shares_rounded = max(shares_for_dollar, 5.0)
        shares_rounded = round(shares_rounded, 1)
        total_cost = shares_rounded * price
        if total_cost < 1.0:
            shares_rounded += 0.1
            total_cost = shares_rounded * price

    if total_cost < 1.0 or shares_rounded < 5.0:
        return 0.0

    return shares_rounded

def place_limit_order(token_id, side, price, size, neg_risk=False):
    """Place a limit order on Polymarket"""
    client = _get_poly_client()

    order_args = OrderArgs(
        token_id=str(token_id),
        price=price,
        size=size,
        side=side.upper(),
        fee_rate_bps=1000
    )

    if neg_risk:
        signed_order = client.create_order(order_args, options=PartialCreateOrderOptions(neg_risk=True))
        response = client.post_order(signed_order)
        if response:
            return response

    signed_order = client.create_order(order_args)
    response = client.post_order(signed_order)

    if response:
        return response

    return {}

def cancel_token_orders(token_id):
    """Cancel all orders for a specific token"""
    client = _get_poly_client()
    client.cancel_market_orders(asset_id=str(token_id))
    return True

def get_all_positions(user_address=None):
    """Get all Polymarket positions and portfolio data"""
    if not user_address:
        user_address = POLY_PUBLIC_KEY

    positions_url = "https://data-api.polymarket.com/positions"
    params = {
        'user': user_address,
        'limit': 500,
        'sortBy': 'CURRENT',
        'sortDirection': 'DESC'
    }

    response = requests.get(positions_url, params=params, timeout=10)
    if response.status_code != 200:
        return None

    positions_data = response.json()

    enhanced_positions = []
    total_current_value = 0

    for pos in positions_data:
        current_value = pos.get('currentValue', 0)
        total_current_value += current_value

        enhanced_positions.append({
            'asset_id': pos.get('asset', ''),
            'outcome': pos.get('outcome', 'Unknown'),
            'position_size': pos.get('size', 0),
            'avg_price': pos.get('avgPrice', 0),
            'current_price': pos.get('curPrice', 0),
            'current_value': current_value,
            'redeemable': pos.get('redeemable', False),
        })

    return {
        'summary': {'total_current_value': round(total_current_value, 2)},
        'positions': enhanced_positions,
    }

# ============================================================================
# HYPERLIQUID FUNCTIONS
# ============================================================================

def hl_ask_bid(symbol):
    """Get ask/bid from Hyperliquid L2 order book"""
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    data = {'type': 'l2Book', 'coin': symbol}

    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()['levels']

    bid = float(l2_data[0][0]['px'])
    ask = float(l2_data[1][0]['px'])

    return ask, bid, l2_data

def hl_get_sz_px_decimals(symbol):
    """Get size and price decimals for a Hyperliquid symbol"""
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    data = {'type': 'meta'}

    response = requests.post(url, headers=headers, data=json.dumps(data))
    symbols = response.json()['universe']
    symbol_info = next((s for s in symbols if s['name'] == symbol), None)

    sz_decimals = symbol_info['szDecimals'] if symbol_info else 0

    ask = hl_ask_bid(symbol)[0]
    ask_str = str(ask)
    px_decimals = len(ask_str.split('.')[1]) if '.' in ask_str else 0

    return sz_decimals, px_decimals

def hl_limit_order(coin, is_buy, sz, limit_px, reduce_only, account):
    """Place a limit order on Hyperliquid"""
    exchange = Exchange(account, constants.MAINNET_API_URL)
    rounding = hl_get_sz_px_decimals(coin)[0]
    sz = round(sz, rounding)

    order_result = exchange.order(coin, is_buy, sz, limit_px, {"limit": {"tif": "Gtc"}}, reduce_only=reduce_only)
    return order_result

def hl_get_position(symbol, account):
    """Get current position info from Hyperliquid"""
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)

    for position in user_state["assetPositions"]:
        if position["position"]["coin"] == symbol and float(position["position"]["szi"]) != 0:
            size = float(position["position"]["szi"])
            entry_px = float(position["position"]["entryPx"])
            pnl_perc = float(position["position"]["returnOnEquity"]) * 100
            is_long = size > 0
            return [position["position"]], True, size, symbol, entry_px, pnl_perc, is_long

    return [], False, 0, None, 0, 0, None

def hl_cancel_all_orders(account):
    """Cancel all open orders on Hyperliquid"""
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    open_orders = info.open_orders(account.address)
    for order in open_orders:
        exchange.cancel(order['coin'], order['oid'])

# ============================================================================
# TRADE LOGGING
# ============================================================================

def log_trade(signal_type, signal_amount, outcome, poly_price, stink_price,
              poly_shares, hedge_side, hedge_size, hedge_price, result, reason=""):
    """Log trade to CSV using pandas"""
    os.makedirs(DATA_DIR, exist_ok=True)

    poly_usd = round(stink_price * poly_shares, 4) if stink_price and poly_shares else 0
    hedge_usd = round(hedge_size * hedge_price, 4) if hedge_size and hedge_price else 0

    new_row = pd.DataFrame([{
        'timestamp': datetime.now().isoformat(),
        'signal_type': signal_type,
        'signal_amount_usd': round(signal_amount, 2),
        'outcome': outcome,
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

def print_trade_summary():
    """Print summary of all tracked trades"""
    if not os.path.exists(TRADE_LOG_FILE):
        return

    df = pd.read_csv(TRADE_LOG_FILE)
    if df.empty:
        return

    total = len(df)
    both_filled = len(df[df['result'] == 'BOTH_FILLED'])
    poly_only = len(df[df['result'] == 'POLY_ONLY'])
    no_fill = len(df[df['result'].isin(['NO_FILL', 'CANCELLED', 'TIME_EXPIRED'])])
    total_poly_usd = df['poly_usd'].sum()
    total_hedge_usd = df['hedge_usd'].sum()

    print(colored(f"\nTRADE HISTORY SUMMARY", "cyan", attrs=['bold']))
    print(colored(f"   Total signals:    {total}", "white"))
    print(colored(f"   Both filled:      {both_filled}", "green"))
    print(colored(f"   Poly only:        {poly_only}", "yellow"))
    print(colored(f"   No fill:          {no_fill}", "white"))
    print(colored(f"   Total Poly USD:   ${total_poly_usd:,.2f}", "white"))
    print(colored(f"   Total Hedge USD:  ${total_hedge_usd:,.2f}", "white"))

# ============================================================================
# LIQUIDATION SCANNER
# ============================================================================

_last_long_liq = 0
_last_short_liq = 0

def get_btc_liquidations():
    """Get BTC liquidations from Moon Dev API (all exchanges combined).
    Returns (btc_long_liq_usd, btc_short_liq_usd)"""
    global _last_long_liq, _last_short_liq

    data = get_all_liquidations(LIQUIDATION_TIMEFRAME)
    if not data:
        return 0, 0

    liqs = data.get('liquidations', data.get('data', []))
    if isinstance(liqs, list):
        long_total = 0
        short_total = 0
        for liq in liqs:
            coin = str(liq.get('coin', liq.get('symbol', ''))).upper()
            if coin != 'BTC':
                continue
            value = float(liq.get('value_usd', liq.get('value', liq.get('usd_value', 0))))
            side = str(liq.get('side', liq.get('direction', ''))).upper()
            if side in ('LONG', 'SELL', 'B'):
                long_total += value
            elif side in ('SHORT', 'BUY', 'S'):
                short_total += value
        return long_total, short_total

    return 0, 0

def check_liquidation_signal():
    """Check for new BTC liquidation signal.
    Returns: ('LONG_LIQ', amount) or ('SHORT_LIQ', amount) or (None, 0)

    LONG liquidations = bearish = we want DOWN
    SHORT liquidations = bullish = we want UP"""
    global _last_long_liq, _last_short_liq

    long_liq, short_liq = get_btc_liquidations()

    _last_long_liq = long_liq
    _last_short_liq = short_liq

    if long_liq >= LIQUIDATION_THRESHOLD_MIN and long_liq <= LIQUIDATION_THRESHOLD_MAX and long_liq > short_liq:
        return 'LONG_LIQ', long_liq
    elif short_liq >= LIQUIDATION_THRESHOLD_MIN and short_liq <= LIQUIDATION_THRESHOLD_MAX and short_liq > long_liq:
        return 'SHORT_LIQ', short_liq
    elif long_liq > LIQUIDATION_THRESHOLD_MAX or short_liq > LIQUIDATION_THRESHOLD_MAX:
        over = max(long_liq, short_liq)
        print(colored(f"   Missed the wave (${over:,.0f} > ${LIQUIDATION_THRESHOLD_MAX:,}), waiting for next", "yellow"))

    return None, 0

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
    return MARKET_DURATION - (now - market_ts)

def get_market_info(market_ts):
    """Get market ID and token IDs for a BTC 5-min market.
    Market slug format: btc-updown-5m-{timestamp}"""
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

    up_token_id = token_data[2]    # NO token = UP
    down_token_id = token_data[1]  # YES token = DOWN

    return {
        'market_id': market_id,
        'up_token_id': up_token_id,
        'down_token_id': down_token_id,
        'question': market['question'],
        'slug': market_slug,
    }

# ============================================================================
# ORDER BOOK & POSITION CHECKS
# ============================================================================

def get_order_book(token_id):
    """Get best bid/ask from Polymarket CLOB"""
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
    """Place inverse hedge on Hyperliquid. Loops until filled.
    If Polymarket outcome is "UP"   -> SHORT BTC on HL
    If Polymarket outcome is "DOWN" -> LONG BTC on HL
    Returns (success, hedge_side, hedge_size_btc, hedge_price)"""
    if poly_outcome.upper() == "UP":
        is_buy = False
        hedge_side = "SHORT"
    elif poly_outcome.upper() == "DOWN":
        is_buy = True
        hedge_side = "LONG"
    else:
        return False, "UNKNOWN", 0, 0

    exchange = Exchange(hl_account, constants.MAINNET_API_URL)
    exchange.update_leverage(HEDGE_LEVERAGE, HEDGE_SYMBOL, is_cross=False)

    for attempt in range(1, HEDGE_MAX_ATTEMPTS + 1):
        ask, bid, _ = hl_ask_bid(HEDGE_SYMBOL)

        mid_price = (ask + bid) / 2
        btc_size = (HEDGE_USD * HEDGE_LEVERAGE) / mid_price

        sz_decimals = hl_get_sz_px_decimals(HEDGE_SYMBOL)[0]
        factor = 10 ** sz_decimals
        btc_size = math.ceil(btc_size * factor) / factor

        if btc_size <= 0:
            return False, hedge_side, 0, 0

        if is_buy:
            limit_px = bid + (ask - bid) * HEDGE_PRICE_BUMP_PCT * attempt
            limit_px = min(limit_px, ask)
        else:
            limit_px = ask - (ask - bid) * HEDGE_PRICE_BUMP_PCT * attempt
            limit_px = max(limit_px, bid)

        hl_cancel_all_orders(hl_account)
        time.sleep(0.3)

        result = hl_limit_order(HEDGE_SYMBOL, is_buy, btc_size, limit_px, False, hl_account)

        if result and 'response' in result:
            statuses = result['response'].get('data', {}).get('statuses', [])
            if statuses:
                status = statuses[0]
                if 'filled' in status:
                    return True, hedge_side, btc_size, limit_px
                elif 'error' in status:
                    continue

        time.sleep(HEDGE_FILL_WAIT)

        positions, in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = hl_get_position(HEDGE_SYMBOL, hl_account)

        if in_pos and abs(pos_size) > 0:
            actual_side = "LONG" if is_long else "SHORT"
            return True, actual_side, abs(pos_size), entry_px

        hl_cancel_all_orders(hl_account)
        time.sleep(0.3)

    return False, hedge_side, 0, 0

# ============================================================================
# MAIN BOT CLASS
# ============================================================================

class LiqStinkBot:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset state for next market"""
        self.current_market_ts = None
        self.market_info = None
        self.signal_fired = False
        self.signal_type = None
        self.signal_amount = 0
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
            return False

        self.signal_price = book['best_ask']
        self.stink_bid_price = round(self.signal_price * (1 - PULLBACK_PCT), 4)
        if self.stink_bid_price < 0.01:
            self.stink_bid_price = 0.01

        self.stink_bid_shares = calculate_shares(POLY_USD_PER_POSITION, self.stink_bid_price)
        if self.stink_bid_shares <= 0:
            return False

        cancel_token_orders(token_id)
        time.sleep(0.5)

        response = place_limit_order(
            token_id=token_id,
            side="BUY",
            price=self.stink_bid_price,
            size=self.stink_bid_shares,
        )

        if response and 'orderID' in response:
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
        print(colored(f"NEW 5-MIN MARKET CYCLE", "cyan", attrs=['bold']))
        print(colored(f"   Market time: {market_et.strftime('%I:%M:%S%p ET')} ({market_dt.strftime('%H:%M:%S UTC')})", "white"))
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
                if self.order_placed and not self.poly_filled:
                    log_trade(self.signal_type or "NONE", self.signal_amount, self.target_outcome or "NONE",
                              self.signal_price, self.stink_bid_price, self.stink_bid_shares,
                              "", 0, 0, "TIME_EXPIRED", "Market ended before fill")
                break

            if time_remaining < MIN_TIME_LEFT and self.order_placed and not self.poly_filled:
                self.cancel_orders()
                log_trade(self.signal_type or "NONE", self.signal_amount, self.target_outcome or "NONE",
                          self.signal_price, self.stink_bid_price, self.stink_bid_shares,
                          "", 0, 0, "CANCELLED", f"< {MIN_TIME_LEFT}s remaining")
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

                    log_trade(self.signal_type, self.signal_amount, self.target_outcome,
                              self.signal_price, self.stink_bid_price, self.stink_bid_shares,
                              hedge_side if hedge_ok else "", hedge_size, hedge_price, result)
                    continue

                time.sleep(2)
                continue

            if not self.signal_fired and time_remaining > MIN_TIME_LEFT:
                signal_type, signal_amount = check_liquidation_signal()

                if signal_type:
                    self.signal_fired = True
                    self.signal_type = signal_type
                    self.signal_amount = signal_amount

                    if signal_type == 'LONG_LIQ':
                        self.target_outcome = "DOWN"
                        self.target_token_id = self.market_info['down_token_id']
                    else:
                        self.target_outcome = "UP"
                        self.target_token_id = self.market_info['up_token_id']

                    self.place_stink_bid()

            time.sleep(BOT_POLL_INTERVAL)

# ============================================================================
# MAIN ENTRY
# ============================================================================

def main():
    print(colored("""
==============================================================================
     MOON DEV's LIQUIDATION STINK BID BOT v1.0 (STANDALONE)
     Moon Dev API Liquidations -> Polymarket Stink Bids + Hyperliquid Hedge
     BTC 5-Min Markets | Pullback Entry | 40% Inverse Hedge
==============================================================================
    """, "cyan", attrs=['bold']))

    print_trade_summary()

    hl_info = Info(constants.MAINNET_API_URL, skip_ws=True)
    hl_state = hl_info.user_state(hl_account.address)
    hl_balance = float(hl_state["marginSummary"]["accountValue"])
    print(colored(f"   Hyperliquid: ${hl_balance:,.2f}", "green"))

    long_liq, short_liq = get_btc_liquidations()
    print(colored(f"   BTC Liqs (10m): Long ${long_liq:,.0f} | Short ${short_liq:,.0f}", "cyan"))

    bot = LiqStinkBot()

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
            print(colored(f"\nBot stopped!", "yellow", attrs=['bold']))
            bot.cancel_orders()
            break
        except Exception as e:
            print(colored(f"\nError: {str(e)[:120]}", "red"))
            import traceback
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()
```
### Want to build this live with us?

We walk through tools like this on our live Zoom calls. Come hang out, ask questions, and build alongside the Moon Dev community.

[Join the Live Zoom Call](https://moondev.com/t/blog/polymarket-hyperliquid-liquidation-statistical-arbitrage)

Built with love by Moon Dev

### Related Resources

[HIP3 Funding Rate Scanner](https://moondev.com/hip-3-funding-rate-scanner)

— Scan every funding rate on Hyperliquid including HIP3 tokenized assets

[HIP3 Liquidation Trading Bot](https://moondev.com/hip-3-liquidation-trading-bot)

— Trade liquidation cascades on HIP3 automatically

[Moon Dev API Documentation](https://moondev.com/docs)

— Liquidation data, funding rates, position snapshots, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations across exchanges

[Market Data Portal](https://moondev.com/data)

— Funding rates, open interest, and more
