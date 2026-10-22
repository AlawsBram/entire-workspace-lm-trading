<!-- source: https://moondev.com/polymarket-strike-cross-sniper -->
<!-- captured: 2026-10-07 -->
<!-- title: Strike-Cross Sniper — Polymarket Mid-Price Lag Taker Bot -->

Strike-Cross Sniper: Polymarket Mid-Price Lag Taker Bot | Algorithmic Trading | Moon Dev

Moon Dev Open Source

# Strike-Cross Sniper: A Polymarket Mid-Price Lag Taker Bot

A Python trading bot that buys the *leading* side of Polymarket 5-minute crypto UP/DOWN markets after Hyperliquid spot has already moved through the strike — while the CLOB is still quoting that side at 30-70¢. PnL forensics on 1,533 live trades found **49/49 wins** in the filtered subset.

By Moon Dev · July 17, 2026

## The Edge: The Orderbook Lags the Spot

Every Polymarket crypto UP/DOWN market has a **strike** — a "price to beat." If BTC is above that strike when the 5-minute window closes, the UP side pays $1.00 and DOWN pays $0.00. It's a binary. Simple. The interesting part is *when the market has effectively already been decided but the orderbook hasn't caught up yet.*

Moon Dev ran PnL forensics across data/lag_arb_trades*.csv — 1,533 resolved live trades — and found something delicious. When spot (measured off Hyperliquid's mark price) has already moved **≥ 0.10%** through the strike, the leading side is essentially a lock to resolve at $1.00. But the CLOB frequently keeps quoting that leading side at just **30-70¢**. Buy it as a taker, and you're paying ~50¢ for something worth ~$1.00 — a ~2x payout on a historical near-lock.

The evidence is what made this bot worth building. In the filtered subset (5-minute windows, entry price 30-70¢, ITM ≥ 0.10%): **49 wins, 0 losses, +105% ROI** ($123 turned into +$128.61). And the threshold behavior was beautifully monotonic — at ITM 0 to 0.05% the win rate is a coin-flippy 50%, but at ITM ≥ 0.10% it jumps to 100%. The move through the strike is the whole signal.

**Why the old bots died:** The previous generation of Moon Dev bots chased 80¢+ entries — "scrape the last few cents." That zone made just +1.0% ROI on $1,344. It's dead. The spread is gone, the fees eat you. This bot ignores it entirely and hunts the bigger swing: the 30-70¢ leading side that spot has already left behind.

One honest caveat before we go further: this is a backtested edge, and past performance on a filtered subset is not a promise. 49/49 is a small sample. That's exactly why the bot is built to log every single window — so you can watch the edge hold up (or decay) in real time on your own account. Let's build it.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-strike-cross-sniper)

## Step 1: The Header and the Zero-Dependency Philosophy

Every Moon Dev bot opens with a fat docstring that *is* the strategy. If you read nothing else, the header tells you the assets, the entry gates, the evidence behind them, and whether you're about to fire live money. Notice the last section: this bot is a **single-file, zero-dependency build**. Everything is inlined — its own .env parser, its own ANSI color function. The only thing you pip install is py_clob_client_v2, the SDK that signs real Polymarket orders (and it drags requests and web3 along with it).

Why go zero-dependency? Because a bot that touches real money should be auditable in one sitting and should never break because python-dotenv or termcolor shipped a breaking change. Fewer moving parts, fewer surprises. You can drop this file on a fresh VPS, install one package, and it runs.

The docstring — the whole strategy in one place

