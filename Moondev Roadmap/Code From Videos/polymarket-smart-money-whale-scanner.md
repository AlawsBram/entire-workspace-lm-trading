<!-- source: https://moondev.com/polymarket-smart-money-whale-scanner -->
<!-- captured: 2026-10-07 -->
<!-- title: Polymarket Smart Money Whale Scanner — Live $2K+ Buys From Profitable Traders Only -->

Polymarket Smart Money Whale Scanner — Live WebSocket Python Bot That Filters $2K+ Buys From Profitable Traders | Moon Dev

Moon Dev Open Source

# Build a Polymarket Smart Money Whale Scanner in Python — Stream Live $2K+ Buys From Profitable Traders Only

The biggest edge in prediction-market trading isn't finding whales. It's finding whales who actually *win*. This Python bot streams Polymarket's live WebSocket trade feed, filters for big BUYs, and cross-references every wallet against a list of historically profitable traders so you only see the moves that matter.

By Moon Dev · May 31, 2026

## Whale Tracking Is Only Half The Edge — Smart Money Is The Other Half

If you watched the basic Polymarket whale scanner, you already know how to stream the firehose of $1,000+ fills off the live WebSocket. That's fun and educational, but if you actually want to *trade* off it, you hit a brutal problem fast: most whales are not smart. Plenty of $25,000 buys come from people who've lost 60% of their bankroll over the last six months. Following them is worse than coin-flipping.

The fix is to combine two data sources. The Polymarket WebSocket at wss://ws-live-data.polymarket.com gives us every fill the instant it lands. And the Moon Dev API endpoint api.moondev.com/api/poly/profitable-traders gives us a constantly-refreshed list of wallets that have been positive over the last seven days — real PnL, real volume, real trade counts. Layer those together and you get the only signal that's actually worth chasing: **a big buy that came from someone who knows what they're doing**.

### Hard-Won Lesson: Don't Poll The REST API

Before settling on the WebSocket, I tried polling data-api.polymarket.com/trades every five seconds. Turns out that endpoint is **heavily cached** — its "newest" trade was consistently 5 to 7 minutes stale and barely moved between polls. The scanner saw nothing new for minutes at a time. The real-time source is the public WebSocket, which pushes around **30 trades per second**. If you're ever building anything live off Polymarket, skip REST entirely and go straight to the socket. Don't make the same mistake I did.

This article walks through the full bot — about 200 lines of Python with three dependencies (websocket-client, requests, termcolor). By the end you'll understand the threading model, the de-dupe trick, the smart-money intersection, and the tiered whale emoji system that makes a 30-trades-per-second firehose actually readable.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-smart-money-whale-scanner)

## Step 1: Docstring, Imports, and the Config Block You'll Actually Touch

The top of the file leads with a heavy docstring. That's deliberate — six months from now when you reopen this file, you'll want to remember *why* it uses a WebSocket instead of polling, and which two data sources it combines. Write that down on day one. The pain you save your future self is real.

The imports are mostly standard library. The three external packages are requests (for the smart-money API), websocket from websocket-client (for the live feed), and termcolor for the colored terminal output. dotenv pulls your MOONDEV_API_KEY out of .env so it never ends up in your shell history or a git commit.

The four config knobs are everything you'll ever want to tune. MIN_BUY_USD sets the floor for what counts as a whale. SMART_REFRESH_MIN controls how often we re-pull the profitable-traders list (30 minutes is plenty — the list doesn't turn over that fast). SMART_ONLY is the most important toggle in the file: when true, you only see whales who are *also* profitable traders. That's the killer setup. And HEARTBEAT_SECONDS controls how often a quiet-stretch status line prints so you know the bot is still alive when nothing's happening.

Docstring, imports, and configuration

