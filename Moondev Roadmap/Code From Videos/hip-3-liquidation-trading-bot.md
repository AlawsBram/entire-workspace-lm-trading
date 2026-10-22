<!-- source: https://moondev.com/hip-3-liquidation-trading-bot -->
<!-- captured: 2026-10-07 -->
<!-- title: HIP-3 Liquidation Trading Bot -->

HIP3 Liquidation Trading Bot for Hyperliquid | Open Source Python Bot | Moon Dev

Moon Dev Open Source

# This Bot Trades Liquidation Cascades on HIP3 Before They Happen

When $250k+ in positions are about to get liquidated and momentum confirms the direction, this bot pulls the trigger automatically. Fully open source. Copy it, run it, make it yours.

By Moon Dev · March 7, 2026

If you've been watching HIP3 on Hyperliquid, you already know what happens when a cluster of overleveraged positions gets close to liquidation. Price moves toward them, they get liquidated, the liquidations push price further, and more positions blow up. It's a cascade.

Most people watch this happen. This bot trades it.

It pulls real time position data from the Moon Dev API to find where the big liquidation clusters are sitting. It checks how close price is to those clusters. It confirms with 1 hour momentum candles. And if everything lines up, it enters a trade in the direction of the cascade.

Let me walk you through exactly how it works, piece by piece. Every code block below is clickable and will copy instantly so you can paste it right into your project.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 1: The Imports

This bot is completely self contained. One file, no custom project dependencies. Everything it needs comes from standard Python packages. The Hyperliquid SDK handles the exchange connection, pandas handles the candle data, and requests talks to the Moon Dev API.

Imports

```python
from __future__ import annotations

import math
import os
import time
import traceback
from datetime import datetime, timedelta

import colorama
import eth_account
import pandas as pd
import requests
from colorama import Fore
from dotenv import load_dotenv
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

colorama.init(autoreset=True)
load_dotenv()
```
The colorama import gives you color coded terminal output so you can actually read what the bot is doing at a glance. Green means position open, yellow means action taken, cyan means data readout.

## Step 2: The Configuration

Everything is controlled through environment variables so you never have to touch the code to change behavior. Set these in a .env file and the bot reads them on startup.

Configuration

```python
DEX = os.getenv("H3_BOT_DEX", "xyz")
SYMBOL = os.getenv("H3_BOT_SYMBOL", "CL")
LEVERAGE = int(os.getenv("H3_BOT_LEVERAGE", "3"))
POSITION_SIZE_USD = float(os.getenv("H3_BOT_POSITION_USD", "15"))
MIN_EFFECTIVE_NOTIONAL_USD = float(os.getenv("H3_BOT_MIN_NOTIONAL_USD", "11"))

NEAR_LIQ_MIN_TOTAL_USD = float(os.getenv("H3_BOT_NEAR_LIQ_MIN_TOTAL_USD", "250000"))
TRIGGER_DISTANCE_PCT = float(os.getenv("H3_BOT_TRIGGER_DISTANCE_PCT", "2.5"))
LIQUIDATION_TIMEFRAME = os.getenv("H3_BOT_LIQ_TIMEFRAME", "30d")

TAKE_PROFIT_PERCENT = float(os.getenv("H3_BOT_TP_PERCENT", "1.5"))
STOP_LOSS_PERCENT = float(os.getenv("H3_BOT_SL_PERCENT", "-1.0"))
MAX_HOLD_HOURS = float(os.getenv("H3_BOT_MAX_HOLD_HOURS", "2"))

ENTRY_SLIPPAGE_BUFFER_PCT = float(os.getenv("H3_BOT_ENTRY_BUFFER_PCT", "0.002"))
LOOP_INTERVAL_SECONDS = int(os.getenv("H3_BOT_LOOP_SECONDS", "30"))
```
The key ones to understand: NEAR_LIQ_MIN_TOTAL_USD is the minimum dollar value of positions that need to be near liquidation before the bot cares. Default is $250k. If there's less than that sitting close to getting blown up, the bot stays flat.

TRIGGER_DISTANCE_PCT controls how close those positions need to be to their liquidation price. Default is 2.5%, meaning positions have to be within 2.5% of getting liquidated for the bot to consider trading.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 3: Account Setup

