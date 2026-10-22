<!-- source: https://moondev.com/polymarket-whale-scanner -->
<!-- captured: 2026-10-07 -->
<!-- title: Polymarket Whale Scanner — Live $1,000+ Trade WebSocket Stream -->

Polymarket Whale Scanner — Python WebSocket Bot That Streams $1,000+ Trades Live | Moon Dev

Moon Dev Open Source

# Build a Polymarket Whale Scanner in Python That Streams Every $1,000+ Trade Live

Polymarket has a public WebSocket feed that broadcasts every single trade that fills, across every market, in real time. Most people don't even know it exists. This standalone Python scanner taps into that firehose, filters for whale trades over $1,000, and prints them to your terminal in fun, color-coded style. No bot framework, no exchange API key, no paid data feed.

By Moon Dev · May 17, 2026

## Why Whale Tracking Is a Cheat Code for Prediction Markets

On crypto exchanges, whale watching is a massive industry. Bloomberg terminals, Nansen, Arkham — there's a whole tooling ecosystem built around answering one question: where is the smart money going? On Polymarket, that question has a free answer hiding in plain sight. The public WebSocket at wss://ws-live-data.polymarket.com broadcasts every fill on every market the instant it happens. You just need the code to listen.

This article walks through a standalone scanner that does exactly that. It connects to the WebSocket, subscribes to the activity feed, and prints any trade where the USD notional is at least $1,000. As trades get bigger, the output color gets hotter — cyan for small whales, magenta and yellow for medium, red bold for $50K+, and red blinking for the absolute monsters at $100K+. Every whale alert shows the market title, outcome, side, price, size, and the trader's wallet (truncated for readability).

### What This Bot Teaches You

This is a great starter project for anyone learning **live data streaming in Python**. You'll see how to manage a long-lived WebSocket connection (with ping loops to keep it alive and auto-reconnect logic when it drops), how to subscribe to topic-based feeds with JSON messages, how to filter a high-volume firehose for the trades that actually matter, and how to make a terminal program feel alive with a rotating heartbeat status line. Every pattern here translates directly to building production trading bots on any exchange.

Let me walk you through the code piece by piece. It's a single Python file with two dependencies — websocket-client and termcolor — and by the end you'll know exactly how it works.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-whale-scanner)

## Step 1: Imports, Configuration, and Shared State

The top of the file sets up everything the rest of the scanner needs. The imports are all standard Python except for the two third-party packages. websocket (from websocket-client) handles the connection lifecycle, and termcolor gives us colored terminal output. threading is in there because we'll need background loops for ping and heartbeat that run independently of the main WebSocket thread.

The configuration block is the only place you need to touch to tune the bot. Bump MIN_WHALE_USD up to $10,000 if you only want to see the real giants, or drop it to $250 to watch more activity. PING_INTERVAL is how often we send a keepalive frame so the connection doesn't get killed by idle timeouts, and HEARTBEAT_INTERVAL controls how often the fun status line prints.

The stats dict is shared mutable state — total trades seen, whales printed, the biggest whale, and when the bot started. Multiple threads will read and write this dict, but the operations are all atomic increments and assignments where we don't care about microsecond-level races, so we skip the locks and keep it simple.

Imports, configuration, and state

