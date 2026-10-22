<!-- source: https://moondev.com/btc-etf-flow-tracker -->
<!-- captured: 2026-10-07 -->
<!-- title: BTC ETF Flow Tracker — Terminal Chart + Live OLS Flow Estimator -->

BTC ETF Flow Tracker: Python Terminal Chart + Live Flow Estimator | Moon Dev

Moon Dev Open Source

# BTC ETF Flow Tracker: Charting the Whale of the 2026 Tape (and Guessing Tonight's Print Before It Lands)

US spot Bitcoin ETF net flows are the single most important number on the crypto tape right now — the discretionary whale that moves price. This Python tool charts every day of flows right in your terminal AND fits a tiny OLS model on every run to estimate tonight's flow print *while the session is still open*. Let's build it together.

By Moon Dev · July 6, 2026

## Why ETF Flows Are the Number That Matters

Here's the thesis. Since the US spot Bitcoin ETFs launched on January 11, 2024, a brand new kind of buyer showed up to the party: the RIA, the wealth manager, the boomer with a brokerage account who will never touch a hardware wallet but *will* click buy on IBIT. That flow is discretionary, it's huge, and it's the closest thing crypto has to a real institutional bid. When those ETFs are hoovering up coins day after day, and the forced sellers (miners, blow-up funds, over-levered longs getting liquidated) start running dry, you get what Moon Dev calls the **seller-exhaustion setup** — thin supply meeting a persistent bid.

The problem is that the official daily net-flow print doesn't land until roughly 6–10pm ET, hours after the equity session closes. If you only look at flows the next morning, you're reacting to news everyone already has. So this tool does two things. First, it charts the entire history of ETF flows directly in your terminal — no browser, no dashboard, just clean bars next to the BTC price column so you can eyeball the regime. Second, and this is the fun part, it fits a small statistical model on every run that estimates **tonight's flow number before the official print**, using signals you *can* see live: yesterday's flow, today's BTC move, and the premium/discount on IBIT versus its net asset value.

By the end of this walkthrough you'll understand how to pull real data from four different sources (and fail loudly when they're down), how to render a bar chart in a terminal that auto-sizes to your window, and how to build a self-recalibrating ordinary-least-squares estimator that re-fits itself against the exact same bars it's charting. This is real quant plumbing — the kind of thing that separates "I read about ETF flows" from "I have a live model of ETF flows." Let's go.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/btc-etf-flow-tracker)

## Step 1: Imports, Colors, and a Session That Refuses to Hang

The top of the file is where we set the tone: real data only, fail loudly, never hang. The imports are lean — numpy for the least-squares math, pandas for the time-series wrangling, requests for the HTTP calls, plus a couple of standard-library helpers. Those GREEN, RED, DIM constants are raw ANSI escape codes — the magic strings that make your terminal print in color. No colorama needed; we just write the escape codes directly.

The two most important design decisions live in the last few lines. TIMEOUT = (5, 30) is a tuple: fail fast on the connect (5 seconds) but allow a generous 30 seconds for the read. This is the difference between a script that hangs for minutes when a source is flaky and one that bails immediately so you know something's wrong. And the SESSION with a mounted Retry adapter automatically retries connection flakes and rate-limit responses (429/502/503) with exponential backoff. Coinbase's WAF loves to drop SYN packets under burst, so this retry logic is what keeps the pagination loop from dying on a transient hiccup.

Docstring, imports, and the resilient session

```python
"""
Moon Dev's BTC ETF Flow Tracker
================================
Terminal chart of US spot Bitcoin ETF daily net flows (the number that matters —
the discretionary whale of the 2026 tape) + BTC close, value traded, and AUM.
Auto-sizes bars to your terminal width; auto-switches to WEEKLY bars on long
windows so you can eyeball two+ years of regime against the price column.

Data sources (real data only, script fails loudly if all sources are down):
  - Farside Investors full history since ETF launch Jan 11 2024 (via r.jina.ai
    reader since farside.co.uk is Cloudflare-walled; cached locally to CSV)
  - SoSoValue open API (no key): last ~300 days of flow + value traded + AUM
  - Coinbase Exchange public API: BTC-USD daily closes (paginated)
  - Yahoo Finance chart API: live IBIT price/volume for the intraday read

Run it:
  /opt/anaconda3/envs/tflow/bin/python data/btc_etf_flow_tracker.py         # last 90 days
  /opt/anaconda3/envs/tflow/bin/python data/btc_etf_flow_tracker.py 30      # last N sessions
  /opt/anaconda3/envs/tflow/bin/python data/btc_etf_flow_tracker.py all     # full history (weekly bars)

Built by Moon Dev 2026-07-06 tracking the seller-exhaustion thesis.
"""

import io
import re
import sys
import shutil
import time
from pathlib import Path

import numpy as np
import requests
import pandas as pd

GREEN, RED, DIM, BOLD, RESET = "\033[92m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"
UA = {"User-Agent": "Mozilla/5.0 (Moon Dev's flow tracker)"}
TIMEOUT = (5, 30)  # fail fast on connect (5s), allow 30s reads — no silent multi-minute hangs

# retry connect flakes (Coinbase WAF drops SYNs under burst) then fail loudly
from requests.adapters import HTTPAdapter, Retry
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(total=3, connect=3, backoff_factor=2,
                                                        status_forcelist=[429, 502, 503])))
```
Notice the philosophy baked into the docstring: **"real data only, script fails loudly if all sources are down."** There's no fallback to fake numbers, no "if the API fails just return zero." In trading, silently bad data is far more dangerous than a loud crash. A crash you notice. A wrong number you trade on.

## Step 2: Config, CLI Argument, and Auto-Sizing to Your Terminal

This little block does a surprising amount of work. The status() helper just prints dimmed progress messages so you can see what the script is doing while it fetches. CACHE is where we'll stash the full Farside history as a CSV so we don't hammer their site on every run. And WEEKLY_THRESHOLD = 120 is the switch: any window longer than 120 sessions automatically collapses into weekly bars so a two-year chart still fits on your screen.