The bot loads your Hyperliquid private key from the environment and creates an account object. This is what signs your orders on chain. It also sets up a couple utility functions that get reused everywhere.

Account and utilities

```python
HYPER_LIQUID_KEY = os.getenv("HYPER_LIQUID_KEY")
if not HYPER_LIQUID_KEY:
    raise RuntimeError("HYPER_LIQUID_KEY is not set in the environment.")

account = eth_account.Account.from_key(HYPER_LIQUID_KEY)
position_entry_time = None

def round_down(value: float, decimals: int) -> float:
    factor = 10 ** decimals
    return math.floor(value * factor) / factor

def moondev_auth_headers():
    api_key = os.getenv("MOONDEV_API_KEY")
    return {"X-API-Key": api_key} if api_key else {}
```
That round_down function is important. When calculating order sizes, you always want to round down, not up. Rounding up could mean you try to buy more than you can afford and the order gets rejected.

## Step 4: Connecting to Hyperliquid HIP3

HIP3 assets live on Hyperliquid but they're on separate "dexes" within the protocol. Symbols look like xyz:CL (crude oil) or xyz:GOLD. These helper functions handle all the resolution and connection logic so you don't have to think about it.

HIP3 connection helpers

```python
def get_h3_info(dex='xyz', skip_ws=True):
    return Info(constants.MAINNET_API_URL, skip_ws=skip_ws, perp_dexs=[dex])

def get_h3_exchange(account, dex='xyz'):
    return Exchange(account, constants.MAINNET_API_URL, perp_dexs=[dex])

def resolve_h3_symbol(coin, dex='xyz', info=None):
    if ':' in coin:
        return coin

    info = info or get_h3_info(dex=dex, skip_ws=True)
    requested = str(coin).upper()
    preferred_symbol = f'{dex}:{requested}'

    meta = info.meta(dex=dex)
    universe = meta.get('universe', [])
    available = {asset['name'] for asset in universe if isinstance(asset, dict) and 'name' in asset}

    if preferred_symbol in available:
        return preferred_symbol

    matches = sorted(symbol for symbol in available if symbol.upper().endswith(f':{requested}'))
    if matches:
        return matches[0]

    raise KeyError(f'Could not resolve H3 symbol for {coin} on dex {dex}')
```
The resolve_h3_symbol function is doing the heavy lifting here. You can pass in just "CL" and it figures out which dex has it and returns the full symbol. It checks the metadata from Hyperliquid's API and matches it up. Simple but essential.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 5: Getting Price and Candle Data

The bot needs two things from the exchange itself: the current mid price (for placing orders at the right level) and historical candle data (for checking momentum). These two functions handle that.

Price and candle data

```python
def get_h3_mid_price(coin, dex='xyz', info=None):
    info = info or get_h3_info(dex=dex, skip_ws=True)
    symbol = resolve_h3_symbol(coin, dex=dex, info=info)
    mids = info.all_mids(dex=dex)
    if symbol in mids:
        return float(mids[symbol])
    if coin in mids:
        return float(mids[coin])
    raise KeyError(f'Could not find mid price for {symbol}')

def get_h3_candles(coin, interval='1h', bars=200, dex='xyz'):
    info = get_h3_info(dex=dex, skip_ws=True)
    symbol = resolve_h3_symbol(coin, dex=dex, info=info)
    end_time = datetime.now()
    interval_to_hours = {
        '1m': 1 / 60, '5m': 5 / 60, '15m': 15 / 60,
        '30m': 0.5, '1h': 1, '4h': 4, '1d': 24,
    }
    lookback_hours = max(int(interval_to_hours.get(interval, 1) * (bars + 24)), 24)
    start_time = end_time - timedelta(hours=lookback_hours)

    candles = info.candles_snapshot(
        symbol, interval,
        int(start_time.timestamp() * 1000),
        int(end_time.timestamp() * 1000),
    )
    if not isinstance(candles, list) or not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles).rename(columns={
        't': 'timestamp', 's': 'symbol', 'i': 'interval',
        'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close',
        'v': 'volume', 'n': 'trades',
    })
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.sort_values('timestamp').tail(bars).reset_index(drop=True)
```
The candle function pulls OHLCV data and returns a clean pandas DataFrame. The bot only uses the last 3 candles for momentum checks, but this function supports up to 200 bars if you want to add more complex indicators later.

