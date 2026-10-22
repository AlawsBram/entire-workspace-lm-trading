<!-- source: https://moondev.com/polymarket-five-minute-bot -->
<!-- captured: 2026-10-07 -->
<!-- title: Polymarket 5-Minute Bot -->

Polymarket 5-Minute Bot | Easy Hyper Gambler | BTC Binary Options Trading Bot | Moon Dev

Moon Dev Open Source

# Polymarket 5-Minute Bot: The Easy Hyper Gambler

The simplest way to bet on BTC 5-minute Up/Down markets on Polymarket. Three keyboard keys — B for UP, S for DOWN, X to close. Places limit orders at a discount so you get better entries. 288 chances per day.

By Moon Dev · March 15, 2026

## What Is This Bot?

Polymarket runs BTC 5-minute Up/Down binary markets — every 5 minutes, a new market opens asking "Will BTC be above $X at the end of this window?" You can bet YES (up) or NO (down). That's 288 markets per day.

This bot gives you a **real-time terminal dashboard** with keyboard controls. You watch the price, the order books, and the countdown timer — then press a key to place your bet. It's manual decision-making with automated execution.

### How It Works

**B = Buy UP** — Places a limit order on the bid for the UP outcome, betting BTC goes higher

**S = Buy DOWN** — Places a limit order on the bid for the DOWN outcome, betting BTC goes lower

**X = Close Position** — Sells your shares into the bid to exit early before expiry

**Press B or S again** — Cancels and re-places your order to chase the price

The key trick: the bot doesn't buy at market price. It places limit orders at a **10% discount** below the current bid. You're fishing for a dip — a momentary pullback that fills your order at a better price. Let me walk you through every piece of this bot.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-five-minute-bot)

## Step 1: The Imports

The bot uses standard Python libraries plus a few key packages: requests for API calls to Binance and Polymarket, termcolor for the colorful terminal display, and dotenv for loading your API keys securely from a .env file.

Imports and environment setup

```python
#!/opt/anaconda3/envs/tflow/bin/python
"""
================================================================================
MOON DEV's EASY HYPER GAMBLER v1.0
================================================================================
The simplest way to bet on BTC 5-minute markets on Polymarket.

CONTROLS:
  B = Buy UP  (limit order on the bid - betting BTC goes up)
  S = Buy DOWN (limit order on the bid - betting BTC goes down)
  X = Close position at market (sell into the bid to exit early)

  Hit B or S again to cancel and re-place your order (chase the price)

288 chances per day. Let's get it.

Built by Moon Dev
================================================================================
"""

import sys
import os
import select
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from termcolor import colored

# Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)
```
The auto re-exec block at the bottom is a neat trick — if you accidentally run the script with the wrong Python environment, it automatically restarts itself using the correct conda environment. No more "module not found" errors because you forgot to conda activate.

## Step 2: Path Setup & Helper Functions

The bot imports helper functions from nice_funcs.py — a utility module that handles common Polymarket operations like canceling orders, calculating share quantities, fetching positions, and looking up token IDs.

Path setup and helper imports

```python
# PATH SETUP
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples'))
from nice_funcs import (
    cancel_token_orders,
    calculate_shares,
    get_all_positions,
    get_token_id,
)
```
The PROJECT_ROOT trick walks up two directories from the script to find the project root where the .env file lives. This means the script works no matter which subdirectory you run it from.

## Step 3: Configuration

All the tunable parameters are at the top of the file. The two most important ones: BET_SIZE_USD controls how much you bet per trade, and BID_DISCOUNT_PCT controls how far below the current bid your limit order is placed.

Configuration block

```python
BET_SIZE_USD = 10.0          # How much per bet in USD
MARKET_DURATION = 300        # 5-minute markets (300 seconds)
BID_DISCOUNT_PCT = 10        # Bid X% under the current bid for a deal
ET = timezone(timedelta(hours=-5))

# Session tracking
SESSION_WINS = 0
SESSION_LOSSES = 0
SESSION_PNL = 0.0
SESSION_TRADES = 0
```
At 10% discount, if the best bid on an UP token is $0.50, the bot places your order at $0.45. You're saying "I'll buy, but only if the price dips to here first." This means you won't always get filled — but when you do, you're in at a better price.

The session tracking variables keep a running scoreboard of your wins, losses, and P&L. These reset every time you restart the bot.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-five-minute-bot)

## Step 4: Placing Limit Orders on Polymarket

This is the core order function. It connects to Polymarket's CLOB (Central Limit Order Book), signs your order with your wallet, and submits it. The function handles both buying and selling, for any token ID, at any price and size.

Limit order placement

```python
def place_limit_order(token_id, side, price, size, neg_risk=False):
    """Place a limit order on Polymarket"""
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
        print(colored("   Missing PRIVATE_KEY or PUBLIC_KEY in .env!", "red"))
        return {}

    try:
        browser_wallet = Web3.toChecksumAddress(browser_address)
    except AttributeError:
        browser_wallet = Web3.to_checksum_address(browser_address)

    client = ClobClient(
        host="https://clob.polymarket.com",
        key=key, chain_id=POLYGON,
        funder=browser_wallet, signature_type=1,
    )

    if api_key and api_secret and passphrase:
        creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=passphrase)
        client.set_api_creds(creds=creds)
    else:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds=creds)

    order_args = OrderArgs(
        token_id=str(token_id), price=price, size=size,
        side=side.upper(), fee_rate_bps=1000,
    )

    if neg_risk:
        signed_order = client.create_order(order_args, options=PartialCreateOrderOptions(neg_risk=True))
    else:
        signed_order = client.create_order(order_args)

    response = client.post_order(signed_order)
    return response if response else {}
```
A few things worth noting. The signature_type=1 tells the CLOB client to use Polymarket's browser wallet signing scheme. The funder is your public address that holds USDC on Polygon. The neg_risk flag handles certain market types that use negative risk token pairs.