```python
#!/usr/bin/env python3
"""
================================================================================
  🐳 MOON DEV's POLYMARKET WHALE SCANNER 🐳
================================================================================
Streams Polymarket's LIVE trade websocket and prints every big BUY the instant
it happens — who the whale is and what market they're piling into.

WHY WEBSOCKET (not a polling loop):
  We first tried polling data-api.polymarket.com/trades every 5s. That endpoint
  is HEAVILY CACHED — its "newest" trade was 5-7 minutes stale and never moved,
  so the scanner saw nothing new. The real-time source is the websocket
  (wss://ws-live-data.polymarket.com), which pushes ~30 trades/sec live. That's
  the same feed your no_market_scanner.py / nostradamus_oracle.py already use.

DATA SOURCES (both real, no fake data):
  1. Polymarket live websocket (activity / orders_matched)
       -> every fill, live. USD = size * price. We keep BUYs >= MIN_BUY_USD.
       -> payload includes proxyWallet, title, outcome, price, size, etc.
  2. Moon Dev API (api.moondev.com/api/poly/profitable-traders, MOONDEV_API_KEY)
       -> full list of profitable Polymarket traders. We TAG a whale 🧠 when the
          buyer is a known profitable trader and show their 7-day P&L. The edge:
          not just a big buyer, but a big buyer who actually WINS.

Built by Moon Dev 🌙
================================================================================
"""

import os
import sys
import json
import time
import threading
import requests
import websocket
from datetime import datetime
from dotenv import load_dotenv
from termcolor import colored

# ============================================================================
# 🔧 MOON DEV - CONFIGURATION (tweak these)
# ============================================================================

MIN_BUY_USD = 2000.0      # 🐳 Only show BUYs this size or bigger
SMART_REFRESH_MIN = 30    # Re-pull the profitable-traders list every N minutes
SMART_ONLY = True         # 🧠 Show ONLY known profitable-trader whales
HEARTBEAT_SECONDS = 15    # Print an "alive" line every N seconds on quiet stretches
```
A note on SMART_ONLY=True as the default: when you first run this you might want to flip it to False just to feel the firehose, see the raw $2K+ flow, get a sense of volume. Then flip it back to true and watch the signal-to-noise jump dramatically. You'll suddenly only see ten or twenty alerts per day instead of hundreds, but every single one is worth looking at.

## Step 2: Startup Banner, Env Loading, and Graceful API-Key Fallback

Right after configuration, the bot prints its banner and loads the .env file from whatever directory the script lives in. Using os.path.dirname(os.path.abspath(__file__)) means you can run this script from anywhere — your home directory, a cron job, a systemd service — and it'll still find its own .env. Trust me, you'll thank yourself for this when you deploy.

Notice the graceful fallback when no MOONDEV_API_KEY is set. The bot doesn't crash and it doesn't refuse to run — it just disables smart-money tagging and prints a yellow warning. This pattern of *degrade gracefully when an optional thing is missing* is one of those small touches that makes a tool feel polished. The user gets a clear signal about what's working and what isn't, and the core whale-streaming still functions.

The banner also prints just the last three characters of your API key — enough for you to confirm the right key loaded, not enough to leak anything if you accidentally screen-share. Tiny, but the kind of detail that matters.

Startup banner and env loading

```python
# ============================================================================
# 🚀 STARTUP - Moon Dev
# ============================================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

MOONDEV_API_KEY = os.getenv("MOONDEV_API_KEY")

WEBSOCKET_URL = "wss://ws-live-data.polymarket.com"
MOONDEV_PROFITABLE_URL = "https://api.moondev.com/api/poly/profitable-traders"

print(colored("🐳🐳🐳  MOON DEV's POLYMARKET WHALE SCANNER  🐳🐳🐳", "cyan", attrs=["bold"]))
print(colored(f"  Min Buy Size: ${MIN_BUY_USD:,.0f} | Live websocket feed | Smart-only: {SMART_ONLY}", "white"))
if MOONDEV_API_KEY:
    print(colored(f"  Moon Dev API key: ...{MOONDEV_API_KEY[-3:]} ✅ (smart-money tagging ON)", "green"))
else:
    print(colored("  ⚠️ No MOONDEV_API_KEY in .env — whales still show, just no 🧠 smart-money tags", "yellow"))
```
You'll need a .env file next to the script with one line — MOONDEV_API_KEY=your_key_here. Get a key from the Moon Dev community if you don't have one. Without it the scanner still streams whales just fine, you just won't get the smart-money brain emojis.

## Step 3: Loading the Profitable Traders List From the Moon Dev API

This is where the second data source comes in. The Moon Dev API tracks every wallet on Polymarket and computes rolling 7-day PnL, volume, and trade count. Wallets that are consistently positive land on the profitable-traders endpoint. We pull that list once at startup, index it by lowercase wallet address into the module-level _smart_money dict, and refresh every 30 minutes from a background thread.