## Step 6: Position and Order Functions

These are the functions that actually interact with your wallet on Hyperliquid. Checking if you have a position open, placing limit orders, canceling orders, and closing positions. Think of them as your trading toolkit.

Position and order functions

```python
def get_h3_position(coin, account, dex='xyz'):
    info = get_h3_info(dex=dex, skip_ws=True)
    symbol = resolve_h3_symbol(coin, dex=dex, info=info)
    user_state = info.user_state(account.address, dex=dex)

    for asset in user_state.get('assetPositions', []):
        position = asset.get('position', {})
        if position.get('coin') == symbol and float(position.get('szi', 0) or 0) != 0:
            return position, True
    return None, False

def h3_price_to_order_price(coin, px, dex='xyz', info=None):
    info = info or get_h3_info(dex=dex, skip_ws=True)
    symbol = resolve_h3_symbol(coin, dex=dex, info=info)
    asset = info.name_to_asset(symbol)
    sz_decimals = info.asset_to_sz_decimals[asset]
    return round(float(f"{float(px):.5g}"), 6 - sz_decimals)

def h3_limit_order(coin, is_buy, sz, limit_px, reduce_only, account, dex='xyz'):
    info = get_h3_info(dex=dex, skip_ws=True)
    exchange = get_h3_exchange(account, dex=dex)
    symbol = resolve_h3_symbol(coin, dex=dex, info=info)
    asset = info.name_to_asset(symbol)
    sz_decimals = info.asset_to_sz_decimals[asset]
    sz = round(float(sz), sz_decimals)
    limit_px = h3_price_to_order_price(symbol, limit_px, dex=dex, info=info)

    return exchange.order(
        symbol, is_buy, sz, float(limit_px),
        {"limit": {"tif": "Gtc"}},
        reduce_only=reduce_only,
    )

def cancel_all_h3_orders(account, dex='xyz', coin=None):
    orders = get_h3_open_orders(account, dex=dex, coin=coin)
    results = []
    for order in orders:
        try:
            info = get_h3_info(dex=dex, skip_ws=True)
            exchange = get_h3_exchange(account, dex=dex)
            symbol = resolve_h3_symbol(order.get('coin'), dex=dex, info=info)
            results.append(exchange.cancel(symbol, order['oid']))
        except Exception as e:
            results.append({'error': str(e)})
    return results

def close_h3_position(coin, account, dex='xyz', slippage=0.05):
    info = get_h3_info(dex=dex, skip_ws=True)
    exchange = get_h3_exchange(account, dex=dex)
    symbol = resolve_h3_symbol(coin, dex=dex, info=info)
    return exchange.market_close(symbol, slippage=slippage)
```
The h3_price_to_order_price function handles Hyperliquid's precision requirements. Each asset has different decimal precision for sizes and prices, and if you send an order with too many decimals it gets rejected. This function formats everything correctly.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 7: Pulling Liquidation Data from Moon Dev API

This is where the edge comes from. The Moon Dev API tracks every HIP3 position and knows exactly how close each one is to liquidation. The bot pulls two things: historical liquidation stats and current near liquidation positions.

Moon Dev API integration

```python
def get_moondev_hip3_liquidations(timeframe='30d', symbol=None, base_url='https://api.moondev.com'):
    response = requests.get(
        f'{base_url}/api/hip3_liquidations/{timeframe}.json',
        headers=moondev_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if symbol is None:
        return payload

    stats = payload.get('stats', {})
    by_asset = stats.get('by_asset', {}) if isinstance(stats, dict) else {}
    return by_asset.get(str(symbol).upper(), {})

def get_moondev_hip3_near_liq_positions(symbol='CL', base_url='https://api.moondev.com'):
    api_key = os.getenv('MOONDEV_API_KEY')
    params = {'api_key': api_key} if api_key else {}
    response = requests.get(
        f'{base_url}/api/positions/all_hip3.json',
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    symbols = payload.get('symbols', {})
    requested = str(symbol).upper()

    if requested in symbols:
        return symbols[requested]

    prefixed = next(
        (value for key, value in symbols.items()
         if isinstance(key, str) and key.upper().endswith(f':{requested}')),
        None,
    )
    return prefixed if prefixed is not None else {}
```
The position data comes back with every long and short, their size, their liquidation price, and how far they are from it as a percentage. That distance_pct field is what the bot uses to know if a cascade is about to happen.