The fee_rate_bps=1000 sets the fee rate to 10% (1000 basis points). This is the maximum fee — in practice, Polymarket charges less, but setting it high ensures your order always goes through.

## Step 5: Market Discovery & Order Books

Every 5 minutes a new market opens. The bot needs to find the right market, get the UP and DOWN token IDs, and fetch the order book to know where to place orders. Here's how it does that.

BTC price and market timing

```python
def get_btc_price():
    """Get current BTC price from Binance"""
    resp = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5)
    if resp.status_code == 200:
        return float(resp.json()['price'])
    return None

def get_current_market_timestamp():
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    return MARKET_DURATION - (int(time.time()) - market_ts)
```
The market timestamp calculation is clever — it rounds the current Unix timestamp down to the nearest 300-second boundary. Every 5-minute market has a unique timestamp. For example, if it's 2:07 PM, the current market started at 2:05 PM (timestamp divisible by 300).

Order book and market info

```python
def get_order_book(token_id):
    """Get best bid/ask from CLOB"""
    response = requests.get("https://clob.polymarket.com/book", params={'token_id': token_id}, timeout=10)
    if response.status_code != 200:
        return None
    data = response.json()
    bids = data.get('bids', [])
    asks = data.get('asks', [])
    if not bids or not asks:
        return None
    return {
        'best_bid': float(bids[-1]['price']),
        'best_ask': float(asks[0]['price']),
        'spread': float(asks[0]['price']) - float(bids[-1]['price']),
    }

def get_market_info(market_ts):
    """Find the 5-min BTC market"""
    market_slug = f"btc-updown-5m-{market_ts}"
    response = requests.get("https://gamma-api.polymarket.com/markets",
                          params={'slug': market_slug, 'closed': 'false', 'active': 'true'}, timeout=10)
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
```
The market slug format btc-updown-5m-{timestamp} is how Polymarket names their 5-minute BTC markets. The Gamma API is Polymarket's market discovery API — it returns the market ID, which the bot then uses to look up the specific token IDs for the UP and DOWN outcomes.

Each market has two tokens: one for UP and one for DOWN. The order book gives us the best bid (highest buy order) and best ask (lowest sell order) for each token. The spread tells us how liquid the market is.

## Step 6: Position Checking

After placing a limit order, the bot needs to know when it gets filled. It does this by checking your portfolio for shares of the token you ordered.

Position checking

```python
def _get_portfolio_quiet():
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    portfolio = get_all_positions()
    sys.stdout = old_stdout
    return portfolio

def check_position(token_id):
    """Check if we hold shares of this token and how many"""
    portfolio = _get_portfolio_quiet()
    if portfolio and 'positions' in portfolio:
        for pos in portfolio['positions']:
            if pos.get('asset_id') == token_id and pos.get('position_size', 0) > 0:
                return float(pos['position_size'])
    return 0.0
```
The _get_portfolio_quiet wrapper suppresses the print output from the get_all_positions helper. Since the bot redraws the screen every second, we don't want stray print statements messing up the display.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-five-minute-bot)

## Step 7: The Terminal Dashboard

The display is the fun part. The bot clears the screen every second and redraws a full dashboard with a countdown timer, order book prices, BTC price comparison, session stats, and a P&L box when you're in a position. It's all built with termcolor and Unicode box-drawing characters.

Display functions

```python
HYPE_MESSAGES = [
    "LFG Moon Dev!", "Send it!", "Moon Dev on the hunt",
    "288 chances today, make 'em count", "Trust the process",
    "Vibes are immaculate", "Moon Dev stays winning",
    "The game never stops", "One trade at a time",
    "Moon Dev built different", "Every 5 min is a new chance",
    "Patience pays, Moon Dev", "Let's cook",
]

def draw_header(hype_msg):
    print(colored("""
+======================================================================+
|          MOON DEV's EASY HYPER GAMBLER v1.0                          |
|              BTC 5-Min Markets | 288 Bets/Day                        |
|                    Bet Size: $""" + f"{BET_SIZE_USD:.0f}" + """                                |
+======================================================================+""", "cyan", attrs=['bold']))
    print(colored(f"  {hype_msg}", "magenta"))

def draw_session_stats():
    """Show session scoreboard"""
    global SESSION_WINS, SESSION_LOSSES, SESSION_PNL, SESSION_TRADES

    if SESSION_TRADES == 0:
        print(colored(f"\n  SESSION: No trades yet - let's get it!", "yellow"))
        return

    win_rate = (SESSION_WINS / SESSION_TRADES * 100) if SESSION_TRADES > 0 else 0
    pnl_color = "green" if SESSION_PNL >= 0 else "red"

    print()
    print(colored(f"  +-------------- SESSION SCOREBOARD --------------+", "yellow"))
    print(colored(f"  |  Trades: {SESSION_TRADES:<5}", "white") +
          colored(f" W: {SESSION_WINS}", "green") +
          colored(f"  L: {SESSION_LOSSES}", "red") +
          colored(f"  WR: {win_rate:.0f}%", "cyan") +
          colored(f"       |", "yellow"))
    print(colored(f"  |  Session P&L: ", "white") +
          colored(f"${SESSION_PNL:+.2f}", pnl_color, attrs=['bold']) +
          colored(f"                          |", "yellow"))
    print(colored(f"  +------------------------------------------------+", "yellow"))
```
The hype messages rotate every 15 seconds — just a fun touch that keeps the dashboard from feeling static. The session scoreboard tracks your real-time win rate and P&L across all trades in the current session.

Market info display with price comparison