The safe_get wrapper is a tiny but important utility. Network calls fail — DNS hiccups, the API rebooting, a 502 from Cloudflare. If any of those took down our scanner we'd miss real whales. So we catch every exception, print a yellow warning with the error type and a 70-character preview of the message, and return None. Callers check for None and just keep the old list. Resilience by default.

maybe_refresh_smart_money is the lazy reload trigger. It's called from the heartbeat loop (which we'll see in step 6), and only actually re-pulls if more than 30 minutes have passed. No timers, no schedulers — just a timestamp check. Simple and bulletproof.

Smart-money list loader

```python
# ============================================================================
# 🧠 SMART MONEY - Moon Dev API profitable-traders list
# ============================================================================

_smart_money = {}            # wallet(lower) -> trader info
_smart_money_loaded_at = 0

def safe_get(url, params=None, headers=None, timeout=20):
    try:
        return requests.get(url, params=params, headers=headers, timeout=timeout)
    except Exception as e:
        print(colored(f"  ⚠️ Moon Dev - request error: {type(e).__name__}: {str(e)[:70]}", "yellow"))
        return None

def load_smart_money():
    """Moon Dev - Pull the full profitable-traders list and index it by wallet."""
    global _smart_money, _smart_money_loaded_at
    if not MOONDEV_API_KEY:
        return
    resp = safe_get(MOONDEV_PROFITABLE_URL, headers={"X-API-Key": MOONDEV_API_KEY})
    if not resp or resp.status_code != 200:
        code = resp.status_code if resp else "no resp"
        print(colored(f"  ⚠️ Moon Dev - profitable-traders returned {code}, keeping old list ({len(_smart_money)})", "yellow"))
        return
    data = resp.json()
    traders = data.get("traders", [])
    _smart_money = {t["wallet"].lower(): t for t in traders if t.get("wallet")}
    _smart_money_loaded_at = time.time()
    full = data.get("full_list", False)
    print(colored(f"  🧠 Moon Dev loaded {len(_smart_money):,} profitable traders {'(FULL list)' if full else '(top 25)'}", "magenta"))

def maybe_refresh_smart_money():
    if MOONDEV_API_KEY and time.time() - _smart_money_loaded_at > SMART_REFRESH_MIN * 60:
        load_smart_money()
```
Indexing by .lower() matters. Ethereum addresses are case-insensitive but EIP-55 checksummed addresses come in mixed case. The WebSocket gives us one format, the API might give us another, and a substring lookup would silently miss matches. Normalize on the way in, normalize on the way out, and you never debug a phantom "why isn't this wallet matching" bug at 2am.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-smart-money-whale-scanner)

## Step 4: Tiered Whale Emojis and the Pretty Printout

When you're watching 30 trades per second scroll past, your eyes need help. That's what the tiered emoji system is for. A $2K buy gets a small dolphin 🐬. $10K bumps you to a whale 🐳. $25K is the big blue whale 🐋. And anything over $100K gets the whale-on-fire 🐋🔥. You can scan a wall of output and instantly spot the monsters without reading numbers.

The _stats dict and _seen set are shared mutable state across all threads — the websocket thread writes to them, the heartbeat thread reads from them. The _lock protects both. We'll use it sparingly (short critical sections only) to avoid stalling the message handler.

buyer_label formats whoever bought into a clean string. Most Polymarket traders have a pseudonym, but some don't — in that case we fall back to a truncated wallet (0x1234...abcd style). And print_whale is where everything comes together — the whale emoji, the USD size and price, the market title and outcome side, the buyer label, and (the headline feature) the magenta 🧠 SMART MONEY line that appears only when the buyer is on the profitable-traders list, showing their 7-day PnL, volume, and trade count.

Whale printout with tiered emojis and smart-money tag