```python
#!/usr/bin/env python3
"""
MOON DEV's WHALE SCANNER
========================
Live WebSocket scanner that watches Polymarket for whale trades
($1,000+) across ALL markets and outcomes. Prints each whale
in fun, colorful style as it streams in.

Run it standalone - no bots required.

Built by Moon Dev
"""

import os
import sys
import json
import time
import signal
import threading
import websocket
from datetime import datetime
from termcolor import colored

# ====================================================================================================
# MOON DEV - Whale Scanner Configuration
# ====================================================================================================
MIN_WHALE_USD = 1_000                       # Only show trades >= $1,000
WEBSOCKET_URL = "wss://ws-live-data.polymarket.com"
PING_INTERVAL = 30
HEARTBEAT_INTERVAL = 10                     # Moon Dev - fun status line every 10s

# ====================================================================================================
# MOON DEV - State
# ====================================================================================================
shutdown_flag = False
ws_app = None
heartbeat_started = False  # Moon Dev - ensure heartbeat only runs once across reconnects

stats = {
    'trades_seen': 0,
    'whales_printed': 0,
    'biggest_whale_usd': 0.0,
    'biggest_whale_market': '',
    'started_at': time.time()
}

# Fun whale emojis cycled per print so the terminal feels alive
WHALE_EMOJIS = ['🐋', '🐳', '🦈', '🌊', '💰', '💎', '🚀', '🔥']

# Moon Dev - rotating heartbeat spinner + fun catchphrases
SPINNER_FRAMES = ['🌊  ', ' 🌊 ', '  🌊', ' 🌊 ']
HEARTBEAT_PHRASES = [
    "scanning the deep blue for whales",
    "Moon Dev is hunting whales",
    "still watching - whales incoming",
    "ocean is quiet... for now",
    "sonar pinging the deep",
    "every splash matters",
    "patience pays - whales are coming",
    "keeping an eye on the tide",
]
HEARTBEAT_COLORS = ['cyan', 'blue', 'magenta', 'green', 'yellow']
```
Notice the heartbeat_started flag at the module level. That one's easy to miss but it matters: when the WebSocket reconnects after a drop, on_open fires again, and we don't want to spawn a second heartbeat thread every time. The flag ensures the heartbeat loop runs exactly once for the entire lifetime of the process.

## Step 2: Graceful Shutdown and Stats Summary

When you hit Ctrl+C, a naive Python script just dies — connection still open on the server side, no summary of what you saw. This scanner does it properly. The signal.signal(signal.SIGINT, signal_handler) registration intercepts the interrupt and runs our handler instead, which sets the shutdown flag, closes the WebSocket cleanly, prints final stats, and exits.

The shutdown_flag is the cooperative cancellation signal. The ping loop and heartbeat loop both check it in their sleep loops and exit cleanly when it flips true. This pattern — global flag + cooperative threads — is way simpler than wrestling with thread cancellation APIs and works perfectly for daemon background threads.

runtime_str formats elapsed time as HH:MM:SS so you can tell at a glance how long the bot has been running. And print_stats dumps a clean summary at shutdown — runtime, total trades observed, whales printed, and the biggest single whale you caught along with which market it was on. Great for sharing on Twitter after an overnight session.

Signal handling, runtime, and stats

```python
def signal_handler(sig, frame):
    """Moon Dev - graceful shutdown on Ctrl+C"""
    global shutdown_flag, ws_app
    print(colored("\n👋 Moon Dev's Whale Scanner shutting down...", "yellow"))
    shutdown_flag = True
    if ws_app:
        ws_app.close()
    print_stats()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def runtime_str():
    elapsed = int(time.time() - stats['started_at'])
    h, rem = divmod(elapsed, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def print_stats():
    """Moon Dev - whale scanner stats summary"""
    print(colored("\n📊 Moon Dev Whale Scanner Stats", "cyan", attrs=['bold']))
    print(colored(f"   Runtime: {runtime_str()}", "white"))
    print(colored(f"   Total trades seen: {stats['trades_seen']:,}", "white"))
    print(colored(f"   Whales printed (>= ${MIN_WHALE_USD:,}): {stats['whales_printed']:,}", "green"))
    if stats['biggest_whale_usd'] > 0:
        print(colored(f"   🏆 Biggest whale: ${stats['biggest_whale_usd']:,.2f}", "yellow", attrs=['bold']))
        print(colored(f"      Market: {stats['biggest_whale_market']}", "white"))
```
One gotcha: sys.exit(0) from inside a signal handler raises SystemExit, which the main reconnect loop has to handle. We'll see how that works in the main section below — short version, the loop's outer except catches KeyboardInterrupt and breaks out cleanly.