## Step 8: Checking Momentum

Liquidation clusters alone aren't enough. The bot also needs momentum confirmation. It looks at the last two hourly candles: if the most recent close is lower than the previous one, that's bearish. If it's higher, that's bullish. Simple, but it keeps the bot from jumping into trades where price is actually moving away from the liquidation cluster.

Momentum confirmation

```python
def get_momentum_context():
    candles = get_h3_candles(SYMBOL, interval="1h", bars=3, dex=DEX)
    if candles.empty or len(candles) < 2:
        return {
            "bullish": False, "bearish": False,
            "last_close": None, "prev_close": None,
        }

    last_close = float(candles["close"].iloc[-1])
    prev_close = float(candles["close"].iloc[-2])
    return {
        "bullish": last_close > prev_close,
        "bearish": last_close < prev_close,
        "last_close": last_close,
        "prev_close": prev_close,
    }
```
This is intentionally simple. You could swap this out for RSI, MACD, or any other indicator you like. The point is that the bot won't trade a long cascade setup if price is actually bouncing. It needs price to be moving toward those liquidation levels, not away from them.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 9: Building the Signal

This function pulls everything together. It grabs the near liquidation positions, the historical stats, and the momentum context, then filters down to just the positions that are within the trigger distance. This is the full picture the bot looks at before deciding to trade.

Signal context builder

```python
def get_signal_context():
    near_liq = get_moondev_hip3_near_liq_positions(SYMBOL)
    liq_stats = get_moondev_hip3_liquidations(LIQUIDATION_TIMEFRAME, symbol=SYMBOL)
    momentum = get_momentum_context()

    longs = near_liq.get("longs", []) if isinstance(near_liq, dict) else []
    shorts = near_liq.get("shorts", []) if isinstance(near_liq, dict) else []

    total_long_value = float(near_liq.get("total_long_value", 0) or 0) if isinstance(near_liq, dict) else 0.0
    total_short_value = float(near_liq.get("total_short_value", 0) or 0) if isinstance(near_liq, dict) else 0.0

    longs_in_range = [
        pos for pos in longs
        if float(pos.get("distance_pct", 999) or 999) <= TRIGGER_DISTANCE_PCT
    ]
    shorts_in_range = [
        pos for pos in shorts
        if float(pos.get("distance_pct", 999) or 999) <= TRIGGER_DISTANCE_PCT
    ]

    near_long_value = sum(float(pos.get("value", 0) or 0) for pos in longs_in_range)
    near_short_value = sum(float(pos.get("value", 0) or 0) for pos in shorts_in_range)

    return {
        "near_liq": near_liq, "liq_stats": liq_stats, "momentum": momentum,
        "total_long_value": total_long_value, "total_short_value": total_short_value,
        "near_long_value": near_long_value, "near_short_value": near_short_value,
        "longs_in_range_count": len(longs_in_range),
        "shorts_in_range_count": len(shorts_in_range),
        "closest_long": longs[0] if longs else None,
        "closest_short": shorts[0] if shorts else None,
    }
```
Notice how it filters positions by TRIGGER_DISTANCE_PCT and sums up the total dollar value of what's in range. This is what the next function uses to decide if the cascade is big enough to trade.

## Step 10: Making the Decision

This is the brain of the bot. Three conditions need to be true at the same time for it to pull the trigger. Heavy value near liquidation, positions close enough to the edge, and momentum confirming the direction.

Trade decision logic