```python
"""
================================================================================
MOON DEV's STRIKE-CROSS SNIPER v1.0  (mid-price lag taker — july_17th fleet #1)
================================================================================
Born from PnL forensics across data/lag_arb_trades*.csv (1,533 resolved live
trades). The finding: the CLOB keeps quoting the LEADING side of the 5-min
updown markets at ~30-70c even after spot has already moved >= 0.10% through
the strike. Buy the leading side as a TAKER -> ~2x payout on a historical
near-lock.

THE EVIDENCE (why Moon Dev built this):
  - Filtered subset (5-min windows, entry 30-70c, ITM >= 0.10%): 49/49 wins,
    +105% ROI ($123 -> +$128.61)
  - Monotonic threshold: ITM 0-0.05% -> 50% win; ITM >= 0.10% -> 100%
  - The 80c+ entries the old bots took made just +1.0% ROI on $1,344 — the
    "scrape the last few cents" zone is DEAD. We hunt the bigger swing.

THE TRADE:
  - Assets: BTC, SOL, XRP, ETH {asset}-updown-5m-{T} markets (T = unix//300*300)
  - Strike = the market's OWN price-to-beat (Polymarket crypto-price endpoint,
    the same number the site UI shows — NOT our first-tick spot guess)
  - Spot = Hyperliquid mark price (all 4 assets in one metaAndAssetCtxs call)
  - ENTER when ALL: itm_pct >= 0.10% through the strike, 45s-270s left,
    leading-side ask 0.30-0.70, ask depth >= our size. Taker (GTC crossable).
  - One entry per window per asset, no re-entry. Hold to resolution.

PAPER_MODE = False — LIVE FIRE on the AUG14 account. Flip to True to paper.

SINGLE-FILE, NO-DEPENDENCY BUILD: everything is inlined (own .env parser,
own ANSI colors). The ONLY pip install needed is py_clob_client_v2.

Account: AUG14 (signature_type 2, CLOB V2 SDK — V1 post_order is DEAD).
Built by Moon Dev
================================================================================
"""
```
Read the PAPER_MODE = False line twice. This file ships aimed at the live AUG14 account. Before you run anything, you'll flip that to True and watch it paper-trade for a few hours.

## Step 2: Rolling Your Own .env Parser and ANSI Colors

Here's the "zero dependency" promise in code. Instead of python-dotenv, we have a 10-line load_env that reads a file, skips comments and blank lines, splits on the first =, and strips quotes. The os.environ.setdefault is deliberate — it won't clobber a variable that's already set in the real environment, so an existing export always wins over the file.

Instead of termcolor, we have a tiny colored() that emits raw ANSI escape codes. Same API you're used to (colored(text, "green", attrs=["bold"])), zero import.

And find_env() is a nice touch: it walks up the directory tree from the script looking for a .env, falling back to your home directory. That means you can run the bot from any subfolder and it'll still find the repo-root .env where Moon Dev keeps all the account keys.

Inlined ANSI colors + .env parser + upward .env search

```python
ANSI = {"red": "31", "green": "32", "yellow": "33", "magenta": "35", "cyan": "36", "white": "37"}

def colored(text, color=None, attrs=None):
    codes = (["1"] if attrs and "bold" in attrs else []) + ([ANSI[color]] if color in ANSI else [])
    return f"\033[{';'.join(codes)}m{text}\033[0m" if codes else str(text)

def load_env(path):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def find_env():
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        candidate = os.path.join(d, '.env')
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.join(os.path.expanduser('~'), '.env')

ENV_PATH = find_env()
load_env(ENV_PATH)
```
These 30 lines replace two pip packages. Nothing magic — but it means the only external code signing your orders is the one SDK you actually need to audit.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-strike-cross-sniper)

## Step 3: Account Selection and the Strategy Knobs

Moon Dev runs several Polymarket wallets in parallel. To point a bot at a different one you change exactly one variable — ACCOUNT_SUFFIX — and every env-var name is rebuilt from it with f-strings. The critical gotcha lives on the last line of that block: the OG account uses signature_type=1 (browser wallet), but every Gnosis Safe sub-account like AUG14 uses signature_type=2. Get this wrong and every signed order is rejected.

Then come the strategy knobs — and these *are* the edge, straight out of the forensics. MIN_ITM_PCT = 0.10 is the 0.10%-through-the-strike threshold where the win rate snapped to 100%. PRICE_BAND = (0.30, 0.70) is the "leading side is still cheap" zone — below 0.30 the depth is usually junk, above 0.70 you're back in the dead "scrape the cents" territory. TIME_BAND = (45, 270) keeps us out of the very start of the window (strike hasn't settled) and the very end (fill risk into resolution).