## Step 3: Color Tiers and Whale Pretty-Printing

This is where the bot gets its personality. color_for_size is a simple stepped function: the bigger the trade, the hotter the color and the more attention-grabbing the formatting. Sub-$5K whales are cyan with no special attributes. As the dollar amounts climb, we shift through magenta bold, yellow bold, red bold, and finally red bold blinking for trades of $100K+. By the time you see blinking red text in your terminal you know something serious just happened.

print_whale is responsible for the actual output. It pulls every relevant field out of the trade payload — outcome (like "YES" or "NO"), price, size, side (BUY/SELL), market title, slug, and the trader's wallet — and formats them in a multiline block with a header bar, emoji, and color-coded fields. The wallet address gets truncated to first 8 + last 4 characters so it's readable but still uniquely identifiable.

Small detail worth calling out: outcomes get colored green when they're YES and red when they're NO, and sides get colored green for BUY and red for SELL. That visual encoding makes it possible to skim a stream of whale alerts and immediately understand the flow — green buys on YES outcomes versus red sells on NO outcomes tell very different stories about market sentiment.

Color tiers and whale formatting

```python
def color_for_size(usd):
    """Moon Dev - bigger trade = hotter color"""
    if usd >= 100_000:
        return ('red', ['bold', 'blink'])
    if usd >= 50_000:
        return ('red', ['bold'])
    if usd >= 10_000:
        return ('yellow', ['bold'])
    if usd >= 5_000:
        return ('magenta', ['bold'])
    return ('cyan', [])

def print_whale(payload, usd_amount):
    """Moon Dev - pretty-print one whale trade"""
    outcome = payload.get('outcome', '?')
    price = float(payload.get('price', 0))
    size = float(payload.get('size', 0))
    side = payload.get('side', '?').upper()
    market_title = payload.get('title', 'Unknown Market')
    market_slug = payload.get('eventSlug', '') or payload.get('slug', '')
    trader = payload.get('proxyWallet', '') or payload.get('user', '') or 'unknown'

    color, attrs = color_for_size(usd_amount)
    emoji = WHALE_EMOJIS[stats['whales_printed'] % len(WHALE_EMOJIS)]
    ts = datetime.now().strftime("%H:%M:%S")

    side_color = 'green' if side == 'BUY' else 'red'
    outcome_color = 'green' if outcome.upper() == 'YES' else 'red' if outcome.upper() == 'NO' else 'cyan'

    bar = "═" * 80
    print(colored(f"\n{bar}", color))
    print(colored(f"{emoji}  WHALE ALERT  {emoji}  ${usd_amount:,.2f}  {emoji}  [{ts}]  Moon Dev", color, attrs=attrs))
    print(colored(bar, color))
    print(colored(f"   📈 Market : {market_title}", "white", attrs=['bold']))
    if market_slug:
        print(colored(f"   🔗 Link   : https://polymarket.com/event/{market_slug}", "blue"))
    print(
        colored("   🎯 Outcome: ", "white") + colored(outcome, outcome_color, attrs=['bold']) +
        colored("   |   Side: ", "white") + colored(side, side_color, attrs=['bold'])
    )
    print(colored(f"   💵 Price  : ${price:.4f}   |   📦 Size: {size:,.2f} shares", "white"))
    if trader and trader != 'unknown':
        short = trader[:8] + "..." + trader[-4:] if len(trader) > 14 else trader
        print(colored(f"   🐳 Trader : {short}", "magenta"))
    print(colored(bar, color))
```
The emoji rotation is a tiny touch that makes the terminal feel alive. WHALE_EMOJIS[stats['whales_printed'] % len(WHALE_EMOJIS)] picks a different emoji for each successive whale, cycling through whale, shark, wave, money bag, gem, rocket, and fire. After a few hours of watching the feed you'll have seen all of them.