```python
def choose_trade(context):
    closest_long = context["closest_long"]
    closest_short = context["closest_short"]
    near_long_value = context["near_long_value"]
    near_short_value = context["near_short_value"]
    momentum = context["momentum"]

    long_distance = float(closest_long.get("distance_pct", 999)) if closest_long else 999.0
    short_distance = float(closest_short.get("distance_pct", 999)) if closest_short else 999.0

    # Longs about to get liquidated + bearish momentum = short
    if (
        near_long_value >= NEAR_LIQ_MIN_TOTAL_USD
        and long_distance <= TRIGGER_DISTANCE_PCT
        and momentum["bearish"]
    ):
        return {"should_trade": True, "is_buy": False, "reason": "Long cascade incoming"}

    # Shorts about to get liquidated + bullish momentum = long
    if (
        near_short_value >= NEAR_LIQ_MIN_TOTAL_USD
        and short_distance <= TRIGGER_DISTANCE_PCT
        and momentum["bullish"]
    ):
        return {"should_trade": True, "is_buy": True, "reason": "Short squeeze incoming"}

    return {"should_trade": False, "is_buy": None, "reason": "No setup"}
```
The logic is straightforward. If there's a ton of long positions within 2.5% of getting liquidated AND the last hourly candle closed lower than the previous one (bearish momentum), the bot goes short. It's betting that those longs are about to get liquidated and push price down even further.

The reverse works too. Heavy shorts near liquidation plus bullish momentum means go long. Ride the short squeeze.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 11: Executing the Trade

When the bot decides to trade, it calculates the right order size based on your configured position size, sets the leverage, adds a small slippage buffer to the limit price so the order actually fills, and sends it. It also cancels any stale orders first so nothing conflicts.

Order preparation and entry

```python
def prepare_order(is_buy: bool):
    info = get_h3_info(dex=DEX, skip_ws=True)
    exchange = get_h3_exchange(account, dex=DEX)
    symbol = resolve_h3_symbol(SYMBOL, dex=DEX, info=info)
    current_mid = get_h3_mid_price(SYMBOL, dex=DEX, info=info)

    try:
        exchange.update_leverage(LEVERAGE, symbol, is_cross=False)
    except Exception as e:
        print(f"Leverage update warning: {e}")

    asset = info.name_to_asset(symbol)
    sz_decimals = info.asset_to_sz_decimals[asset]
    effective_notional = max(POSITION_SIZE_USD, MIN_EFFECTIVE_NOTIONAL_USD)
    raw_entry_price = current_mid * (1 + ENTRY_SLIPPAGE_BUFFER_PCT) if is_buy else current_mid * (1 - ENTRY_SLIPPAGE_BUFFER_PCT)
    entry_price = h3_price_to_order_price(symbol, raw_entry_price, dex=DEX, info=info)
    order_size = round_down(effective_notional / entry_price, sz_decimals)

    if order_size <= 0:
        raise ValueError(f"Computed order size is zero for {symbol}")

    return {
        "symbol": symbol, "mid": current_mid,
        "entry_price": entry_price, "order_size": order_size,
        "effective_notional": effective_notional,
    }

def place_entry(is_buy: bool, reason: str):
    global position_entry_time

    order = prepare_order(is_buy)
    cancel_all_h3_orders(account, dex=DEX, coin=SYMBOL)

    result = h3_limit_order(
        SYMBOL, is_buy, order["order_size"],
        order["entry_price"], False, account, dex=DEX,
    )

    time.sleep(3)
    state = get_h3_position_state()
    if state["in_position"]:
        position_entry_time = datetime.now()
```
The slippage buffer is 0.2% by default. For buys, it sets the limit price slightly above mid. For sells, slightly below. This way the order fills immediately like a market order but you still get limit order protections against extreme slippage.

## Step 12: Managing the Position

Once in a trade, the bot checks three things every loop: has it hit take profit, has it hit stop loss, or has it been open too long. Default is 1.5% TP, 1% SL, and a 2 hour max hold time. If any of those trigger, it closes.

Position management