DAILY_STOP_LOSS = -100 is your circuit breaker — if realized PnL for the day drops to −$100, the bot stops opening new positions. Even a 49/49 backtest deserves a hard floor when it's live. And MIN_SHARES = 5 is the Polymarket per-order minimum you can't go under.

Account config + strategy parameters

```python
ACCOUNT_SUFFIX = "_AUG14"
PRIVATE_KEY_ENV_NAME = f"PRIVATE_KEY{ACCOUNT_SUFFIX}"
PUBLIC_KEY_ENV_NAME = f"PUBLIC_KEY{ACCOUNT_SUFFIX}"
API_KEY_ENV_NAME = f"API_KEY{ACCOUNT_SUFFIX}"
PASSPHRASE_ENV_NAME = f"PASSPHRASE{ACCOUNT_SUFFIX}"
SIGNATURE_TYPE = 1 if ACCOUNT_SUFFIX == "" else 2

MIN_ITM_PCT = 0.10          # spot must be >= 0.10% through the strike (the edge)
PRICE_BAND = (0.30, 0.70)   # leading-side ask must sit in this band
TIME_BAND = (45, 270)       # only enter with 45-270 seconds left in the window
USD_SIZE = 5                # size per entry, in USD
MAX_CONCURRENT = 4          # one per asset, four assets => cap at 4
DAILY_STOP_LOSS = -100      # halt new entries if the day's PnL hits -$100
PAPER_MODE = False          # LIVE. flip to True to paper-trade first.

ASSETS = ['BTC', 'SOL', 'XRP', 'ETH']
MIN_SHARES = 5              # Polymarket per-order minimum
MARKET_DURATION = 300       # 5-minute markets => unix // 300 * 300
CHECK_INTERVAL = 2          # main loop cadence, seconds
ET = timezone(timedelta(hours=-4))

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "strike_cross_log.csv")
LOG_FIELDS = ["timestamp", "asset", "slug", "strike", "spot", "itm_pct", "side",
              "ask", "size", "action", "outcome", "won", "pnl_usd", "paper"]
```
Notice there's no post_only anywhere here — unlike Moon Dev's maker bots, this one is a **taker**. We *want* to cross the book and grab that mispriced leading side right now, not sit on the bid hoping. More on why that matters in Step 6.

## Step 4: Getting the Strike and the Spot (Two Different Sources)

This is the most important data detail in the whole bot, and it's subtle. The **strike** and the **spot** come from two different places, on purpose.

The strike is the market's *own* price-to-beat — the exact number the Polymarket UI shows you. We fetch it from Polymarket's crypto-price endpoint, **not** by snapshotting spot at the first tick of the window. This matters because an early guess drifts; the market's official strike is the number resolution will actually be judged against. Comparing spot to anything else is comparing against the wrong line.

The spot comes from **Hyperliquid's mark price**, and here's the efficiency trick: a single metaAndAssetCtxs call returns the mark price for *all four assets at once*. One request per loop, not four. The bot builds a {asset: mark} dict and every asset's ITM check reads from it.

get_strike + get_hl_marks — the two-source data layer