## Step 4: Trade Filtering and Whale Detection

process_trade is the heart of the filter. It runs on every single trade that streams through the WebSocket — which can be hundreds per minute on busy days — and it has to be fast. The filter is dead simple: USD notional equals price times size, and if that's below the threshold, return immediately. No formatting, no string concatenation, no color computations. The cost of dropping a non-whale trade is basically free.

When a trade does qualify, we increment the whale counter, check whether it's a new record, and pass it off to print_whale for display. Tracking the biggest whale across the session is a nice touch — it gives you a number to brag about and lets the heartbeat status line keep showing "biggest: $X" even during quiet periods.

One thing to note about the math: price * size works as the USD notional because Polymarket prices are denominated in dollars per share, where each share pays out $1 if the outcome resolves YES. So a fill of 5,000 shares at $0.30 is $1,500 of USD risk, regardless of which outcome got bought. This is different from how you'd calculate notional on a perp exchange.

Trade processing and whale filter

```python
def process_trade(payload):
    """Moon Dev - filter whales and print"""
    stats['trades_seen'] += 1

    price = float(payload.get('price', 0))
    size = float(payload.get('size', 0))
    usd_amount = price * size

    if usd_amount < MIN_WHALE_USD:
        return

    stats['whales_printed'] += 1
    if usd_amount > stats['biggest_whale_usd']:
        stats['biggest_whale_usd'] = usd_amount
        stats['biggest_whale_market'] = payload.get('title', 'Unknown')

    print_whale(payload, usd_amount)
```
Defensive parsing via payload.get('price', 0) matters here — if the schema ever changes or a field is missing, we get a zero instead of a crash. Same logic applies for size. The bot keeps running through schema drift, which is exactly what you want for a long-running scanner.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-whale-scanner)

## Step 5: WebSocket Message Handlers

The WebSocket library uses a callback-based model — you register handlers for events like on_message, on_error, on_close, and on_open, and the library invokes them when the corresponding thing happens. on_message is by far the most important — that's where every incoming message lands.

The handler ignores empty messages, tries to parse the rest as JSON, and bails on parse errors. Polymarket sends a few different message types: a subscribed confirmation when our subscription is accepted, pong responses to our keepalive pings, and the actual trade messages on the activity topic with type orders_matched. Only the last one carries actual trade data; the rest get acknowledged and discarded.

Notice we're looking for the exact combination of topic == 'activity' and type == 'orders_matched'. The activity topic carries other event types too — like order placements and cancellations — and we don't want any of those, just the actual fills.

WebSocket event handlers

```python
def on_message(ws, message):
    if not message or not message.strip():
        return
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return

    if data.get('type') == 'subscribed':
        print(colored("✅ Subscribed to live trades! (Moon Dev is watching the whales 🐋)", "green", attrs=['bold']))
        return
    if data.get('type') == 'pong':
        return

    if data.get('topic') == 'activity' and data.get('type') == 'orders_matched':
        process_trade(data.get('payload', {}))

def on_error(ws, error):
    print(colored(f"⚠️ Moon Dev WS error: {error}", "red"))

def on_close(ws, close_status_code, close_msg):
    print(colored(f"🔌 WebSocket closed: {close_status_code} - {close_msg}", "yellow"))
```
The error and close handlers do basically nothing beyond printing. That's intentional. The actual reconnect logic lives in the main loop — these handlers just provide visibility into what's happening. When the connection drops, you see the close message and then a moment later you see "Reconnecting in 5 seconds" followed by a fresh connection attempt. Keeps responsibilities cleanly separated.

## Step 6: Heartbeat Status Line and Connection Opening

The heartbeat loop is what makes this scanner fun to leave running on a side monitor. Every 10 seconds it prints a one-line status update with a rotating wave spinner, a randomly cycled catchphrase, runtime so far, total trades seen, whales caught, and the biggest one. The phrase and color rotate each tick so the output doesn't look monotonous, and the spinner shifts position to fake a little motion.