```python
def draw_market_info(market_info, time_remaining, up_book, down_book, btc_price, price_to_beat):
    mins = time_remaining // 60
    secs = time_remaining % 60

    # Timer bar
    pct = time_remaining / MARKET_DURATION
    bar_width = 40
    filled = int(bar_width * pct)
    bar = "=" * filled + "-" * (bar_width - filled)

    if time_remaining > 180:
        timer_color = "green"
    elif time_remaining > 60:
        timer_color = "yellow"
    else:
        timer_color = "red"

    print()
    print(colored(f"  TIME LEFT: {mins}:{secs:02d}", timer_color, attrs=['bold']))
    print(colored(f"  [{bar}]", timer_color))

    # BIG price to beat vs current BTC price display
    if price_to_beat and btc_price:
        diff = btc_price - price_to_beat
        diff_pct = (diff / price_to_beat) * 100
        if diff > 0:
            status = "ABOVE"
            status_color = "green"
        else:
            status = "BELOW"
            status_color = "red"

        print(colored(f"  +=====================================================+", "cyan", attrs=['bold']))
        print(colored(f"  |  PRICE TO BEAT:  ", "white", attrs=['bold']) +
              colored(f"${price_to_beat:,.2f}", "cyan", attrs=['bold']))
        print(colored(f"  |  CURRENT BTC:    ", "white", attrs=['bold']) +
              colored(f"${btc_price:,.2f}", status_color, attrs=['bold']))
        print(colored(f"  |  DIFF:           ", "white", attrs=['bold']) +
              colored(f"${diff:+,.2f} ({diff_pct:+.3f}%)", status_color, attrs=['bold']))
        print(colored(f"  |                    >>> {status} <<<", status_color, attrs=['bold']))
        print(colored(f"  +=====================================================+", "cyan", attrs=['bold']))
```
The "price to beat" is the BTC price captured at the moment the 5-minute market opened. The dashboard shows you in real time whether BTC is currently above or below that price — and by how much. This is the core information you need to decide whether to bet UP or DOWN.

The timer bar changes color as time runs out — green when there's plenty of time, yellow under 3 minutes, red under 1 minute. When you're in a position, the dashboard shows a large P&L box with dynamic messages based on how the trade is going.

## Step 8: The Live P&L Box

When you're in a position, the dashboard switches from "ready to bet" mode to showing a real-time P&L box. It tracks your entry price, current bid, shares, and unrealized profit/loss — with dynamic vibe messages.

Live P&L display

```python
def draw_pnl_box(state, up_book, down_book):
    """BIG P&L display when in a position"""
    if not state['position_side'] or not state['position_token_id']:
        return

    entry_price = state['entry_price']
    shares = state['position_shares']
    side = state['position_side']

    # Get current bid for our token (that's what we could sell at)
    current_book = up_book if side == "UP" else down_book
    if not current_book:
        return

    current_bid = current_book['best_bid']
    cost_basis = entry_price * shares
    current_value = current_bid * shares
    pnl_usd = current_value - cost_basis
    pnl_pct = ((current_bid / entry_price) - 1) * 100 if entry_price > 0 else 0

    is_winning = pnl_usd >= 0
    pnl_color = "green" if is_winning else "red"

    # Fun dynamic vibe messages
    if pnl_pct > 50:
        vibe = "TO THE MOON!!!"
    elif pnl_pct > 20:
        vibe = "COOKING!"
    elif pnl_pct > 5:
        vibe = "Looking good!"
    elif pnl_pct > -5:
        vibe = "Flat..."
    elif pnl_pct > -20:
        vibe = "Come on..."
    elif pnl_pct > -50:
        vibe = "Pain..."
    else:
        vibe = "GUH"

    # Big flashy P&L box
    print()
    print(colored(f"  +===================================================+", pnl_color, attrs=['bold']))
    print(colored(f"  |  POSITION: {side:<6}                              |", pnl_color, attrs=['bold']))
    print(colored(f"  |    Entry:   ${entry_price:.4f}                    |", "white"))
    print(colored(f"  |    Current: ${current_bid:.4f}                    |", "white"))
    print(colored(f"  |    Shares:  {shares:.1f}                          |", "white"))
    pnl_str = f"${pnl_usd:+.2f} ({pnl_pct:+.1f}%)"
    print(colored(f"  |    P&L:  {pnl_str:<20}                  |", pnl_color, attrs=['bold']))
    print(colored(f"  |    {vibe:<40}      |", pnl_color, attrs=['bold']))
    print(colored(f"  |    [X] = Close at market  |  Hold to expiry       |", "yellow"))
    print(colored(f"  +===================================================+", pnl_color, attrs=['bold']))
```
The P&L is calculated against the current bid — that's the price you'd actually get if you hit X to close. Entry price times shares gives your cost basis, current bid times shares gives your current value, and the difference is your unrealized P&L. Simple math, big visual impact.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-five-minute-bot)

## Step 9: The Main Loop

The main loop ties everything together. It runs at 10Hz (every 0.1 seconds), checking for keyboard input, fetching fresh order books every 3 seconds, detecting new markets, and redrawing the display every second. The terminal is set to raw mode so single keypresses are detected instantly.

Main loop - state and market detection