```python
def get_market_tokens(asset, market_ts):
    """Resolve the {asset}-updown-5m-{ts} market -> slug + UP/DOWN token ids."""
    slug = f"{asset.lower()}-updown-5m-{market_ts}"
    r = requests.get(
        "https://gamma-api.polymarket.com/markets",
        params={"slug": slug, "closed": "false", "active": "true"},
        timeout=10,
    )
    if r.status_code != 200 or not r.json():
        return None
    m = r.json()[0]
    tokens = json.loads(m["clobTokenIds"])
    return {"slug": slug, "market_id": m["id"],
            "up_token": tokens[0], "down_token": tokens[1],
            "neg_risk": m.get("negRisk", False)}

def get_strike(asset, market_ts):
    """The market's OWN price-to-beat, from Polymarket's crypto-price endpoint.
    This is the SAME number the site UI shows — NOT our first-tick spot guess."""
    r = requests.get(
        "https://gamma-api.polymarket.com/crypto-price",
        params={"symbol": asset, "timestamp": market_ts},
        timeout=10,
    )
    if r.status_code != 200:
        return None
    return float(r.json().get("price"))

def get_hl_marks():
    """All four mark prices in ONE Hyperliquid metaAndAssetCtxs call."""
    r = requests.post("https://api.hyperliquid.xyz/info",
                      json={"type": "metaAndAssetCtxs"}, timeout=10)
    if r.status_code != 200:
        return {}
    meta, ctxs = r.json()
    names = [a["name"] for a in meta["universe"]]
    marks = {}
    for name, ctx in zip(names, ctxs):
        if name in ASSETS:
            marks[name] = float(ctx["markPx"])
    return marks
```
If either source is missing for an asset this tick, the bot simply skips that asset and logs NO_SIGNAL — no strike or no spot means no comparison, so there's nothing to trade. Missing data is a skip, never a guess.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-strike-cross-sniper)

## Step 5: Reading the Leading Side's Ask and Depth

Once the bot knows which side is leading (spot is above the strike ⟶ UP leads; below ⟶ DOWN leads), it needs the price and depth of that side's ask — because we're a taker, we pay the ask. get_book_ask pulls the CLOB book for a token and returns the best ask *and* the size available there.

The depth check is what separates a real fill from a fantasy. Polymarket returns bids and asks sorted worst-to-best, so asks[-1] is the lowest (best) ask — the one we'd actually take. But if only 2 shares are resting there and we want 10, we'd walk up the book and pay a worse average price than the number our gate approved. So the entry gate requires ask_size >= our size. No depth, no trade.

get_book_ask — price and depth at the best ask

```python
def get_book_ask(token_id):
    """Best ask price + the size resting there (for the depth check).
    Polymarket sorts asks worst->best, so asks[-1] is the lowest = best ask."""
    r = requests.get("https://clob.polymarket.com/book",
                     params={"token_id": token_id}, timeout=10)
    if r.status_code != 200:
        return None, 0.0
    asks = r.json().get("asks", [])
    if not asks:
        return None, 0.0
    best = asks[-1]
    return float(best["price"]), float(best["size"])
```
Two independent gates ride on this one function: the price band (0.30 ≤ ask ≤ 0.70) and the depth check (size ≥ shares). If the ask is above 0.70 we log ASK_TOO_HIGH; below 0.30, ASK_TOO_LOW. Every rejection is a labeled row in the CSV.

## Step 6: hunt() — The Entry Gate and Why We Use GTC (Not FAK/FOK)

hunt() runs once per asset per tick and is the heart of the bot. It computes itm_pct — how far, in percent, spot has moved through the strike — picks the leading side, then walks every gate in order. Only if *all* gates pass does it fire a taker order. Every branch that doesn't fire writes a labeled skip to the CSV, so you can later ask "how many windows did I miss for ASK_TOO_HIGH vs TOO_LATE?"

Here's the counterintuitive part: the order type is **GTC** (good-til-cancelled), not FAK (fill-and-kill) or FOK (fill-or-kill). We're a taker — we want an immediate fill — so why GTC? Because on Polymarket's CLOB V2, a GTC limit order priced *at or above the best ask* crosses the book and fills immediately as a taker, just like a market order would. But unlike FOK, it doesn't nuke the whole order if the top level is a hair thin, and unlike FAK it's the order type the V2 SDK handles most reliably for this flow. We price it aggressively (at the ask), the depth check guarantees the size is there, and the fill happens on the spot. GTC gives us taker behavior with the most forgiving fill semantics.

The one entry per window per asset rule is enforced by an entered set keyed on (asset, market_ts). Once we've fired for BTC's current window, we never re-enter it — we hold that position straight through to resolution. No averaging in, no second bullet.