This is genuinely important for a streaming bot, not just decoration. When you have a quiet period — say, late at night on the US East Coast when Polymarket activity is light — there might be 30 minutes without a single whale. Without the heartbeat you'd stare at a frozen terminal wondering if the connection died. With it, you see the bot is alive and counting, and you can glance at the stats to verify it's still ingesting trades.

on_open is where the action starts. As soon as the WebSocket connects, we send a JSON subscribe message specifying the activity topic and the orders_matched type. Then we spawn the ping loop — every 30 seconds it sends a JSON ping action to keep the connection alive — and (only on the first connection) we spawn the heartbeat loop. Both are daemon threads, so they die automatically when the main process exits.

Heartbeat loop and connection opening

```python
def heartbeat_loop():
    """Moon Dev - fun status line every HEARTBEAT_INTERVAL seconds so you know it's ALIVE."""
    import random
    tick = 0
    while not shutdown_flag:
        time.sleep(HEARTBEAT_INTERVAL)
        tick += 1
        spinner = SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]
        phrase = HEARTBEAT_PHRASES[tick % len(HEARTBEAT_PHRASES)]
        color = HEARTBEAT_COLORS[tick % len(HEARTBEAT_COLORS)]
        biggest = f"${stats['biggest_whale_usd']:,.0f}" if stats['biggest_whale_usd'] else "$0"
        line = (
            f"{spinner} [{runtime_str()}] Moon Dev - {phrase} "
            f"| seen: {stats['trades_seen']:,} | 🐋 whales: {stats['whales_printed']:,} "
            f"| 🏆 biggest: {biggest}"
        )
        print(colored(line, color, attrs=['bold']))

def on_open(ws):
    print(colored("🔌 Moon Dev WebSocket connected!", "green", attrs=['bold']))
    sub_msg = {
        "action": "subscribe",
        "subscriptions": [{"topic": "activity", "type": "orders_matched"}]
    }
    ws.send(json.dumps(sub_msg))
    print(colored("📡 Subscribing to live trades...", "cyan"))

    def ping_loop():
        while not shutdown_flag:
            time.sleep(PING_INTERVAL)
            try:
                ws.send(json.dumps({"action": "ping"}))
            except Exception:
                break

    threading.Thread(target=ping_loop, daemon=True).start()

    global heartbeat_started
    if not heartbeat_started:
        heartbeat_started = True
        threading.Thread(target=heartbeat_loop, daemon=True).start()
```
The ping loop is critical and easy to forget. WebSocket connections through proxies and load balancers often get killed after 60 seconds of no traffic. Sending an application-level ping every 30 seconds keeps the connection looking active to every layer of infrastructure between you and Polymarket. If the send fails, the loop breaks and we let the outer reconnect logic take over.

## Step 7: Connection Wrapper, Reconnect Loop, and Main

connect_websocket creates a fresh WebSocketApp with all our handlers wired up, then calls run_forever() which blocks until the connection closes. When it does, control returns to the main loop, which checks the shutdown flag and either exits or sleeps 5 seconds and reconnects. This is the simplest possible reconnect pattern — no exponential backoff, no jitter — and for a scanner that's perfectly fine. The Polymarket WebSocket is stable enough that a 5-second retry on rare disconnects works great.