```python
def main():
    global SESSION_WINS, SESSION_LOSSES, SESSION_PNL, SESSION_TRADES

    import tty
    import termios

    # State
    state = {
        'order_side': None,       # "UP" or "DOWN" if we have a pending order
        'order_price': 0,
        'order_token_id': None,
        'position_side': None,    # "UP" or "DOWN" if we're holding
        'position_shares': 0,
        'position_token_id': None,
        'entry_price': 0,         # Track entry for P&L
        'current_market_ts': None,
        'market_info': None,
        'price_to_beat': None,    # BTC price at market open
    }

    # Set terminal to raw mode for non-blocking single char input
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            now = time.time()
            market_ts = get_current_market_timestamp()
            time_remaining = get_time_remaining(market_ts)

            # New market detected - reset everything
            if market_ts != state['current_market_ts']:
                # If we had a position that expired, count it
                if state['position_side'] and state['position_token_id']:
                    current_book = up_book if state['position_side'] == "UP" else down_book
                    if current_book and state['entry_price'] > 0:
                        final_bid = current_book['best_bid']
                        pnl = (final_bid - state['entry_price']) * state['position_shares']
                        SESSION_PNL += pnl
                        SESSION_TRADES += 1
                        if pnl >= 0:
                            SESSION_WINS += 1
                        else:
                            SESSION_LOSSES += 1

                # Cancel unfilled orders from previous market
                if state['order_side'] and state['order_token_id'] and not state['position_side']:
                    cancel_token_orders(state['order_token_id'])

                # Reset state for new market
                state = {k: None if k != 'current_market_ts' else market_ts
                         for k in state}
                state['order_price'] = 0
                state['position_shares'] = 0
                state['entry_price'] = 0

                # Grab BTC price at market open = price to beat
                state['price_to_beat'] = get_btc_price()

                # Find the new market (retry up to 8 times)
                for attempt in range(8):
                    state['market_info'] = get_market_info(market_ts)
                    if state['market_info']:
                        break
                    time.sleep(2)

            time.sleep(0.1)
```
The state dictionary is the brain of the bot. It tracks everything — whether you have an open order or a filled position, which side (UP/DOWN), the entry price, and the current market info. When a new 5-minute window starts, the state resets and the bot hunts for the new market.

The "price to beat" is captured right when the market opens. This becomes the reference price shown on the dashboard — BTC needs to be above this price at expiry for UP to win, or below for DOWN to win.

## Step 10: Keyboard Controls

The input handler reads single keypresses without requiring Enter. When you press B or S, it cancels any existing order, fetches the current order book, calculates a discounted bid price, and places a new limit order.

Keyboard input handling

```python
# B = Buy UP
if char == 'B':
    token_id = market_info['up_token_id']

    # Cancel existing order if any
    if state['order_token_id']:
        cancel_token_orders(state['order_token_id'])
        time.sleep(0.5)

    book = get_order_book(token_id)
    if not book:
        continue

    # Bid X% under the best bid for a deal
    bid_price = round(book['best_bid'] * (1 - BID_DISCOUNT_PCT / 100), 4)
    shares = calculate_shares(BET_SIZE_USD, bid_price)
    if shares <= 0:
        continue

    resp = place_limit_order(token_id, "BUY", bid_price, shares, neg_risk=neg_risk)

    if resp and resp.get('orderID'):
        state['order_side'] = "UP"
        state['order_price'] = bid_price
        state['order_token_id'] = token_id

# S = Buy DOWN (same logic, different token)
elif char == 'S':
    token_id = market_info['down_token_id']
    # ... same pattern as above ...

# X = Close position at market
elif char == 'X':
    if not state['position_side'] or not state['position_token_id']:
        continue

    token_id = state['position_token_id']
    shares = state['position_shares']

    # Sell into the bid to exit immediately
    book = get_order_book(token_id)
    if not book:
        continue

    sell_price = book['best_bid']

    # Calculate P&L for this close
    close_pnl = (sell_price - state['entry_price']) * shares
    SESSION_PNL += close_pnl
    SESSION_TRADES += 1
    if close_pnl >= 0:
        SESSION_WINS += 1
    else:
        SESSION_LOSSES += 1

    cancel_token_orders(token_id)
    time.sleep(0.5)
    resp = place_limit_order(token_id, "SELL", sell_price, shares, neg_risk=neg_risk)
```
The key mechanic: pressing B or S **cancels your existing order first**, then places a new one at the current discounted price. This is how you "chase" the market — if the price moved since your last order, hitting B or S again gets you a fresh limit order at the new level.

X (close) works differently — it sells **into the bid** at the current best bid price. This is essentially a market sell. You'll get filled immediately, but at whatever the bid is. The P&L from the close is immediately added to your session stats.

## Full Source Code

Here's the complete easy.py file — copy and paste this into your project to start trading BTC 5-minute markets on Polymarket. Make sure you have your .env file set up with your Polymarket credentials (PRIVATE_KEY, PUBLIC_KEY, API_KEY, SECRET, PASSPHRASE).

easy.py - Full source code