hunt() — compute ITM, walk the gates, fire a GTC taker

```python
def hunt(asset, market_ts, marks, tracker):
    key = (asset, market_ts)
    if key in tracker.entered:
        return  # one entry per window per asset

    time_left = MARKET_DURATION - (int(time.time()) - market_ts)
    tokens = get_market_tokens(asset, market_ts)
    strike = get_strike(asset, market_ts)
    spot = marks.get(asset)
    if not tokens or strike is None or spot is None:
        return log_skip(asset, market_ts, "NO_SIGNAL")

    # How far, in %, is spot through the strike? Sign picks the leading side.
    itm_pct = (spot - strike) / strike * 100.0
    side = "UP" if itm_pct > 0 else "DOWN"
    itm_pct = abs(itm_pct)
    token = tokens["up_token"] if side == "UP" else tokens["down_token"]

    # GATE 1: far enough through the strike (the edge)
    if itm_pct < MIN_ITM_PCT:
        return log_skip(asset, market_ts, "NO_SIGNAL", strike, spot, itm_pct, side)
    # GATE 2: time window
    if not (TIME_BAND[0] <= time_left <= TIME_BAND[1]):
        return log_skip(asset, market_ts, "TOO_LATE", strike, spot, itm_pct, side)
    # GATE 3 + 4: price band + depth
    ask, ask_size = get_book_ask(token)
    if ask is None:
        return log_skip(asset, market_ts, "NO_SIGNAL", strike, spot, itm_pct, side)
    if ask > PRICE_BAND[1]:
        return log_skip(asset, market_ts, "ASK_TOO_HIGH", strike, spot, itm_pct, side, ask)
    if ask < PRICE_BAND[0]:
        return log_skip(asset, market_ts, "ASK_TOO_LOW", strike, spot, itm_pct, side, ask)

    shares = max(MIN_SHARES, round(USD_SIZE / ask))
    if ask_size < shares:
        return log_skip(asset, market_ts, "ASK_TOO_LOW", strike, spot, itm_pct, side, ask)

    # ALL GATES PASSED -> fire a crossable GTC taker at the ask
    ok = place_taker(token, ask, shares, tokens["neg_risk"])
    action = "FILLED" if ok else "NO_FILL"
    tracker.entered.add(key)
    tracker.open_position(asset, market_ts, tokens["slug"], side, token,
                          strike, spot, itm_pct, ask, shares, filled=ok)
    log_skip(asset, market_ts, action, strike, spot, itm_pct, side, ask, shares)
```
place_taker — a crossable GTC BUY (taker on CLOB V2)

```python
def place_taker(token_id, price, shares, neg_risk=False):
    """Crossable GTC BUY = immediate taker fill. Priced AT the ask, depth already
    verified, so it crosses and fills now. NOT post_only — we WANT to take."""
    if PAPER_MODE:
        log_event(f"[PAPER] would take {shares} @ {price:.2f}", "magenta")
        return True

    from py_clob_client_v2.clob_types import OrderArgs, OrderType, PartialCreateOrderOptions
    client = _build_client()
    args = OrderArgs(token_id=str(token_id), price=float(price),
                     size=float(shares), side="BUY")
    options = PartialCreateOrderOptions(neg_risk=True) if neg_risk else None
    try:
        resp = client.create_and_post_order(args, options=options,
                                            order_type=OrderType.GTC)
        if resp and (resp.get("orderID") or resp.get("success")):
            log_event(f"TAKER FILLED {shares} @ {price:.2f}", "green")
            return True
        log_event(f"order rejected: {resp}", "red")
        return False
    except Exception as e:
        log_event(f"post_order failed: {type(e).__name__}: {e}", "red")
        return False
```
Notice PAPER_MODE short-circuits place_taker before any signing happens. In paper mode the bot runs the *entire* real pipeline — data, gates, sizing, logging — and only stubs the one line that spends money. That's the right way to paper-trade: everything real except the fill.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-strike-cross-sniper)