The main block prints a banner, the configured minimum whale size, and a friendly "press Ctrl+C" instruction. Then it enters the reconnect loop. The exception handling is layered: KeyboardInterrupt breaks out immediately (this is the path the signal handler's sys.exit takes), generic exceptions trigger the 5-second reconnect, and clean returns from connect_websocket when shutdown is requested also break out cleanly.

Connect wrapper and main reconnect loop

```python
def connect_websocket():
    global ws_app
    if shutdown_flag:
        return
    print(colored(f"🚀 Moon Dev connecting to {WEBSOCKET_URL}...", "cyan"))
    ws_app = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws_app.run_forever()

# ====================================================================================================
# MOON DEV - Main
# ====================================================================================================
if __name__ == "__main__":
    banner = """
╔══════════════════════════════════════════════════════════════╗
║        🌙  MOON DEV's POLYMARKET WHALE SCANNER  🐋           ║
║        Live stream of every whale trade >= $1,000            ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(colored(banner, "cyan", attrs=['bold']))
    print(colored(f"⚙️  Min whale size: ${MIN_WHALE_USD:,}", "yellow"))
    print(colored(f"🎧 Listening for whales... press Ctrl+C to stop\n", "green", attrs=['bold']))

    while not shutdown_flag:
        try:
            connect_websocket()
            if shutdown_flag:
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            if not shutdown_flag:
                print(colored(f"⚠️ Moon Dev connection error: {e}", "red"))
                print(colored("🔄 Reconnecting in 5 seconds...", "yellow"))
                time.sleep(5)

    print(colored("🌙 Moon Dev's Whale Scanner stopped 🌙", "cyan", attrs=['bold']))
```
The fact that we re-create the WebSocketApp on every reconnect is intentional. The library doesn't play well with reusing the same app object after close — fresh state every time keeps things simple. The heartbeat thread keeps running across reconnects because of that heartbeat_started flag we saw earlier.

## Putting It All Together

When you run this script, here's the choreography: the banner prints, the main loop calls connect_websocket, which opens the connection and triggers on_open. That sends the subscribe message and spawns the ping and heartbeat threads. Polymarket confirms the subscription, the heartbeat starts pulsing every 10 seconds, and trades start streaming through on_message.

Every trade hits process_trade, which increments the counter and either filters out (most trades) or prints a colored whale alert (the big ones). When you Ctrl+C, the signal handler fires, the shutdown flag flips, the WebSocket closes, the final stats summary prints, and the process exits. Clean, predictable, debuggable.

## How to Run the Scanner

Two dependencies, one command. No API keys, no .env file, no signup. This is one of the cleanest little tools to spin up.

Install and run

```python
pip install websocket-client termcolor
python whale_scanner.py
```
Within a few seconds you'll see the connect message, the subscription confirmation, and then the first heartbeat tick. As soon as a $1,000+ trade fills anywhere on Polymarket, your terminal will light up with a colorful whale alert showing every detail of the trade. Leave it running on a side monitor during major events — elections, sports finals, Fed days — and you'll see the order flow in real time as it happens.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-whale-scanner)

## Wrapping Up

This is the kind of tool that's simple on the surface but teaches a ton if you study it. Long-lived WebSocket connections, background heartbeat loops, cooperative shutdown via signal handlers, auto-reconnect with state preservation — these patterns show up in every serious trading bot. The fact that you can wire all of this together in roughly 200 lines of Python and watch live market data flow through it is genuinely fun.

Some ideas for extending it: persist whale trades to a SQLite database for later analysis, post to Discord or Telegram when a $50K+ whale hits, add per-market filtering (only show whales on a specific event), or layer on a basic following strategy — when wallet X buys, mirror the trade in your own account through the Polymarket API. The foundation here is solid; the next step is yours.

Come hang out on the live Zoom calls where we build tools like this together. We'll walk through the code, answer questions, and brainstorm extensions. Algorithmic trading is way more fun with a community around you — and Moon Dev's community is the place to be.

### Want to build this live with us?

We walk through tools like this on our live Zoom calls. Come hang out, ask questions, and build alongside the Moon Dev community.

[Join the Live Zoom Call](https://moondev.com/t/blog/polymarket-whale-scanner)

### Related Resources

[Polymarket Weather Scanner](/polymarket-weather-scanner)

[Polymarket 5-Minute Bot](/polymarket-five-minute-bot)

[HIP3 Funding Rate Scanner](/hip-3-funding-rate-scanner)

[Polymarket Redemption Bot](/polymarket-redemption-bot)

Built with love by Moon Dev