The CLI argument handling is dead simple but flexible. Run with no argument and you get the last 90 sessions. Pass a number for N sessions. Pass all and it sets DAYS to 10,000, which is effectively "everything since launch." The last two lines are the clever bit: shutil.get_terminal_size() reads how wide your terminal actually is, and BAR_WIDTH is computed from that — clamped between 6 and 24 characters — so the chart looks right whether you're in a skinny SSH window or a full-screen terminal.

Configuration and auto-sizing

```python
def status(msg):
    print(f"{DIM}  ...{msg}{RESET}", flush=True)
CACHE = Path(__file__).parent / "farside_btc_etf_flows.csv"
WEEKLY_THRESHOLD = 120  # sessions; beyond this the chart aggregates to weekly bars

arg = sys.argv[1] if len(sys.argv) > 1 else "90"
DAYS = 10_000 if arg.lower() == "all" else int(arg)

TERM_W = shutil.get_terminal_size((100, 24)).columns
BAR_WIDTH = max(6, min(24, (TERM_W - 44) // 2))
```
The (TERM_W - 44) // 2 math reserves 44 characters for the date, price, flow number, and AUM columns, then splits the remaining width in half — because the flow bars extend both left (outflows, red) and right (inflows, green) from a center line. We'll see that center-line rendering in Step 6.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/btc-etf-flow-tracker)

## Step 3: The Full History from Farside (and the Cloudflare Workaround)

Farside Investors publishes the gold-standard table of daily ETF net flows going all the way back to launch. The catch: farside.co.uk is behind Cloudflare, so a plain requests.get() gets bounced. The workaround is a neat trick: r.jina.ai is a free reader proxy that fetches a page and returns it as clean markdown. Prefix any URL with it and you get through the Cloudflare wall, with the table already converted to markdown pipe-delimited rows.

Because that markdown table is predictable, we parse it with a regex that matches lines starting with a date like | 11 Jan 2024 |. We skip holiday rows (where every cell is a dash) and grab the last cell, which is the total net flow. Farside writes negative numbers in accounting parentheses — (120.5) means an outflow of $120.5M — so we detect the leading paren and flip the sign ourselves.

The caching logic is worth studying. We only re-fetch if the cache is missing or older than 12 hours. And there's a defensive guard: if the fetch comes back with fewer than 400 rows (a sign the proxy returned something garbled), we fall back to the existing cache rather than overwriting good data with junk. If there's *no* cache to fall back on, we raise a loud RuntimeError. That's the "fail loudly" principle in action — never silently persist a thin, broken dataset.

fetch_farside_full

```python
def fetch_farside_full():
    """Full daily net-flow history since Jan 11 2024, cached to CSV."""
    fresh = CACHE.exists() and time.time() - CACHE.stat().st_mtime < 12 * 3600
    if not fresh:
        status("fetching Farside full history via jina proxy (first run / stale cache)")
        r = SESSION.get("https://r.jina.ai/https://farside.co.uk/bitcoin-etf-flow-all-data/",
                         headers=UA, timeout=(5, 60))
        rows = []
        for line in r.text.splitlines():
            m = re.match(r"^\| (\d{2} \w{3} \d{4}) \|(.*)\|", line)
            if not m:
                continue
            cells = [c.strip() for c in m.group(2).split("|")]
            if all(c == "-" for c in cells[:-1]):
                continue  # holiday / not-yet-reported day
            total = cells[-1].replace(",", "")
            val = -float(total[1:-1]) if total.startswith("(") else float(total)
            rows.append({"date": m.group(1), "flow_m": val})
        if len(rows) < 400:
            if CACHE.exists():
                print(f"{DIM}Moon Dev note: Farside fetch thin ({len(rows)} rows), using cached CSV{RESET}")
                rows = None
            else:
                raise RuntimeError(f"Moon Dev alert: Farside via jina returned only {len(rows)} rows and no cache exists!")
        if rows:
            pd.DataFrame(rows).to_csv(CACHE, index=False)
    df = pd.read_csv(CACHE)
    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y")
    return df.set_index("date").sort_index()
```
The final three lines read the CSV back, parse the date strings into real pandas timestamps, and return a clean DataFrame indexed by date and sorted chronologically. From here on, Farside is just a tidy time series of one column: flow_m, net flow in millions of dollars.

## Step 4: SoSoValue for the Rich Data, Coinbase for the Price

Farside gives us the long history, but it's just the flow number. SoSoValue's open API (no key required) gives us the last ~300 days with three columns we care about: net inflow, total value traded, and total net assets (AUM). We divide by 1e6 and 1e9 to normalize into millions (flow) and billions (traded/AUM) — the units that read cleanly in the terminal table. This is our richer, more recent source, and it's also the source the flow estimator will train against.

For the BTC price column we go straight to Coinbase's public candle API. There's one gotcha: Coinbase caps you at 300 candles per request. With daily granularity that's under a year, so for any longer window we have to **paginate** — walk forward in ~290-day chunks until we reach now. Notice we freeze now once before the loop; if you recomputed it each iteration you could end up with a tiny degenerate final chunk. And the time.sleep(0.35) between requests keeps us polite — Coinbase throttles bursts at the connection level, and combined with the retry adapter from Step 1 this makes the loop bulletproof.

fetch_sosovalue and fetch_btc_closes