## Step 7: The Trade Tracker and finalize() — Scoring Every Resolution

The bot doesn't just fire and forget. A lightweight TradeTracker holds every open position and the running daily PnL. When a window's market_ts has fully elapsed, finalize() checks how it resolved, scores the trade, updates PnL, and writes the final won / pnl_usd row to the CSV.

Resolution is simple because the strike and the leading side are already known: if the side we bought is the one that won, we get $1.00 per share and our PnL is (1.00 − entry_ask) × shares. If it lost, we're out entry_ask × shares. That's the ~2x asymmetry the whole strategy is built on — risk ~50¢ to make ~50¢, but on a historical near-lock.

TradeTracker + finalize() — resolution scoring

```python
class TradeTracker:
    def __init__(self):
        self.entered = set()      # (asset, market_ts) we've already fired
        self.open = {}            # (asset, market_ts) -> position dict
        self.daily_pnl = 0.0
        self.wins = 0
        self.losses = 0

    def open_position(self, asset, market_ts, slug, side, token,
                      strike, spot, itm_pct, ask, shares, filled):
        if not filled:
            return
        self.open[(asset, market_ts)] = {
            "asset": asset, "slug": slug, "side": side, "token": token,
            "strike": strike, "ask": ask, "shares": shares,
        }

def finalize(tracker, market_ts):
    """Score every open position whose window has fully elapsed."""
    for key in list(tracker.open.keys()):
        asset, ts = key
        if ts != market_ts:
            continue
        pos = tracker.open.pop(key)
        won = resolve_won(pos["asset"], ts, pos["side"], pos["strike"])
        if won:
            pnl = (1.0 - pos["ask"]) * pos["shares"]
            tracker.wins += 1
        else:
            pnl = -pos["ask"] * pos["shares"]
            tracker.losses += 1
        tracker.daily_pnl += pnl
        log_result(pos, ts, won, pnl)

def resolve_won(asset, market_ts, side, strike):
    """Did our side win? Compare the resolution spot to the strike."""
    final_spot = get_strike(asset, market_ts + MARKET_DURATION) or get_hl_marks().get(asset)
    if final_spot is None:
        return None
    if side == "UP":
        return final_spot > strike
    return final_spot < strike
```
Because every open, skip, and result is a CSV row, you can reproduce the exact forensics that birthed this bot on your *own* live trades. That's the point: the bot is also a data collector. Watch your strike_cross_log.csv and re-run the ITM-threshold analysis weekly to see if the edge is holding.

## Step 8: The Main Loop, Window Rollover, and the Daily Stop-Loss

The main loop ties it all together on a CHECK_INTERVAL (2s) cadence. Each tick it computes the current window timestamp with int(time.time()) // 300 * 300, and if that's a new window it first finalize()s the window that just closed (scoring any open positions), then pulls one get_hl_marks() batch and runs hunt() for each of the four assets.

The daily stop-loss is the first thing checked inside the loop. If tracker.daily_pnl ≤ DAILY_STOP_LOSS, the bot stops hunting (but keeps finalizing open positions so nothing is left un-scored). A backtest is a story about the past; the stop-loss is your insurance against the day the story stops being true.

Everything wraps in a live terminal draw() dashboard — per-asset strike vs spot vs ITM%, the recent event log, and the running scoreboard (wins, losses, daily PnL). It's pure UX; strip it out and the bot trades identically. But watching the ITM% tick up toward 0.10% and then seeing a green TAKER FILLED line is how you build trust in the edge before you scale the size.

main() — rollover, stop-loss, hunt the fleet