```python
def get_h3_position_state():
    position, in_position = get_h3_position(SYMBOL, account, dex=DEX)
    if not in_position or not position:
        return {
            "in_position": False, "position": None,
            "size": 0.0, "entry_px": 0.0, "pnl_perc": 0.0, "is_long": None,
        }

    size = float(position.get("szi", 0) or 0)
    pnl_perc = float(position.get("returnOnEquity", 0) or 0) * 100
    return {
        "in_position": True, "position": position, "size": size,
        "entry_px": float(position.get("entryPx", 0) or 0),
        "pnl_perc": pnl_perc, "is_long": size > 0,
    }

def close_position(reason: str):
    global position_entry_time
    cancel_all_h3_orders(account, dex=DEX, coin=SYMBOL)
    close_h3_position(SYMBOL, account, dex=DEX, slippage=0.03)
    position_entry_time = None

def manage_open_position():
    global position_entry_time

    state = get_h3_position_state()
    if not state["in_position"]:
        position_entry_time = None
        return False

    if position_entry_time is None:
        position_entry_time = datetime.now()

    elapsed_hours = (datetime.now() - position_entry_time).total_seconds() / 3600

    if state["pnl_perc"] >= TAKE_PROFIT_PERCENT:
        close_position(f"take profit hit ({state['pnl_perc']:.2f}%)")
        return True

    if state["pnl_perc"] <= STOP_LOSS_PERCENT:
        close_position(f"stop loss hit ({state['pnl_perc']:.2f}%)")
        return True

    if elapsed_hours >= MAX_HOLD_HOURS:
        close_position(f"max hold reached ({elapsed_hours:.2f}h)")
        return True

    return True
```
The max hold time is important. Liquidation cascades are fast events. If it hasn't played out in 2 hours, the thesis is probably wrong and it's better to close and wait for the next setup.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

## Step 13: The Main Loop

This ties it all together. Every 30 seconds the bot runs one cycle: check if there's an open position to manage, if not then look for a new setup, and if the setup is there then take the trade. Clean and simple.

Main bot loop

```python
def bot():
    if manage_open_position():
        return

    context = get_signal_context()
    trade = choose_trade(context)
    if not trade["should_trade"]:
        return

    place_entry(trade["is_buy"], trade["reason"])

if __name__ == "__main__":
    print("Starting H3 liquidation momentum loop...")
    try:
        bot()
        while True:
            time.sleep(LOOP_INTERVAL_SECONDS)
            bot()
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as e:
        print(f"Bot error: {e}")
        print(traceback.format_exc())
```
Notice the priority order: managing an existing position always comes first. The bot won't look for new setups if it's already in a trade. One position at a time. This keeps things clean and prevents overexposure.

## Running the Bot

Set up your .env file with your keys and you're good to go.

.env file

```python
MOONDEV_API_KEY=your_moondev_api_key
HYPER_LIQUID_KEY=your_hyperliquid_private_key

# Optional overrides
H3_BOT_DEX=xyz
H3_BOT_SYMBOL=CL
H3_BOT_LEVERAGE=3
H3_BOT_POSITION_USD=15
H3_BOT_NEAR_LIQ_MIN_TOTAL_USD=250000
H3_BOT_TRIGGER_DISTANCE_PCT=2.5
H3_BOT_TP_PERCENT=1.5
H3_BOT_SL_PERCENT=-1.0
H3_BOT_MAX_HOLD_HOURS=2
H3_BOT_LOOP_SECONDS=30
```
Install dependencies and run

```python
pip install requests pandas python-dotenv colorama eth-account hyperliquid-python-sdk
python h3_liq_momentum_bot.py
```
It loops every 30 seconds by default. Each loop it checks for near liquidation positions, confirms momentum, and either enters a new trade or manages the existing one. All the output is color coded in your terminal so you can see exactly what it's doing.

### Want to build this live with us?

We walk through bots like this on our live Zoom calls. Come hang out, ask questions, and build alongside the Moon Dev community.

[Join the Live Zoom Call](https://moondev.com/t/blog/hip-3-liquidation-trading-bot)

Built with love by Moon Dev

### Related Resources

[Moon Dev API Documentation](https://moondev.com/docs)

— HIP3 liquidation data, position snapshots, funding rates, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations across exchanges

[Market Data Portal](https://moondev.com/data)

— Funding rates, open interest, and more