```python
def fetch_sosovalue():
    """Last ~300 days: flow + value traded + AUM."""
    status("fetching SoSoValue flows/AUM")
    r = SESSION.post("https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart",
                      json={"type": "us-btc-spot"}, timeout=TIMEOUT)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["data"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    df["flow_m"] = df["totalNetInflow"] / 1e6
    df["traded_b"] = df["totalValueTraded"] / 1e9
    df["aum_b"] = df["totalNetAssets"] / 1e9
    return df[["flow_m", "traded_b", "aum_b"]]

def fetch_btc_closes(start):
    """Coinbase daily closes, paginated (300 candles max per request)."""
    status("fetching BTC daily candles from Coinbase")
    out = []
    t0 = pd.Timestamp(start)
    now = pd.Timestamp.utcnow().tz_localize(None)  # freeze once: no degenerate final chunk
    while t0 < now:
        t1 = min(t0 + pd.Timedelta(days=290), now)
        r = SESSION.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                        params={"granularity": 86400, "start": t0.isoformat(), "end": t1.isoformat()},
                        headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        out += r.json()
        t0 = t1
        time.sleep(0.35)  # stay polite, Coinbase throttles bursts at the connection level
    candles = pd.DataFrame(out, columns=["time", "low", "high", "open", "close", "vol"]).drop_duplicates("time")
    candles["date"] = pd.to_datetime(candles["time"], unit="s").dt.normalize()
    return candles.set_index("date")["close"]
```
We drop_duplicates on the timestamp because overlapping chunk boundaries can return the same candle twice, then normalize the unix timestamps to midnight so they line up cleanly with the daily flow index. The function returns a single pandas Series of closes, indexed by date — ready to be mapped onto the flow DataFrame.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/btc-etf-flow-tracker)

## Step 5: The Live Read, Part 1 — IBIT Premium and Volume Pace

This is the marquee feature, so let's take it slow. The idea: IBIT (BlackRock's fund) is roughly 60% of the entire sector's assets, so its tape leads the aggregate flow print. If we can read IBIT's behavior *during* the session — how it's trading relative to its net asset value, and how heavy its volume is — we can guess where tonight's total flow number will land before it's officially reported.

First we pull six months of daily IBIT bars from Yahoo Finance's chart API and grab the live BTC spot price from Coinbase. Then we compute the **premium**: an ETF share should track a fixed ratio to BTC, so we take the median IBIT/BTC ratio over the last ten completed sessions and measure how far today's live ratio has drifted from it, expressed in basis points. A positive premium means IBIT is trading rich to its NAV — a sign of net creation pressure (authorized participants minting new shares to meet demand, which corresponds to inflows).

Next we compute how far into the trading session we are (frac, clamped so we never divide by near-zero at the open) and the **volume pace** — today's volume-so-far scaled up by how much of the session remains, compared to the recent 20-day average. A pace of 1.5x means IBIT is on track to trade 50% heavier than normal, which usually means a big flow day in one direction or the other.

live_ibit_read — fetching and the premium/pace signals

```python
def live_ibit_read(btc_daily_closes, soso):
    """
    Moon Dev's early-warning read: tonight's flow print in $M, estimated DURING the
    session. The estimator is a small OLS model re-fit on every run against the REAL
    historical daily flows (the same bars charted below), using three live-computable
    features: yesterday's flow (streaks persist), today's BTC move (flows chase
    price), and IBIT premium x sector volume (AP creation/redemption pressure).
    IBIT ~60% of sector AUM -> its tape leads the aggregate print.
    """
    status("fetching live IBIT from Yahoo")
    r = SESSION.get("https://query1.finance.yahoo.com/v8/finance/chart/IBIT",
                    params={"interval": "1d", "range": "6mo"}, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    chart = r.json()["chart"]["result"][0]
    meta, quote = chart["meta"], chart["indicators"]["quote"][0]
    dates = pd.to_datetime(chart["timestamp"], unit="s").normalize()
    ibit = pd.DataFrame({"close": quote["close"], "volume": quote["volume"]}, index=dates).dropna()

    spot = SESSION.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker",
                       headers=UA, timeout=TIMEOUT).json()
    btc_now = float(spot["price"])
    ibit_now = meta["regularMarketPrice"]

    hist = ibit.iloc[:-1]  # completed sessions only
    ratios = hist["close"].tail(10) / hist.index[-10:].map(btc_daily_closes)
    premium_bps = (ibit_now / btc_now / ratios.median() - 1) * 10_000

    reg = meta["currentTradingPeriod"]["regular"]
    now = meta["regularMarketTime"]
    frac = min(max((now - reg["start"]) / (reg["end"] - reg["start"]), 0.02), 1.0)
    session_open = reg["start"] <= now < reg["end"]
    vol_today = ibit["volume"].iloc[-1]
    pace = vol_today / (hist["volume"].tail(20).mean() * frac)
```
The key subtlety is hist = ibit.iloc[:-1] — we drop today's still-forming bar when computing the historical baseline, because today isn't done yet. You always want to calibrate against *completed* sessions and then apply that calibration to the live, partial one.

## Step 5: The Live Read, Part 2 — The Self-Recalibrating OLS Model