```python
def main():
    tracker = TradeTracker()
    last_ts = None
    print(colored("STRIKE-CROSS SNIPER v1.0 — LIVE" if not PAPER_MODE
                  else "STRIKE-CROSS SNIPER v1.0 — PAPER", "cyan", attrs=["bold"]))

    while True:
        now = int(time.time())
        market_ts = now // MARKET_DURATION * MARKET_DURATION

        # New window? Score the one that just closed.
        if last_ts is not None and market_ts != last_ts:
            finalize(tracker, last_ts)
        last_ts = market_ts

        # Daily stop-loss: stop opening, keep resolving.
        halted = tracker.daily_pnl <= DAILY_STOP_LOSS

        marks = get_hl_marks()
        if marks and not halted:
            for asset in ASSETS:
                try:
                    hunt(asset, market_ts, marks, tracker)
                except Exception as e:
                    log_event(f"{asset} hunt error: {e}", "red")

        draw(tracker, marks, market_ts, halted)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colored("\nStopped by Moon Dev. Stay liquid.", "yellow"))
```
That's the whole lifecycle: every 2 seconds, one Hyperliquid batch, four hunt() passes, a finalize on rollover, a dashboard redraw. Small, legible, and every decision is written to disk.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/polymarket-strike-cross-sniper)

## Putting It All Together

Zoom out and the bot is one clean idea wrapped in disciplined plumbing. The idea: **the CLOB lags the spot**, so when Hyperliquid mark price has moved ≥ 0.10% through the market's own strike, buy the still-cheap leading side as a taker. The plumbing: two data sources (Polymarket strike, Hyperliquid spot), four entry gates (ITM, time, price band, depth), one entry per window, hold to resolution, and a CSV that records every decision.

The single-file, zero-dependency build is what makes it deployable and auditable — one pip install, one file, no framework. And the daily stop-loss plus paper mode are the guardrails that keep a backtested edge from becoming a live disaster before you've verified it's real on your own account.

## How to Run It

The only dependency is py_clob_client_v2 (it pulls requests and web3 in with it). Your repo-root .env needs the keys for whichever account ACCOUNT_SUFFIX points at — for AUG14 that's PRIVATE_KEY_AUG14, PUBLIC_KEY_AUG14, and API credentials.

Run the bot

```python
# 1) One and only dependency
pip install py_clob_client_v2

# 2) Confirm your .env (anywhere up the tree, or ~/.env) has:
#    PRIVATE_KEY_AUG14=0x...
#    PUBLIC_KEY_AUG14=0x...
#    API_KEY_AUG14=...  PASSPHRASE_AUG14=...  (optional — will derive if missing)

# 3) PAPER FIRST. Open the file and set PAPER_MODE = True
#    Watch a few windows roll through and confirm the gates + logging.

python strike_cross_sniper.py

# 4) When you trust it, flip PAPER_MODE = False. Ctrl+C to bail.
```
Start with USD_SIZE = 5 and PAPER_MODE = True. Let it run for a day, open data/strike_cross_log.csv, and check that the ITM ≥ 0.10% rows are actually winning before you send a single real dollar. The whole point of this bot is that it hands you the data to verify its own edge.

## Go Build Your Own Edge

Don't just run this bot. The fastest way to lose money is to copy-paste someone else's strategy and hope. The Strike-Cross Sniper is here to teach you a repeatable process: **form a hypothesis, log everything, run the forensics, gate hard, and put a stop-loss under it.** That process is the real asset — the specific 0.10% threshold is just this week's expression of it.

Tweak the knobs, test your own ITM thresholds, add a fifth asset, tighten the price band. If you build something that works — or find where this edge decays — come share it with the Moon Dev community. Built with love by Moon Dev 🌙

## Want to build trading bots with Moon Dev?

Join the community, get the full code from every video, and learn algorithmic trading, quantitative finance, and how to actually automate your trading.

[Explore the Roadmap](https://moondev.com/roadmap)

## Related Moon Dev Builds

[

### Polymarket 95¢ Bid Sniper

The patient, maker-only cousin — sits on the bid of already-decided markets.

[

### Polymarket × Hyperliquid Stat Arb

Another cross-venue edge between Polymarket odds and Hyperliquid liquidations.

[

### Polymarket 5-Minute Bot

The original 5-minute UP/DOWN market bot walkthrough.

[

### Full Code-From-Videos Roadmap

Every open-source trading bot walkthrough in one place.

Built with love by Moon Dev 🌙