```python
# ============================================================================
# 🐳 WHALE PRINTOUT - Moon Dev
# ============================================================================

# session stats (shared across threads)
_stats = {"trades": 0, "whales": 0, "smart": 0, "last_print": 0}
_seen = set()
_lock = threading.Lock()

def buyer_label(t):
    name = (t.get("pseudonym") or t.get("name") or "").strip()
    wallet = t.get("proxyWallet", "")
    short = f"{wallet[:6]}...{wallet[-4:]}" if wallet else "unknown"
    return f"{name} ({short})" if name else short

def print_whale(t, usd):
    wallet = t.get("proxyWallet", "")
    title = t.get("title", "Unknown market")
    outcome = t.get("outcome", "?")
    price = float(t.get("price", 0))
    shares = float(t.get("size", 0))
    event_slug = t.get("eventSlug") or t.get("slug", "")
    ts = datetime.now().strftime("%H:%M:%S")

    smart = _smart_money.get(wallet.lower())

    if usd >= 100_000:   whale = "🐋🔥"
    elif usd >= 25_000:  whale = "🐋"
    elif usd >= 10_000:  whale = "🐳"
    else:                whale = "🐬"

    print(colored("  " + "─" * 76, "blue"))
    print(colored(f"  {whale}  ${usd:,.0f} BUY  @ ${price:.3f}  ({shares:,.0f} shares)   {ts}", "green", attrs=["bold"]))
    print(colored(f"     Market : {title}", "white"))
    print(colored(f"     Betting: {outcome.upper()}", "cyan"))
    print(colored(f"     Buyer  : {buyer_label(t)}", "white"))
    if smart:
        print(colored(f"     🧠 SMART MONEY — 7d P&L ${smart.get('pnl_7d',0):,.0f} | "
                      f"7d Vol ${smart.get('volume_7d',0):,.0f} | {smart.get('trades_7d',0)} trades",
                      "magenta", attrs=["bold"]))
    print(colored(f"     👤 https://polymarket.com/{wallet}", "blue"))
    if event_slug:
        print(colored(f"     🔗 https://polymarket.com/event/{event_slug}", "blue"))
```
The two clickable URLs at the bottom — to the wallet's Polymarket profile and to the event page — are gold. When something hot prints, you cmd-click and you're looking at the whale's entire trade history or the market they just piled into within two seconds. That's the difference between a useful tool and a noisy one.

## Step 5: WebSocket Message Handling, De-dupe, and the Smart-Only Filter

handle_trade is the brain. Every fill hits it. First it bails on anything that isn't a BUY (sells aren't the signal we care about — we want to see who's entering positions). Then it computes the USD notional as size * price and discards anything below MIN_BUY_USD.