Now the statistics. Instead of hard-coding "if premium is high then inflows," we let the data tell us the weights. On every single run we build a feature matrix from history and solve an ordinary-least-squares regression against the *real* daily flow numbers — the same bars we're about to chart. Three features drive the model: **flow_lag** (yesterday's flow, because flow streaks persist), **btc_ret** (today's BTC percentage move, because flows chase price), and **press** (premium times value traded, the authorized-participant creation/redemption pressure signal).

We stack those features with a column of ones (the intercept) into matrix X and hand it to np.linalg.lstsq, which returns the beta coefficients that best fit the historical flows. Then — this is the honest part — we compute the residuals and report both R² (how much variance the model explains) and RMSE (the typical dollar error). The tool never pretends to be an oracle; it tells you its own error bars every time it prints. Re-fitting on every run means the model automatically adapts as the flow regime shifts, no stale saved weights.

To turn the model into a prediction we build one live feature row x_live: yesterday's actual flow, BTC's move since yesterday's close, and the live premium multiplied by a projection of tonight's full-day sector value traded (backed out from IBIT's pace and its typical share of sector volume). Dot that row with beta and you get est_m — the estimated flow in millions — which we also convert to an approximate number of BTC bought or sold.

live_ibit_read — the OLS fit, the live prediction, and the print

```python
    # ---- calibrate flow model on history (real bars, re-fit every run) ----
    d = ibit.copy()
    d["btc"] = d.index.map(btc_daily_closes)
    ratio = d["close"] / d["btc"]
    d["prem"] = (ratio / ratio.rolling(10).median().shift(1) - 1) * 10_000
    d["ibit_dvol_b"] = d["close"] * d["volume"] / 1e9
    d = d.join(soso[["flow_m", "traded_b"]])
    d["flow_lag"] = d["flow_m"].shift(1)
    d["btc_ret"] = d["btc"].pct_change() * 100
    d["press"] = d["prem"] * d["traded_b"]
    fit = d.iloc[:-1][["flow_m", "flow_lag", "btc_ret", "press"]].dropna()
    X = np.column_stack([np.ones(len(fit)), fit["flow_lag"], fit["btc_ret"], fit["press"]])
    beta, *_ = np.linalg.lstsq(X, fit["flow_m"].values, rcond=None)
    resid = fit["flow_m"].values - X @ beta
    r2 = 1 - (resid ** 2).sum() / ((fit["flow_m"] - fit["flow_m"].mean()) ** 2).sum()
    rmse = float(np.sqrt((resid ** 2).mean()))

    ibit_share = (d["ibit_dvol_b"] / d["traded_b"]).tail(20).median()
    sector_traded_proj = (vol_today / frac * ibit_now / 1e9) / ibit_share
    x_live = np.array([1.0, soso["flow_m"].iloc[-1],
                       (btc_now / d["btc"].iloc[-2] - 1) * 100,
                       premium_bps * sector_traded_proj])
    est_m = float(x_live @ beta)
    est_btc = est_m * 1e6 / btc_now
    ecolor = GREEN if est_m >= 0 else RED

    print(f"{BOLD}⚡ LIVE READ — tonight's ETF flow print, estimated now "
          f"({'session OPEN' if session_open else 'market closed, projecting last session'}){RESET}")
    print(f"  {ecolor}{BOLD}EST FLOW ≈ {est_m:+,.0f}M{RESET}{ecolor} = ~{est_btc:+,.0f} BTC "
          f"{'bought' if est_m >= 0 else 'sold'}{RESET} {DIM}(± {rmse:,.0f}M model error, "
          f"R² {r2:.2f} on {len(fit)} sessions){RESET}")
    print(f"  drivers: yesterday {soso['flow_m'].iloc[-1]:+,.0f}M | BTC {x_live[2]:+.1f}% today | "
          f"IBIT {premium_bps:+.0f}bps vs NAV on {pace:.1f}x volume pace")
    print(f"  {DIM}model estimate, not a measurement — official print lands ~6-10pm ET{RESET}\n")
```
### Why re-fit every run instead of saving the model?

A saved model is a frozen opinion. The relationship between IBIT premium and next flow print drifts as the market's microstructure changes — new APs, changing fee structures, shifting demand. By solving the least-squares fit fresh on every run against the most recent history, the coefficients stay current automatically. It costs a few milliseconds of numpy and buys you a model that never goes stale. And because it prints R² and RMSE alongside the estimate, you always know how much to trust tonight's number. Low R²? Take the read with a grain of salt. That transparency is the whole point.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/btc-etf-flow-tracker)

## Step 6: Drawing Bars in a Terminal

No matplotlib, no browser — just Unicode block characters and spaces. The bar() function takes a flow value and the chart's scale (the largest absolute flow in the window) and returns a string that renders a horizontal bar. The trick is a center line: inflows grow to the *right* in green, outflows grow to the *left* in red, with a dim | marking zero in the middle.

The math is a simple proportion: what fraction of the max is this flow, times the bar width, capped so it never overflows. For a positive flow we print BAR_WIDTH spaces (the empty left half), the center pipe, then n green blocks padded out to full width. For a negative flow we do the mirror image: right-align n red blocks against the center line. Both branches always return exactly the same total width, so the columns to the right of the chart stay perfectly aligned.

The bar renderer

```python
def bar(flow, scale):
    n = min(int(abs(flow) / scale * BAR_WIDTH), BAR_WIDTH) if scale else 0
    if flow >= 0:
        return " " * BAR_WIDTH + DIM + "|" + RESET + GREEN + "█" * n + RESET + " " * (BAR_WIDTH - n)
    return " " * (BAR_WIDTH - n) + RED + "█" * n + RESET + DIM + "|" + RESET + " " * BAR_WIDTH
```
That if scale else 0 guard is a small but important defense: if every flow in the window happened to be zero (or the scale is somehow zero), we'd divide by zero without it. Little guards like this are what keep a tool from crashing on a weird edge day.

## Step 7: Assembling the Window (and Collapsing to Weekly Bars)

Here's where the data sources come together. We always fetch SoSoValue first. If your requested window fits inside what SoSoValue covers (~300 days), we just use it — it's the richest source. If you asked for more history than that, we pull the full Farside record and join the SoSoValue traded/AUM columns onto it wherever they overlap. So short windows get the full detail, and long windows get the complete flow history with detail where available. Then we map the BTC closes onto whichever DataFrame we ended up with.

The weekly aggregation is the elegant part. If the window is longer than 120 sessions, staring at 500 daily bars is useless — so we resample to Friday-ending weeks. Flows and value traded get **summed** across the week (they're additive quantities), AUM and BTC close take the **last** value (they're point-in-time levels), and we keep a n_days count so we can drop empty weeks. This is a great little lesson in resampling: not every column aggregates the same way. Sum the flows, take the last of the levels.

Assembling the window and weekly resampling

```python
# ---- assemble the window ----
soso = fetch_sosovalue()
if DAYS <= len(soso):
    flows = soso.tail(DAYS).copy()
else:
    flows = fetch_farside_full()
    flows = flows.join(soso[["traded_b", "aum_b"]])  # traded/AUM only where SoSoValue reaches
    flows = flows.tail(DAYS).copy()

btc = fetch_btc_closes(min(flows.index[0], soso.index[0]) - pd.Timedelta(days=5))
flows["btc_close"] = flows.index.map(btc)

weekly = len(flows) > WEEKLY_THRESHOLD
if weekly:
    flows = pd.DataFrame({
        "flow_m": flows["flow_m"].resample("W-FRI").sum(),
        "traded_b": flows["traded_b"].resample("W-FRI").sum(min_count=1) if "traded_b" in flows else None,
        "aum_b": flows["aum_b"].resample("W-FRI").last() if "aum_b" in flows else None,
        "btc_close": flows["btc_close"].resample("W-FRI").last(),
        "n_days": flows["flow_m"].resample("W-FRI").count(),
    }).dropna(subset=["n_days"])
    flows = flows[flows["n_days"] > 0]

scale = flows["flow_m"].abs().max()
unit = "week" if weekly else "session"
```
After this block, flows is a tidy DataFrame — one row per session or per week — with everything we need to chart: the flow, the traded volume, the AUM, and the BTC close. The scale is the biggest absolute flow, which the bar() function uses to size everything proportionally.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/btc-etf-flow-tracker)