```python
#!/opt/anaconda3/envs/tflow/bin/python
"""
================================================================================
MOON DEV's EASY HYPER GAMBLER v1.0
================================================================================
The simplest way to bet on BTC 5-minute markets on Polymarket.

CONTROLS:
  B = Buy UP  (limit order on the bid - betting BTC goes up)
  S = Buy DOWN (limit order on the bid - betting BTC goes down)
  X = Close position at market (sell into the bid to exit early)

  Hit B or S again to cancel and re-place your order (chase the price)

288 chances per day. Let's get it.

Built by Moon Dev
================================================================================
"""

import sys
import os
import select
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from termcolor import colored

# Auto re-exec with tflow python if we're in the wrong env
TFLOW_PYTHON = "/opt/anaconda3/envs/tflow/bin/python"
if os.path.exists(TFLOW_PYTHON) and sys.executable != TFLOW_PYTHON:
    os.execv(TFLOW_PYTHON, [TFLOW_PYTHON] + sys.argv)

# ============================================================================
# PATH SETUP
# ============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples'))
from nice_funcs import (
    cancel_token_orders,
    calculate_shares,
    get_all_positions,
    get_token_id,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

BET_SIZE_USD = 10.0          # How much per bet in USD
MARKET_DURATION = 300        # 5-minute markets (300 seconds)
BID_DISCOUNT_PCT = 10        # Bid X% under the current bid for a deal
ET = timezone(timedelta(hours=-5))

# Session tracking
SESSION_WINS = 0
SESSION_LOSSES = 0
SESSION_PNL = 0.0
SESSION_TRADES = 0

# ============================================================================
# ORDER FUNCTIONS
# ============================================================================

def place_limit_order(token_id, side, price, size, neg_risk=False):
    """Place a limit order on Polymarket"""
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
        print(colored("   Missing PRIVATE_KEY or PUBLIC_KEY in .env!", "red"))
        return {}

    try:
        browser_wallet = Web3.toChecksumAddress(browser_address)
    except AttributeError:
        browser_wallet = Web3.to_checksum_address(browser_address)

    client = ClobClient(
        host="https://clob.polymarket.com",
        key=key, chain_id=POLYGON,
        funder=browser_wallet, signature_type=1,
    )

    if api_key and api_secret and passphrase:
        creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=passphrase)
        client.set_api_creds(creds=creds)
    else:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds=creds)

    order_args = OrderArgs(
        token_id=str(token_id), price=price, size=size,
        side=side.upper(), fee_rate_bps=1000,
    )

    if neg_risk:
        signed_order = client.create_order(order_args, options=PartialCreateOrderOptions(neg_risk=True))
    else:
        signed_order = client.create_order(order_args)

    response = client.post_order(signed_order)
    return response if response else {}

# ============================================================================
# MARKET FUNCTIONS
# ============================================================================

def get_btc_price():
    """Get current BTC price from Binance"""
    resp = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5)
    if resp.status_code == 200:
        return float(resp.json()['price'])
    return None

def get_current_market_timestamp():
    now = int(time.time())
    return (now // MARKET_DURATION) * MARKET_DURATION

def get_time_remaining(market_ts):
    return MARKET_DURATION - (int(time.time()) - market_ts)

def get_order_book(token_id):
    """Get best bid/ask from CLOB"""
    response = requests.get("https://clob.polymarket.com/book", params={'token_id': token_id}, timeout=10)
    if response.status_code != 200:
        return None
    data = response.json()
    bids = data.get('bids', [])
    asks = data.get('asks', [])
    if not bids or not asks:
        return None
    return {
        'best_bid': float(bids[-1]['price']),
        'best_ask': float(asks[0]['price']),
        'spread': float(asks[0]['price']) - float(bids[-1]['price']),
    }

def get_market_info(market_ts):
    """Find the 5-min BTC market"""
    market_slug = f"btc-updown-5m-{market_ts}"
    response = requests.get("https://gamma-api.polymarket.com/markets",
                          params={'slug': market_slug, 'closed': 'false', 'active': 'true'}, timeout=10)
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

def _get_portfolio_quiet():
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    portfolio = get_all_positions()
    sys.stdout = old_stdout
    return portfolio

def check_position(token_id):
    """Check if we hold shares of this token and how many"""
    portfolio = _get_portfolio_quiet()
    if portfolio and 'positions' in portfolio:
        for pos in portfolio['positions']:
            if pos.get('asset_id') == token_id and pos.get('position_size', 0) > 0:
                return float(pos['position_size'])
    return 0.0

# ============================================================================
# DISPLAY
# ============================================================================

HYPE_MESSAGES = [
    "LFG Moon Dev!", "Send it!", "Moon Dev on the hunt",
    "288 chances today, make 'em count", "Trust the process",
    "Vibes are immaculate", "Moon Dev stays winning",
    "The game never stops", "One trade at a time",
    "Moon Dev built different", "Every 5 min is a new chance",
    "Patience pays, Moon Dev", "Let's cook",
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_header(hype_msg):
    print(colored("""
+======================================================================+
|          MOON DEV's EASY HYPER GAMBLER v1.0                          |
|              BTC 5-Min Markets | 288 Bets/Day                        |
|                    Bet Size: $""" + f"{BET_SIZE_USD:.0f}" + """                                |
+======================================================================+""", "cyan", attrs=['bold']))
    print(colored(f"  {hype_msg}", "magenta"))

def draw_session_stats():
    """Show session scoreboard"""
    global SESSION_WINS, SESSION_LOSSES, SESSION_PNL, SESSION_TRADES

    if SESSION_TRADES == 0:
        print(colored(f"\n  SESSION: No trades yet - let's get it!", "yellow"))
        return

    win_rate = (SESSION_WINS / SESSION_TRADES * 100) if SESSION_TRADES > 0 else 0
    pnl_color = "green" if SESSION_PNL >= 0 else "red"
    pnl_emoji = "+" if SESSION_PNL >= 0 else "-"

    print()
    print(colored(f"  +-------------- SESSION SCOREBOARD --------------+", "yellow"))
    print(colored(f"  |  Trades: {SESSION_TRADES:<5}", "white") +
          colored(f" W: {SESSION_WINS}", "green") +
          colored(f"  L: {SESSION_LOSSES}", "red") +
          colored(f"  WR: {win_rate:.0f}%", "cyan") +
          colored(f"       |", "yellow"))
    print(colored(f"  |  Session P&L: ", "white") +
          colored(f"${SESSION_PNL:+.2f}", pnl_color, attrs=['bold']) +
          colored(f"                          |", "yellow"))
    print(colored(f"  +------------------------------------------------+", "yellow"))

def draw_market_info(market_info, time_remaining, up_book, down_book, btc_price, price_to_beat):
    mins = time_remaining // 60
    secs = time_remaining % 60

    # Timer bar
    pct = time_remaining / MARKET_DURATION
    bar_width = 40
    filled = int(bar_width * pct)
    bar = "=" * filled + "-" * (bar_width - filled)

    if time_remaining > 180:
        timer_color = "green"
    elif time_remaining > 60:
        timer_color = "yellow"
    else:
        timer_color = "red"

    print()
    print(colored(f"  TIME LEFT: {mins}:{secs:02d}", timer_color, attrs=['bold']))
    print(colored(f"  [{bar}]", timer_color))
    print()

    if market_info:
        print(colored(f"  {market_info['question']}", "white", attrs=['bold']))
        print()

        # BIG price to beat vs current BTC price display
        if price_to_beat and btc_price:
            diff = btc_price - price_to_beat
            diff_pct = (diff / price_to_beat) * 100
            if diff > 0:
                status = "ABOVE"
                status_color = "green"
                arrow = "^"
            else:
                status = "BELOW"
                status_color = "red"
                arrow = "v"

            print(colored(f"  +=====================================================+", "cyan", attrs=['bold']))
            print(colored(f"  |  PRICE TO BEAT:  ", "white", attrs=['bold']) + colored(f"${price_to_beat:,.2f}", "cyan", attrs=['bold']) + colored(f"                    |", "cyan", attrs=['bold']))
            print(colored(f"  |  CURRENT BTC:    ", "white", attrs=['bold']) + colored(f"${btc_price:,.2f}", status_color, attrs=['bold']) + colored(f"                    |", "cyan", attrs=['bold']))
            print(colored(f"  |  {arrow}  DIFF:           ", "white", attrs=['bold']) + colored(f"${diff:+,.2f} ({diff_pct:+.3f}%)", status_color, attrs=['bold']) + colored(f"            |", "cyan", attrs=['bold']))
            print(colored(f"  |                      ", "white") + colored(f"  >>> {status} <<<", status_color, attrs=['bold']) + colored(f"                          |", "cyan", attrs=['bold']))
            print(colored(f"  +=====================================================+", "cyan", attrs=['bold']))
            print()

        if up_book:
            print(colored(f"  UP   | Bid: ${up_book['best_bid']:.4f}  |  Ask: ${up_book['best_ask']:.4f}  |  Spread: ${up_book['spread']:.4f}", "green"))
        else:
            print(colored(f"  UP   | No order book", "green"))

        if down_book:
            print(colored(f"  DOWN | Bid: ${down_book['best_bid']:.4f}  |  Ask: ${down_book['best_ask']:.4f}  |  Spread: ${down_book['spread']:.4f}", "red"))
        else:
            print(colored(f"  DOWN | No order book", "red"))

def draw_pnl_box(state, up_book, down_book):
    """BIG P&L display when in a position"""
    if not state['position_side'] or not state['position_token_id']:
        return

    entry_price = state['entry_price']
    shares = state['position_shares']
    side = state['position_side']

    # Get current bid for our token (that's what we could sell at)
    current_book = up_book if side == "UP" else down_book
    if not current_book:
        return

    current_bid = current_book['best_bid']
    cost_basis = entry_price * shares
    current_value = current_bid * shares
    pnl_usd = current_value - cost_basis
    pnl_pct = ((current_bid / entry_price) - 1) * 100 if entry_price > 0 else 0

    is_winning = pnl_usd >= 0
    pnl_color = "green" if is_winning else "red"
    side_emoji = "[UP]" if side == "UP" else "[DOWN]"

    # Fun dynamic elements
    if pnl_pct > 50:
        vibe = "TO THE MOON!!!"
    elif pnl_pct > 20:
        vibe = "COOKING!"
    elif pnl_pct > 5:
        vibe = "Looking good!"
    elif pnl_pct > -5:
        vibe = "Flat..."
    elif pnl_pct > -20:
        vibe = "Come on..."
    elif pnl_pct > -50:
        vibe = "Pain..."
    else:
        vibe = "GUH"

    # Big flashy P&L box
    print()
    print(colored(f"  +===================================================+", pnl_color, attrs=['bold']))
    print(colored(f"  |  {side_emoji} POSITION: {side:<6}                            |", pnl_color, attrs=['bold']))
    print(colored(f"  |                                                   |", pnl_color))
    print(colored(f"  |    Entry:   ${entry_price:.4f}                              |", "white"))
    print(colored(f"  |    Current: ${current_bid:.4f}                              |", "white"))
    print(colored(f"  |    Shares:  {shares:.1f}                                  |", "white"))
    print(colored(f"  |                                                   |", pnl_color))

    # The big P&L line
    pnl_str = f"${pnl_usd:+.2f} ({pnl_pct:+.1f}%)"
    if is_winning:
        print(colored(f"  |    P&L:  {pnl_str:<20}                  |", "green", attrs=['bold']))
    else:
        print(colored(f"  |    P&L:  {pnl_str:<20}                  |", "red", attrs=['bold']))

    print(colored(f"  |                                                   |", pnl_color))
    print(colored(f"  |    {vibe:<40}      |", pnl_color, attrs=['bold']))
    print(colored(f"  |                                                   |", pnl_color))
    print(colored(f"  |    [X] = Close at market  |  Hold to expiry       |", "yellow"))
    print(colored(f"  +===================================================+", pnl_color, attrs=['bold']))

def draw_status(state, up_book, down_book):
    """Status area"""
    # If we have a position, show the big P&L box
    if state['position_side']:
        draw_pnl_box(state, up_book, down_book)
        return

    print()
    print(colored("  ---------------------------------------------------------", "white"))

    if state['order_side']:
        side = state['order_side']
        price = state['order_price']
        color = "green" if side == "UP" else "red"
        # Animated waiting dots
        dots = "." * (int(time.time()) % 4)
        print(colored(f"  ORDER OPEN: {side} limit @ ${price:.4f} {dots}", color, attrs=['bold']))
        print(colored(f"  Press [B] or [S] to cancel & re-place  |  Waiting for pullback...", "yellow"))
    else:
        print(colored(f"  READY TO BET!", "yellow", attrs=['bold']))
        print(colored(f"  Press [B] to buy UP  |  Press [S] to buy DOWN", "white", attrs=['bold']))

    print(colored("  ---------------------------------------------------------", "white"))

def draw_controls():
    print()
    print(colored("  +-------------------------------------+", "white"))
    print(colored("  |  [B] = Buy UP    [S] = Buy DOWN     |", "white", attrs=['bold']))
    print(colored("  |  [X] = Close Position at Market      |", "white", attrs=['bold']))
    print(colored("  |  [Q] = Quit                          |", "white", attrs=['bold']))
    print(colored("  +-------------------------------------+", "white"))
    print(colored("  >>> ", "yellow", attrs=['bold']), end='', flush=True)

# ============================================================================
# MAIN BOT
# ============================================================================

def main():
    global SESSION_WINS, SESSION_LOSSES, SESSION_PNL, SESSION_TRADES

    import tty
    import termios

    print(colored("Moon Dev's Easy Hyper Gambler - Starting up...", "cyan"))

    # State
    state = {
        'order_side': None,       # "UP" or "DOWN" if we have a pending order
        'order_price': 0,
        'order_token_id': None,
        'position_side': None,    # "UP" or "DOWN" if we're holding
        'position_shares': 0,
        'position_token_id': None,
        'entry_price': 0,         # Track entry for P&L
        'current_market_ts': None,
        'market_info': None,
        'price_to_beat': None,    # BTC price at market open
    }

    last_display_time = 0
    last_book_fetch = 0
    up_book = None
    down_book = None
    btc_price = None
    hype_msg = random.choice(HYPE_MESSAGES)
    last_hype_change = time.time()

    # Set terminal to raw mode for non-blocking single char input
    old_settings = termios.tcgetattr(sys.stdin)

    def cleanup():
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def get_char():
        """Non-blocking single character read"""
        if select.select([sys.stdin], [], [], 0.0)[0]:
            return sys.stdin.read(1).upper()
        return None

    tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            now = time.time()
            market_ts = get_current_market_timestamp()
            time_remaining = get_time_remaining(market_ts)

            # Rotate hype message every 15 seconds
            if now - last_hype_change > 15:
                hype_msg = random.choice(HYPE_MESSAGES)
                last_hype_change = now

            # -- New market detected --
            if market_ts != state['current_market_ts']:
                # If we had a position that expired, count it
                if state['position_side'] and state['position_token_id']:
                    current_book = up_book if state['position_side'] == "UP" else down_book
                    if current_book and state['entry_price'] > 0:
                        final_bid = current_book['best_bid']
                        pnl = (final_bid - state['entry_price']) * state['position_shares']
                        SESSION_PNL += pnl
                        SESSION_TRADES += 1
                        if pnl >= 0:
                            SESSION_WINS += 1
                        else:
                            SESSION_LOSSES += 1

                # Cancel any unfilled orders from previous market
                if state['order_side'] and state['order_token_id'] and not state['position_side']:
                    cancel_token_orders(state['order_token_id'])

                state['current_market_ts'] = market_ts
                state['order_side'] = None
                state['order_price'] = 0
                state['order_token_id'] = None
                state['position_side'] = None
                state['position_shares'] = 0
                state['position_token_id'] = None
                state['entry_price'] = 0
                state['market_info'] = None
                state['price_to_beat'] = None
                up_book = None
                down_book = None

                # Grab BTC price right at market open = price to beat
                opening_price = get_btc_price()
                if opening_price:
                    state['price_to_beat'] = opening_price
                    btc_price = opening_price

                # Find the new market
                for attempt in range(8):
                    state['market_info'] = get_market_info(market_ts)
                    if state['market_info']:
                        break
                    time.sleep(2)

                # If we didn't get it above, grab it now
                if not state['price_to_beat']:
                    state['price_to_beat'] = get_btc_price()

                if not state['market_info']:
                    next_ts = market_ts + MARKET_DURATION
                    wait = next_ts - int(time.time())
                    if wait > 0:
                        clear_screen()
                        draw_header(hype_msg)
                        print(colored(f"\n  Market not found, waiting {wait}s for next one...", "yellow"))
                        time.sleep(min(wait + 1, 10))
                    continue

            # -- Fetch order books + BTC price every 3 seconds --
            if state['market_info'] and now - last_book_fetch > 3:
                last_book_fetch = now
                up_book = get_order_book(state['market_info']['up_token_id'])
                down_book = get_order_book(state['market_info']['down_token_id'])
                btc_price = get_btc_price()

                # Check if our order got filled
                if state['order_side'] and state['order_token_id'] and not state['position_side']:
                    shares = check_position(state['order_token_id'])
                    if shares > 0:
                        state['position_side'] = state['order_side']
                        state['position_shares'] = shares
                        state['position_token_id'] = state['order_token_id']
                        state['entry_price'] = state['order_price']
                        state['order_side'] = None
                        state['order_price'] = 0
                        state['order_token_id'] = None

            # -- Redraw display every second --
            if now - last_display_time > 1:
                last_display_time = now
                clear_screen()
                draw_header(hype_msg)
                draw_session_stats()

                if not state['market_info']:
                    next_ts = market_ts + MARKET_DURATION
                    wait = max(0, next_ts - int(time.time()))
                    print(colored(f"\n  Waiting for next market... {wait}s", "yellow"))
                else:
                    draw_market_info(state['market_info'], time_remaining, up_book, down_book, btc_price, state['price_to_beat'])
                    draw_status(state, up_book, down_book)
                    draw_controls()

            # -- Check for input --
            char = get_char()
            if char:
                market_info = state['market_info']
                if not market_info:
                    continue

                neg_risk = market_info.get('neg_risk', False)

                # -- B = Buy UP --
                if char == 'B':
                    token_id = market_info['up_token_id']

                    # Cancel existing order if any
                    if state['order_token_id']:
                        cancel_token_orders(state['order_token_id'])
                        time.sleep(0.5)

                    book = get_order_book(token_id)
                    if not book:
                        continue

                    # Bid X% under the best bid for a deal
                    bid_price = round(book['best_bid'] * (1 - BID_DISCOUNT_PCT / 100), 4)
                    shares = calculate_shares(BET_SIZE_USD, bid_price)
                    if shares <= 0:
                        continue

                    resp = place_limit_order(token_id, "BUY", bid_price, shares, neg_risk=neg_risk)

                    if resp and resp.get('orderID'):
                        state['order_side'] = "UP"
                        state['order_price'] = bid_price
                        state['order_token_id'] = token_id
                    time.sleep(1)

                # -- S = Buy DOWN --
                elif char == 'S':
                    token_id = market_info['down_token_id']

                    # Cancel existing order if any
                    if state['order_token_id']:
                        cancel_token_orders(state['order_token_id'])
                        time.sleep(0.5)

                    book = get_order_book(token_id)
                    if not book:
                        continue

                    # Bid X% under the best bid for a deal
                    bid_price = round(book['best_bid'] * (1 - BID_DISCOUNT_PCT / 100), 4)
                    shares = calculate_shares(BET_SIZE_USD, bid_price)
                    if shares <= 0:
                        continue

                    resp = place_limit_order(token_id, "BUY", bid_price, shares, neg_risk=neg_risk)

                    if resp and resp.get('orderID'):
                        state['order_side'] = "DOWN"
                        state['order_price'] = bid_price
                        state['order_token_id'] = token_id
                    time.sleep(1)

                # -- X = Close position at market --
                elif char == 'X':
                    if not state['position_side'] or not state['position_token_id']:
                        continue

                    token_id = state['position_token_id']
                    shares = state['position_shares']

                    # Sell into the bid to exit immediately
                    book = get_order_book(token_id)
                    if not book:
                        continue

                    sell_price = book['best_bid']

                    # Calculate P&L for this close
                    close_pnl = (sell_price - state['entry_price']) * shares
                    SESSION_PNL += close_pnl
                    SESSION_TRADES += 1
                    if close_pnl >= 0:
                        SESSION_WINS += 1
                    else:
                        SESSION_LOSSES += 1

                    # Cancel any existing orders first
                    cancel_token_orders(token_id)
                    time.sleep(0.5)

                    resp = place_limit_order(token_id, "SELL", sell_price, shares, neg_risk=neg_risk)

                    if resp and resp.get('orderID'):
                        state['position_side'] = None
                        state['position_shares'] = 0
                        state['position_token_id'] = None
                        state['entry_price'] = 0
                    time.sleep(1)

                # -- Q = Quit --
                elif char == 'Q':
                    raise KeyboardInterrupt

            time.sleep(0.1)

    except KeyboardInterrupt:
        cleanup()
        print(colored(f"\n\n  {'='*60}", "yellow"))
        print(colored(f"  Moon Dev - Easy Hyper Gambler stopped! GG.", "yellow", attrs=['bold']))
        print(colored(f"  {'='*60}", "yellow"))

        # Final session stats
        if SESSION_TRADES > 0:
            pnl_color = "green" if SESSION_PNL >= 0 else "red"
            wr = SESSION_WINS / SESSION_TRADES * 100
            print(colored(f"\n  FINAL SESSION STATS:", "cyan", attrs=['bold']))
            print(colored(f"  Trades: {SESSION_TRADES} | Wins: {SESSION_WINS} | Losses: {SESSION_LOSSES} | Win Rate: {wr:.0f}%", "white"))
            print(colored(f"  Session P&L: ${SESSION_PNL:+.2f}", pnl_color, attrs=['bold']))
        print()

        # Cancel any open orders on exit
        if state.get('order_token_id') and state.get('order_side') and not state.get('position_side'):
            print(colored("  Canceling open orders...", "yellow"))
            cancel_token_orders(state['order_token_id'])
    finally:
        cleanup()

if __name__ == "__main__":
    print("Moon Dev's Easy Hyper Gambler - 288 chances a day, let's ride!")
    main()
```
## Prerequisites & Setup