Then the de-dupe trick. Polymarket sometimes replays the same fill on the WebSocket, especially during reconnects. We key on transactionHash:asset (the hash alone isn't unique because a single tx can fill across multiple outcome tokens) and stuff it into a set. If we've seen it, skip. When the set grows past 8,000 entries we just clear the whole thing — old fills from a session ago aren't going to re-broadcast, and unbounded memory growth is for amateurs.

The SMART_ONLY filter lives here too. After de-dupe, we check whether the wallet is in _smart_money, and if SMART_ONLY is true and they're not smart, we drop the trade. That single boolean is the difference between a wall of $2K buys and a hand-curated signal feed.

on_message parses incoming JSON, ignores anything that isn't the right topic+type (subscribed confirmations, pongs, and other noise the websocket sends), and routes real fills to handle_trade. The on_open handler sends the subscribe message and spawns a daemon thread that pings every 30 seconds to keep the connection alive through proxies and load balancers that love to kill idle sockets.

WebSocket handlers, de-dupe, and ping loop

```python
# ============================================================================
# 🔌 WEBSOCKET HANDLERS - Moon Dev
# ============================================================================

def handle_trade(payload):
    """Moon Dev - One live fill. Keep BUYs >= MIN_BUY_USD, tag, print."""
    if payload.get("side", "").upper() != "BUY":
        return

    usd = float(payload.get("size", 0) or 0) * float(payload.get("price", 0) or 0)
    if usd < MIN_BUY_USD:
        return

    key = f"{payload.get('transactionHash','')}:{payload.get('asset','')}"
    with _lock:
        if key in _seen:
            return
        _seen.add(key)
        if len(_seen) > 8000:
            _seen.clear()

    is_smart = bool(_smart_money.get(payload.get("proxyWallet", "").lower()))
    if SMART_ONLY and not is_smart:
        return

    with _lock:
        _stats["whales"] += 1
        if is_smart:
            _stats["smart"] += 1

    print_whale(payload, usd)

def on_message(ws, message):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return
    if data.get("type") == "subscribed":
        print(colored("  ✅ Moon Dev - subscribed to the live trade feed!\n", "green"))
        return
    if data.get("type") == "pong":
        return
    if data.get("topic") == "activity" and data.get("type") == "orders_matched":
        with _lock:
            _stats["trades"] += 1
        handle_trade(data.get("payload", {}))

def on_error(ws, error):
    print(colored(f"  ⚠️ Moon Dev - websocket error: {str(error)[:70]}", "yellow"))

def on_close(ws, code, msg):
    print(colored(f"  🔌 Moon Dev - websocket closed ({code}). Reconnecting...", "yellow"))

def on_open(ws):
    print(colored("  🔌 Moon Dev - websocket connected, subscribing...", "cyan"))
    ws.send(json.dumps({
        "action": "subscribe",
        "subscriptions": [{"topic": "activity", "type": "orders_matched"}],
    }))

    def ping():
        while True:
            time.sleep(30)
            try:
                ws.send(json.dumps({"action": "ping"}))
            except Exception:
                break
    threading.Thread(target=ping, daemon=True).start()
```
The ping thread is defined inside on_open as a closure so it captures the ws object directly. When the socket drops and we reconnect, a fresh on_open spawns a fresh ping thread for the new connection. The old one breaks out of its loop the next time the dead socket's send fails. Clean self-cleanup.

## Step 6: The Heartbeat Loop — Proof Of Life On Quiet Stretches

When SMART_ONLY=True there can be ten or fifteen minutes between alerts. That's great for signal quality, but it's anxiety-inducing if you're staring at a silent terminal wondering if the bot died, or your wifi dropped, or Polymarket went down. The heartbeat fixes that.

Every HEARTBEAT_SECONDS (default 15), the heartbeat thread prints a compact one-liner showing current time, total trades seen across the whole firehose, total whales matching our filter, and how many of those were smart. It also calls maybe_refresh_smart_money so the profitable-traders list refreshes itself without us needing a separate scheduler thread.

This is the heartbeat thread doing three jobs in one: proving liveness, surfacing session-level stats, and triggering the smart-money refresh. One sleeping loop, three responsibilities. Clean.

Heartbeat loop

```python
# ============================================================================
# ❤️ HEARTBEAT - Moon Dev (proves it's alive on quiet stretches)
# ============================================================================

def heartbeat_loop():
    while True:
        time.sleep(HEARTBEAT_SECONDS)
        maybe_refresh_smart_money()
        ts = datetime.now().strftime("%H:%M:%S")
        with _lock:
            s = dict(_stats)
        print(colored(
            f"  ⏱️ [{ts}] live: {s['trades']:,} trades seen · "
            f"{s['whales']} whales ≥ ${MIN_BUY_USD:,.0f} ({s['smart']} 🧠)",
            "white"))
```
The with _lock: s = dict(_stats) snapshot is a small but meaningful detail. We hold the lock just long enough to copy the dict, then release it before doing the print (which can be slow on some terminals). The websocket thread keeps incrementing stats while we format the line. Always minimize the work you do inside a lock.

## Step 7: The Main Loop — Boot, Reconnect Forever, Exit Cleanly

main is short and that's the point. It does the initial smart-money load synchronously (so the first messages already have tagging available), spawns the heartbeat as a daemon thread, then enters an infinite reconnect loop. Each iteration creates a fresh WebSocketApp, calls run_forever() which blocks until the connection dies, sleeps 5 seconds, then loops back and reconnects.

No exponential backoff, no fancy jitter. The Polymarket WebSocket is stable enough that a flat 5-second retry works fine, and if it's really down the heartbeat will keep printing zeros while we retry. Simple beats clever.

The KeyboardInterrupt handler at the bottom is the polish move. When you Ctrl+C, you don't want a Python traceback — you want a clean send-off with stats. So we catch the interrupt, snapshot the session stats one last time, and print a cyan goodbye showing how many whales (and how many smart-money whales) you saw this session. "The whales swim on" is the kind of closing line that makes the tool feel alive.

Main loop and graceful shutdown

```python
# ============================================================================
# 🚀 MAIN - Moon Dev
# ============================================================================

def main():
    print(colored("\n🐳🌙 Moon Dev's Whale Scanner starting up!", "cyan", attrs=["bold"]))
    print(colored("   Press Ctrl+C to exit\n", "white"))

    load_smart_money()
    threading.Thread(target=heartbeat_loop, daemon=True).start()

    while True:
        ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever()
        # If we get here the socket dropped — wait and reconnect
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        with _lock:
            s = dict(_stats)
        print(colored(f"\n\n🌙 Moon Dev's Whale Scanner stopped. "
                      f"Saw {s['whales']} whales ({s['smart']} 🧠) this session. The whales swim on. 🐳",
                      "cyan", attrs=["bold"]))
```
Marking the heartbeat thread as a daemon is what makes Ctrl+C work clean. Daemon threads die when the main thread dies — no explicit shutdown signaling needed. Same for the ping closure inside on_open. The whole process collapses gracefully on the interrupt.

## Putting It All Together

Run it and here's the choreography. Banner prints. load_smart_money pulls the profitable-trader list from the Moon Dev API — say, 200 wallets — and indexes them by lowercase address. The heartbeat thread spawns and starts ticking every 15 seconds. The main thread enters its reconnect loop, opens the WebSocket, and on_open fires, sending the subscribe message and spawning a ping thread.

Polymarket starts firing trades at us. on_message filters out the noise and routes orders_matched events to handle_trade. Most get dropped — wrong side, too small, duplicate, or wallet not on the smart-money list. The ones that survive get pretty-printed with the tiered whale emoji, market title, outcome, buyer label, smart-money tag, and clickable links.

Every 15 seconds the heartbeat prints a status line and silently re-fetches the smart-money list if 30+ minutes have passed. Every 30 seconds the ping thread sends a keepalive frame. If anything dies — socket drops, server reboots, your wifi flickers — the main loop catches it, sleeps 5 seconds, and reconnects. You leave this running on a side monitor and forget about it.

## How To Run It

Three dependencies, a one-line .env file, and you're live. The smart-money tagging is the optional bit — without the API key the bot still works, you just don't get the 🧠 enrichment.

Install and run

```python
pip install websocket-client requests python-dotenv termcolor

# create .env next to the script
echo "MOONDEV_API_KEY=your_key_here" > .env

# run it
python whale_scanner.py
```
First boot the banner prints, the smart-money list loads (you'll see the magenta "loaded N profitable traders" line), the WebSocket connects, and within seconds you should see the green "subscribed to the live trade feed" confirmation. Then heartbeats every 15 seconds and whale alerts whenever a smart-money buy lands. Run it during a big event — an election night, a Fed announcement, a major sports final — and you'll see institutional-grade signal in your terminal for the cost of three pip installs.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-smart-money-whale-scanner)

## Wrapping Up

The whole bot is about 200 lines of Python, but the ideas inside it generalize way past Polymarket. The two-source intersection pattern (live event feed + reference list of who-to-care-about) is the same shape as crypto whale watchers that filter Etherscan flows by funded-by-Binance, sports betting bots that filter line moves by sharp-book consensus, and equities order-flow tools that filter dark-pool prints by 13F-tracked institutions. The data sources change. The pattern doesn't.

Some extensions to try: persist every smart-money whale to a SQLite database so you can backtest a copy-trading strategy on the next week's data, post the alerts to Discord or Telegram with a webhook, layer on per-market or per-outcome filters, or build a simple follower bot that automatically places a small bet in the same direction whenever a top-10 smart wallet enters a position over $5K. The foundation is here. The edge is yours to build.

Come hang out on the live Zoom calls where we build tools like this together. Real Q&A, real code, real strategies — and a community of algorithmic traders and quant builders who get excited about the same weird-looking edges you do. Building this stuff is way more fun with people who care.

### Want to build this live with us?

We walk through tools like this on the live Zoom calls. Come hang out, ask questions, and build alongside the Moon Dev community.

[Join the Live Zoom Call](https://moondev.com/t/blog/polymarket-smart-money-whale-scanner)

### Related Resources

[Polymarket Whale Scanner ($1K+ Stream)](/polymarket-whale-scanner)

[Polymarket Weather Scanner](/polymarket-weather-scanner)

[Polymarket 5-Minute Bot](/polymarket-five-minute-bot)

[Polymarket Redemption Bot](/polymarket-redemption-bot)

Built with love by Moon Dev