## Step 8: Printing the Chart

First we call live_ibit_read() so the estimate prints at the top — that's the first thing you want to see. Then we print a header with the date range and a subtitle noting the data sources, the bar mode (daily vs weekly), and the exact dollar scale of the bars. The column header uses ◄ and ► arrows to remind you that left is outflow and right is inflow.

The loop itself walks each row and draws it. There's a nice touch for readability: in daily mode it prints a horizontal rule at the start of each week (when date.weekday() == 0, i.e. Monday); in weekly mode it prints a rule at each quarter boundary. Each row shows the BTC price in thousands (like 68.4k), the color-coded bar, the signed flow number, and the traded/AUM columns — with dashes where a value is missing so the table never breaks alignment.

Header and the render loop

```python
print()
live_ibit_read(btc, soso)

print(f"{BOLD}🌙 BTC ETF FLOWS — {len(flows)} {unit}s ({flows.index[0]:%b %d %Y} → {flows.index[-1]:%b %d %Y}) — Moon Dev{RESET}")
print(f"{DIM}Farside/SoSoValue + Coinbase | {'WEEKLY bars (Fri-ending)' if weekly else 'daily bars'} | "
      f"bar scale ±${scale:,.0f}M | $M flow, $B traded/AUM{RESET}\n")

datew = 9 if weekly else 6
print(BOLD + f"{'DATE':<{datew}} {'BTC':>7}  {'◄':>{BAR_WIDTH}} {'►':<{BAR_WIDTH}} {'FLOW':>8} {'TRD':>4} {'AUM':>5}" + RESET)
rule = DIM + "─" * (datew + BAR_WIDTH * 2 + 30) + RESET

prev_period = None
for date, row in flows.iterrows():
    period = date.strftime("%Y-%m") if weekly else date.weekday() == 0
    if weekly:
        if prev_period and period != prev_period and date.month in (1, 4, 7, 10):
            print(rule)  # quarter breaks in weekly mode
        prev_period = period
    elif period:
        print(rule)
    px = f"{row.btc_close/1000:,.1f}k" if pd.notna(row.btc_close) else "?"
    color = GREEN if row.flow_m >= 0 else RED
    label = date.strftime("%d%b%y") if weekly else date.strftime("%b %d")
    trd = f"{row.traded_b:>4,.1f}" if "traded_b" in row and pd.notna(row.traded_b) else "   -"
    aum = f"{row.aum_b:>5,.1f}" if "aum_b" in row and pd.notna(row.aum_b) else "    -"
    print(f"{label:<{datew}} {px:>7}  {bar(row.flow_m, scale)} {color}{row.flow_m:>+8,.0f}{RESET} {trd} {aum}")
```
Every format specifier here is doing alignment work — {label:<{datew}} left-pads the date, {row.flow_m:>+8,.0f} right-aligns the flow with a forced sign and thousands separators. This obsessive alignment is what makes a terminal table feel like a real chart instead of a wall of text.

## Step 9: Moon Dev's Read — the Summary That Ties It to the Thesis

The chart shows you the trees; this final block shows you the forest. We compute the current **streak** — how many consecutive sessions (or weeks) the flow has stayed the same sign — by walking backwards from the latest bar until the sign flips. A long green streak is exactly the persistent-bid condition the whole tool exists to detect.

Then we roll up the essentials: the latest flow, the trailing 5- and 20-period sums (short and medium momentum), the total for the whole window with a green/total tally, and the single worst and best days. Finally, the punchline — the trigger condition Moon Dev is actually watching for: **green AND holding while forced sellers empty = thin-supply setup.** That's the seller-exhaustion thesis in one line. Persistent ETF inflows plus a drying-up of forced supply is the structural setup that precedes the moves.

Streak computation and Moon Dev's read

```python
# ---- Moon Dev's summary ----
last = flows.iloc[-1]
streak_sign = 1 if last.flow_m >= 0 else -1
streak = 0
for f in reversed(flows["flow_m"].tolist()):
    if (1 if f >= 0 else -1) != streak_sign:
        break
    streak += 1

green = (flows["flow_m"] >= 0).sum()
print(f"""
{BOLD}MOON DEV'S READ{RESET}
  Latest ......... {GREEN if last.flow_m >= 0 else RED}{last.flow_m:+,.0f}M{RESET} ({flows.index[-1]:%b %d}) | streak: {streak} {'green' if streak_sign > 0 else 'red'} {unit}(s)
  Last 5 / 20 .... {flows['flow_m'].tail(5).sum():+,.0f}M / {flows['flow_m'].tail(20).sum():+,.0f}M
  Window ......... {flows['flow_m'].sum():+,.0f}M ({green}/{len(flows)} green)
  Worst / best ... {flows['flow_m'].min():+,.0f}M {flows['flow_m'].idxmin():%b %d %y} / {flows['flow_m'].max():+,.0f}M {flows['flow_m'].idxmax():%b %d %y}

  Trigger: green AND holding while forced sellers empty = thin-supply setup. 🌙
""")
```
Notice how the summary reuses the same unit variable from Step 7, so it correctly says "green sessions" or "green weeks" depending on the mode. Small consistency details like that are what make a tool feel finished.