Before running this bot, you need a few things set up:

### Required Setup

**1. Polymarket Account** — You need a funded Polymarket account with USDC on Polygon. Set up API credentials at polymarket.com.

**2. Python Environment** — Python 3.10+ with conda (or venv). Install deps: pip install requests python-dotenv termcolor web3 py-clob-client

**3. .env File** — Create a .env file with: PRIVATE_KEY, PUBLIC_KEY, API_KEY, SECRET, PASSPHRASE

**4. nice_funcs.py** — The helper module needs to be in an examples/ directory one level up from the script

.env file template

```python
PRIVATE_KEY=your_polymarket_private_key_here
PUBLIC_KEY=your_polygon_wallet_address_here
API_KEY=your_polymarket_api_key
SECRET=your_polymarket_api_secret
PASSPHRASE=your_polymarket_api_passphrase
```
## Want to learn more?

Join the live Zoom calls where Moon Dev walks through these bots in real time and answers your questions.

[Join the Live Zoom Call](https://moondev.com/t/blog/polymarket-five-minute-bot)

Built with love by Moon Dev

### Related Resources

[Polymarket Hyperliquid Liquidation Statistical Arbitrage](https://moondev.com/polymarket-hyperliquid-liquidation-statistical-arbitrage)

— Advanced bot that uses liquidation data to trade Polymarket and hedge on Hyperliquid

[HIP3 Liquidation Trading Bot](https://moondev.com/hip-3-liquidation-trading-bot)

— Trade liquidation cascades on HIP3 automatically

[HIP3 Funding Rate Scanner](https://moondev.com/hip-3-funding-rate-scanner)

— Scan every funding rate on Hyperliquid including HIP3 tokenized assets

[Moon Dev API Documentation](https://moondev.com/docs)

— Liquidation data, funding rates, position snapshots, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations across exchanges