## Putting It All Together

Step back and the whole thing is a clean pipeline. Four data sources feed in: Farside for the deep history, SoSoValue for the recent rich detail, Coinbase for the BTC price column, and Yahoo for the live IBIT tape. The window-assembly logic (Step 7) decides which sources to blend based on how much history you asked for and whether to collapse to weekly bars. The OLS estimator (Step 5) trains on the same flow data you're charting and prints tonight's guess with honest error bars. The bar() renderer (Step 6) and the print loop (Step 8) turn it all into a chart in your terminal. And the summary (Step 9) collapses it to the one thing you actually trade on: is the whale buying, and are the sellers running out?

The through-line is discipline: real data only, fail loudly, show your error bars, and never hide a broken source behind a fake number. That's the difference between a toy and a tool you'd actually put money behind.

## How to Run It

Only two dependencies beyond the standard library. Install them, drop the script somewhere, and run it. No API keys required — every source here is public.

Install and run

```python
pip install numpy pandas requests

# last 90 sessions (default)
python btc_etf_flow_tracker.py

# last N sessions
python btc_etf_flow_tracker.py 30

# full history since launch, weekly bars
python btc_etf_flow_tracker.py all
```
The very first run fetches the full Farside history through the jina proxy and caches it to farside_btc_etf_flows.csv next to the script; subsequent runs within 12 hours read straight from that cache and are near-instant. Widen your terminal for fatter bars, and run it right before the flow print lands to see how close the live estimate gets.

## Full Source Code

Here's the complete tracker in one block. Study it, tweak the features in the OLS model, add your own data source — make it yours.

btc_etf_flow_tracker.py (full)

```python
"""
Moon Dev's BTC ETF Flow Tracker
================================
Terminal chart of US spot Bitcoin ETF daily net flows (the number that matters —
the discretionary whale of the 2026 tape) + BTC close, value traded, and AUM.
Auto-sizes bars to your terminal width; auto-switches to WEEKLY bars on long
windows so you can eyeball two+ years of regime against the price column.

Data sources (real data only, script fails loudly if all sources are down):
  - Farside Investors full history since ETF launch Jan 11 2024 (via r.jina.ai
    reader since farside.co.uk is Cloudflare-walled; cached locally to CSV)
  - SoSoValue open API (no key): last ~300 days of flow + value traded + AUM
  - Coinbase Exchange public API: BTC-USD daily closes (paginated)
  - Yahoo Finance chart API: live IBIT price/volume for the intraday read

Run it:
  /opt/anaconda3/envs/tflow/bin/python data/btc_etf_flow_tracker.py         # last 90 days
  /opt/anaconda3/envs/tflow/bin/python data/btc_etf_flow_tracker.py 30      # last N sessions
  /opt/anaconda3/envs/tflow/bin/python data/btc_etf_flow_tracker.py all     # full history (weekly bars)

Built by Moon Dev 2026-07-06 tracking the seller-exhaustion thesis.
"""

import io
import re
import sys
import shutil
import time
from pathlib import Path

import numpy as np
import requests
import pandas as pd

GREEN, RED, DIM, BOLD, RESET = "\033[92m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"
UA = {"User-Agent": "Mozilla/5.0 (Moon Dev's flow tracker)"}
TIMEOUT = (5, 30)  # fail fast on connect (5s), allow 30s reads — no silent multi-minute hangs

# retry connect flakes (Coinbase WAF drops SYNs under burst) then fail loudly
from requests.adapters import HTTPAdapter, Retry
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(total=3, connect=3, backoff_factor=2,
                                                        status_forcelist=[429, 502, 503])))

def status(msg):
    print(f"{DIM}  ...{msg}{RESET}", flush=True)
CACHE = Path(__file__).parent / "farside_btc_etf_flows.csv"
WEEKLY_THRESHOLD = 120  # sessions; beyond this the chart aggregates to weekly bars

arg = sys.argv[1] if len(sys.argv) > 1 else "90"
DAYS = 10_000 if arg.lower() == "all" else int(arg)

TERM_W = shutil.get_terminal_size((100, 24)).columns
BAR_WIDTH = max(6, min(24, (TERM_W - 44) // 2))

def fetch_farside_full():
    """Full daily net-flow history since Jan 11 2024, cached to CSV."""
    fresh = CACHE.exists() and time.time() - CACHE.stat().st_mtime < 12 * 3600
    if not fresh:
        status("fetching Farside full history via jina proxy (first run / stale cache)")
        r = SESSION.get("https://r.jina.ai/https://farside.co.uk/bitcoin-etf-flow-all-data/",
                         headers=UA, timeout=(5, 60))
        rows = []
        for line in r.text.splitlines():
            m = re.match(r"^\| (\d{2} \w{3} \d{4}) \|(.*)\|", line)
            if not m:
                continue
            cells = [c.strip() for c in m.group(2).split("|")]
            if all(c == "-" for c in cells[:-1]):
                continue  # holiday / not-yet-reported day
            total = cells[-1].replace(",", "")
            val = -float(total[1:-1]) if total.startswith("(") else float(total)
            rows.append({"date": m.group(1), "flow_m": val})
        if len(rows) < 400:
            if CACHE.exists():
                print(f"{DIM}Moon Dev note: Farside fetch thin ({len(rows)} rows), using cached CSV{RESET}")
                rows = None
            else:
                raise RuntimeError(f"Moon Dev alert: Farside via jina returned only {len(rows)} rows and no cache exists!")
        if rows:
            pd.DataFrame(rows).to_csv(CACHE, index=False)
    df = pd.read_csv(CACHE)
    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y")
    return df.set_index("date").sort_index()

def fetch_sosovalue():
    """Last ~300 days: flow + value traded + AUM."""
    status("fetching SoSoValue flows/AUM")
    r = SESSION.post("https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart",
                      json={"type": "us-btc-spot"}, timeout=TIMEOUT)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["data"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    df["flow_m"] = df["totalNetInflow"] / 1e6
    df["traded_b"] = df["totalValueTraded"] / 1e9
    df["aum_b"] = df["totalNetAssets"] / 1e9
    return df[["flow_m", "traded_b", "aum_b"]]

def fetch_btc_closes(start):
    """Coinbase daily closes, paginated (300 candles max per request)."""
    status("fetching BTC daily candles from Coinbase")
    out = []
    t0 = pd.Timestamp(start)
    now = pd.Timestamp.utcnow().tz_localize(None)  # freeze once: no degenerate final chunk
    while t0 < now:
        t1 = min(t0 + pd.Timedelta(days=290), now)
        r = SESSION.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                        params={"granularity": 86400, "start": t0.isoformat(), "end": t1.isoformat()},
                        headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        out += r.json()
        t0 = t1
        time.sleep(0.35)  # stay polite, Coinbase throttles bursts at the connection level
    candles = pd.DataFrame(out, columns=["time", "low", "high", "open", "close", "vol"]).drop_duplicates("time")
    candles["date"] = pd.to_datetime(candles["time"], unit="s").dt.normalize()
    return candles.set_index("date")["close"]

def live_ibit_read(btc_daily_closes, soso):
    """
    Moon Dev's early-warning read: tonight's flow print in $M, estimated DURING the
    session. The estimator is a small OLS model re-fit on every run against the REAL
    historical daily flows (the same bars charted below), using three live-computable
    features: yesterday's flow (streaks persist), today's BTC move (flows chase
    price), and IBIT premium x sector volume (AP creation/redemption pressure).
    IBIT ~60% of sector AUM -> its tape leads the aggregate print.
    """
    status("fetching live IBIT from Yahoo")
    r = SESSION.get("https://query1.finance.yahoo.com/v8/finance/chart/IBIT",
                    params={"interval": "1d", "range": "6mo"}, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    chart = r.json()["chart"]["result"][0]
    meta, quote = chart["meta"], chart["indicators"]["quote"][0]
    dates = pd.to_datetime(chart["timestamp"], unit="s").normalize()
    ibit = pd.DataFrame({"close": quote["close"], "volume": quote["volume"]}, index=dates).dropna()

    spot = SESSION.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker",
                       headers=UA, timeout=TIMEOUT).json()
    btc_now = float(spot["price"])
    ibit_now = meta["regularMarketPrice"]

    hist = ibit.iloc[:-1]  # completed sessions only
    ratios = hist["close"].tail(10) / hist.index[-10:].map(btc_daily_closes)
    premium_bps = (ibit_now / btc_now / ratios.median() - 1) * 10_000

    reg = meta["currentTradingPeriod"]["regular"]
    now = meta["regularMarketTime"]
    frac = min(max((now - reg["start"]) / (reg["end"] - reg["start"]), 0.02), 1.0)
    session_open = reg["start"] <= now < reg["end"]
    vol_today = ibit["volume"].iloc[-1]
    pace = vol_today / (hist["volume"].tail(20).mean() * frac)

    # ---- calibrate flow model on history (real bars, re-fit every run) ----
    d = ibit.copy()
    d["btc"] = d.index.map(btc_daily_closes)
    ratio = d["close"] / d["btc"]
    d["prem"] = (ratio / ratio.rolling(10).median().shift(1) - 1) * 10_000
    d["ibit_dvol_b"] = d["close"] * d["volume"] / 1e9
    d = d.join(soso[["flow_m", "traded_b"]])
    d["flow_lag"] = d["flow_m"].shift(1)
    d["btc_ret"] = d["btc"].pct_change() * 100
    d["press"] = d["prem"] * d["traded_b"]
    fit = d.iloc[:-1][["flow_m", "flow_lag", "btc_ret", "press"]].dropna()
    X = np.column_stack([np.ones(len(fit)), fit["flow_lag"], fit["btc_ret"], fit["press"]])
    beta, *_ = np.linalg.lstsq(X, fit["flow_m"].values, rcond=None)
    resid = fit["flow_m"].values - X @ beta
    r2 = 1 - (resid ** 2).sum() / ((fit["flow_m"] - fit["flow_m"].mean()) ** 2).sum()
    rmse = float(np.sqrt((resid ** 2).mean()))

    ibit_share = (d["ibit_dvol_b"] / d["traded_b"]).tail(20).median()
    sector_traded_proj = (vol_today / frac * ibit_now / 1e9) / ibit_share
    x_live = np.array([1.0, soso["flow_m"].iloc[-1],
                       (btc_now / d["btc"].iloc[-2] - 1) * 100,
                       premium_bps * sector_traded_proj])
    est_m = float(x_live @ beta)
    est_btc = est_m * 1e6 / btc_now
    ecolor = GREEN if est_m >= 0 else RED

    print(f"{BOLD}⚡ LIVE READ — tonight's ETF flow print, estimated now "
          f"({'session OPEN' if session_open else 'market closed, projecting last session'}){RESET}")
    print(f"  {ecolor}{BOLD}EST FLOW ≈ {est_m:+,.0f}M{RESET}{ecolor} = ~{est_btc:+,.0f} BTC "
          f"{'bought' if est_m >= 0 else 'sold'}{RESET} {DIM}(± {rmse:,.0f}M model error, "
          f"R² {r2:.2f} on {len(fit)} sessions){RESET}")
    print(f"  drivers: yesterday {soso['flow_m'].iloc[-1]:+,.0f}M | BTC {x_live[2]:+.1f}% today | "
          f"IBIT {premium_bps:+.0f}bps vs NAV on {pace:.1f}x volume pace")
    print(f"  {DIM}model estimate, not a measurement — official print lands ~6-10pm ET{RESET}\n")

def bar(flow, scale):
    n = min(int(abs(flow) / scale * BAR_WIDTH), BAR_WIDTH) if scale else 0
    if flow >= 0:
        return " " * BAR_WIDTH + DIM + "|" + RESET + GREEN + "█" * n + RESET + " " * (BAR_WIDTH - n)
    return " " * (BAR_WIDTH - n) + RED + "█" * n + RESET + DIM + "|" + RESET + " " * BAR_WIDTH

# ---- assemble the window ----
soso = fetch_sosovalue()
if DAYS <= len(soso):
    flows = soso.tail(DAYS).copy()
else:
    flows = fetch_farside_full()
    flows = flows.join(soso[["traded_b", "aum_b"]])  # traded/AUM only where SoSoValue reaches
    flows = flows.tail(DAYS).copy()

btc = fetch_btc_closes(min(flows.index[0], soso.index[0]) - pd.Timedelta(days=5))
flows["btc_close"] = flows.index.map(btc)

weekly = len(flows) > WEEKLY_THRESHOLD
if weekly:
    flows = pd.DataFrame({
        "flow_m": flows["flow_m"].resample("W-FRI").sum(),
        "traded_b": flows["traded_b"].resample("W-FRI").sum(min_count=1) if "traded_b" in flows else None,
        "aum_b": flows["aum_b"].resample("W-FRI").last() if "aum_b" in flows else None,
        "btc_close": flows["btc_close"].resample("W-FRI").last(),
        "n_days": flows["flow_m"].resample("W-FRI").count(),
    }).dropna(subset=["n_days"])
    flows = flows[flows["n_days"] > 0]

scale = flows["flow_m"].abs().max()
unit = "week" if weekly else "session"

print()
live_ibit_read(btc, soso)

print(f"{BOLD}🌙 BTC ETF FLOWS — {len(flows)} {unit}s ({flows.index[0]:%b %d %Y} → {flows.index[-1]:%b %d %Y}) — Moon Dev{RESET}")
print(f"{DIM}Farside/SoSoValue + Coinbase | {'WEEKLY bars (Fri-ending)' if weekly else 'daily bars'} | "
      f"bar scale ±${scale:,.0f}M | $M flow, $B traded/AUM{RESET}\n")

datew = 9 if weekly else 6
print(BOLD + f"{'DATE':<{datew}} {'BTC':>7}  {'◄':>{BAR_WIDTH}} {'►':<{BAR_WIDTH}} {'FLOW':>8} {'TRD':>4} {'AUM':>5}" + RESET)
rule = DIM + "─" * (datew + BAR_WIDTH * 2 + 30) + RESET

prev_period = None
for date, row in flows.iterrows():
    period = date.strftime("%Y-%m") if weekly else date.weekday() == 0
    if weekly:
        if prev_period and period != prev_period and date.month in (1, 4, 7, 10):
            print(rule)  # quarter breaks in weekly mode
        prev_period = period
    elif period:
        print(rule)
    px = f"{row.btc_close/1000:,.1f}k" if pd.notna(row.btc_close) else "?"
    color = GREEN if row.flow_m >= 0 else RED
    label = date.strftime("%d%b%y") if weekly else date.strftime("%b %d")
    trd = f"{row.traded_b:>4,.1f}" if "traded_b" in row and pd.notna(row.traded_b) else "   -"
    aum = f"{row.aum_b:>5,.1f}" if "aum_b" in row and pd.notna(row.aum_b) else "    -"
    print(f"{label:<{datew}} {px:>7}  {bar(row.flow_m, scale)} {color}{row.flow_m:>+8,.0f}{RESET} {trd} {aum}")

# ---- Moon Dev's summary ----
last = flows.iloc[-1]
streak_sign = 1 if last.flow_m >= 0 else -1
streak = 0
for f in reversed(flows["flow_m"].tolist()):
    if (1 if f >= 0 else -1) != streak_sign:
        break
    streak += 1

green = (flows["flow_m"] >= 0).sum()
print(f"""
{BOLD}MOON DEV'S READ{RESET}
  Latest ......... {GREEN if last.flow_m >= 0 else RED}{last.flow_m:+,.0f}M{RESET} ({flows.index[-1]:%b %d}) | streak: {streak} {'green' if streak_sign > 0 else 'red'} {unit}(s)
  Last 5 / 20 .... {flows['flow_m'].tail(5).sum():+,.0f}M / {flows['flow_m'].tail(20).sum():+,.0f}M
  Window ......... {flows['flow_m'].sum():+,.0f}M ({green}/{len(flows)} green)
  Worst / best ... {flows['flow_m'].min():+,.0f}M {flows['flow_m'].idxmin():%b %d %y} / {flows['flow_m'].max():+,.0f}M {flows['flow_m'].idxmax():%b %d %y}

  Trigger: green AND holding while forced sellers empty = thin-supply setup. 🌙
""")
```
### Want to build this live with us?

We walk through tools like this on our live Zoom calls. Come hang out, ask questions, and build alongside the Moon Dev community.

[Join the Live Zoom Call](https://moondev.com/t/blog/btc-etf-flow-tracker)

Built with love by Moon Dev

### Related Resources

[HIP3 Funding Rate Scanner](https://moondev.com/hip-3-funding-rate-scanner)

— Scan every funding rate on Hyperliquid, crypto and HIP3 assets

[HIP3 Liquidation Trading Bot](https://moondev.com/hip-3-liquidation-trading-bot)

— Trade liquidation cascades on HIP3 automatically

[Market Data Portal](https://moondev.com/data)

— Funding rates, open interest, liquidations, and more

[Moon Dev Roadmap](https://moondev.com/roadmap)

— More open source code from the videos
