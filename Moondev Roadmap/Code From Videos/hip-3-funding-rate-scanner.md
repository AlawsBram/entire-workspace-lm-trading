<!-- source: https://moondev.com/hip-3-funding-rate-scanner -->
<!-- captured: 2026-10-07 -->
<!-- title: HIP-3 Funding Rate Scanner -->

HIP3 Funding Rate Scanner for Hyperliquid | Open Source Python Tool | Moon Dev

Moon Dev Open Source

# Wall Street Doesn't Have This: A Funding Rate Scanner for Every HIP3 Asset

Funding rates are crypto's secret weapon. They don't exist in traditional markets. Now that HIP3 lets you trade oil, gold, silver, stocks, and more on Hyperliquid — you can exploit funding rates on assets where nobody else is looking. This scanner shows you every single one.

By Moon Dev · March 8, 2026

⚠️ Heads up (updated Aug 13, 2026)

[The /api/hlp/funding and /api/hlp/funding/hip3 endpoints used in this article were retired on 2026-08-13 and now return HTTP 410. The concepts and scanner structure below still apply, but for live data use the supported /api/hlp/sentiment and /api/hlp/positions endpoints — see the [API docs](/docs)

.

## What Are Funding Rates (And Why Wall Street Doesn't Have Them)

In traditional finance, if you want to go long oil or short gold, you're dealing with futures contracts that expire on specific dates. There's no mechanism for the market to self-balance in real time. You buy the contract, you hold it until expiry or roll it, that's it.

Crypto invented something different: **perpetual futures**. These contracts never expire. But to keep the price of a perpetual future tethered to the actual spot price, exchanges use a mechanism called the **funding rate**.

Here's how it works: every 8 hours (on Hyperliquid, sometimes every hour), one side of the trade pays the other. If funding is **positive**, longs pay shorts. If funding is **negative**, shorts pay longs. The rate is determined by the imbalance between buyers and sellers.

When too many people are long, the funding rate goes positive — meaning longs are paying a fee to shorts just to hold their position. This is a signal: the market is crowded on one side. When funding is extremely negative, the opposite is true — shorts are paying a premium.

### Why This Matters for HIP3

HIP3 brought traditional assets — crude oil, gold, silver, Tesla, Nvidia, the S&P 500 — onto Hyperliquid as perpetual futures. That means these assets now have **funding rates** for the first time ever. Wall Street traders looking at crude oil don't see funding rates. Stock traders don't see funding rates. But you do, because you're looking at these assets through a crypto-native lens. This is an informational edge that simply doesn't exist in traditional markets. You're seeing crowd positioning data on oil, gold, and stocks that Bloomberg terminals can't show you.

This scanner pulls every single funding rate from Hyperliquid — both crypto perps and HIP3 tokenized assets — and displays them in a clean table so you can spot where the crowd is leaning. Let me walk you through how it works.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-funding-rate-scanner)

## Step 1: The Imports

The scanner is completely self contained. One file, standard Python packages. Requests handles the API calls, pandas formats the data into tables, colorama makes the terminal output readable with colors, and dotenv loads your API key securely.

Imports and path setup

```python
#!/usr/bin/env python3
"""
Moon Dev's Funding Rate Scanner

Scans ALL Hyperliquid funding rates (both crypto perps and HIP3 tokenized assets)
and displays them in a clean pandas table. Loops every 5 minutes.

Built by Moon Dev
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import colorama
import pandas as pd
import requests
from colorama import Fore
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

colorama.init(autoreset=True)
load_dotenv()
```
The ROOT_DIR setup adds the project root to your Python path. This way you can run the script from any directory and it still finds your .env file. If you're running it standalone, just make sure your .env is in the same folder.

## Step 2: The Configuration

Three settings control the scanner's behavior. The API base URL, how often it scans, and the minimum open interest filter. The OI filter is important — it weeds out low-liquidity assets where the funding rate might look extreme but there's nobody actually trading it.

Configuration

```python
# ===== CONFIG =====
BASE_URL = "https://api.moondev.com"
LOOP_INTERVAL_SECONDS = 5 * 60  # 5 minutes
MIN_OI_VALUE = 5_000_000  # Minimum Open Interest value filter ($5M)

MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}Funding Rate Scanner{Fore.RESET}
{Fore.YELLOW}Scan all Hyperliquid funding rates - Crypto & HIP3{Fore.RESET}
"""
```
MIN_OI_VALUE is set to $5 million by default. This means the scanner will only show you assets where at least $5M of open interest exists. If a random HIP3 asset has a 50% annualized funding rate but only $10k in OI, that's noise, not signal. Crank this number up or down depending on how aggressive you want to filter.

The loop runs every 5 minutes by default. Funding rates don't change every second — they're calculated on longer intervals — so 5 minutes gives you a real-time-enough view without hammering the API.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-funding-rate-scanner)

## Step 3: API Authentication

Simple auth header builder. Your Moon Dev API key lives in your .env file and gets passed as a header on every request.

Auth headers

```python
def _auth_headers():
    """Moon Dev API auth headers"""
    api_key = os.getenv("MOONDEV_API_KEY")
    return {"X-API-Key": api_key} if api_key else {}
```
[If you don't have a Moon Dev API key yet, grab one at [moondev.com/docs](https://moondev.com/docs)

. The funding rate endpoints require authentication.

## Step 4: Fetching the Funding Rates

Two functions, two endpoints. One pulls funding rates for all crypto perpetuals (BTC, ETH, SOL, etc.). The other pulls funding rates for all HIP3 tokenized assets (oil, gold, silver, stocks). Same API, different data universes.

Fetch functions

```python
def fetch_crypto_funding():
    """Fetch funding rates for all crypto perps"""
    print(f"{Fore.CYAN}Moon Dev fetching crypto perp funding rates...")
    response = requests.get(
        f"{BASE_URL}/api/hlp/funding",
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def fetch_hip3_funding():
    """Fetch funding rates for all HIP3 tokenized assets"""
    print(f"{Fore.CYAN}Moon Dev fetching HIP3 funding rates...")
    response = requests.get(
        f"{BASE_URL}/api/hlp/funding/hip3",
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
```
The /api/hlp/funding endpoint returns crypto perps only. The /api/hlp/funding/hip3 endpoint returns HIP3 tokenized assets only. Both return the same data structure — symbol, rate, annualized percentage, mark price, and open interest.

This is where the magic happens. That HIP3 endpoint is giving you funding rate data on assets like xyz:GOLD, xyz:BRENTOIL, cash:TSLA. Data that literally does not exist in traditional finance. Nobody on the CME can see this.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-funding-rate-scanner)

## Step 5: Parsing the Data into a DataFrame

The API response comes back as JSON with an all_rates dictionary. This function converts it into a clean pandas DataFrame that's easy to sort, filter, and display.

Parse rates to DataFrame

```python
def parse_rates_to_df(data, source_label):
    """Parse funding rate data into a pandas DataFrame"""
    rates = data.get("all_rates", [])

    if not rates:
        if isinstance(data, list):
            rates = data
        else:
            for key in ["current_rates", "rates", "data"]:
                if key in data and data[key]:
                    rates = data[key]
                    break

    if not rates:
        print(f"{Fore.YELLOW}Warning: No rates found in {source_label} response")
        print(f"{Fore.YELLOW}   Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return pd.DataFrame()

    if isinstance(rates, dict):
        # Convert dict of {symbol: rate_info} to list
        rows = []
        for symbol, info in rates.items():
            if isinstance(info, dict):
                info["coin"] = symbol
                rows.append(info)
            else:
                rows.append({"coin": symbol, "rate_pct": info})
        rates = rows

    df = pd.DataFrame(rates)
    df["source"] = source_label
    return df
```
The function handles multiple response formats defensively. The Moon Dev API returns all_rates as a dictionary where each key is a symbol (like xyz:GOLD) and each value contains the rate data. The function flattens this into rows for pandas.

The source column tags each row as either "crypto" or "hip3" so you can filter by category later if you want.

## Step 6: Standardizing Column Names

The API response uses snake_case field names. This utility function renames them to human-readable headers and ensures the numeric columns are actually numeric types so pandas can sort them properly.

Standardize DataFrame

```python
def _standardize_df(df):
    """Standardize column names and numeric types"""
    col_map = {}
    for col in df.columns:
        lower = col.lower()
        if "coin" in lower or "symbol" in lower or "name" in lower:
            col_map[col] = "Symbol"
        elif "rate_pct" in lower or ("rate" in lower and "annual" not in lower and "yearly" not in lower):
            col_map[col] = "Rate %"
        elif "annual" in lower or "yearly" in lower:
            col_map[col] = "Annualized %"
        elif "mark" in lower and "price" in lower:
            col_map[col] = "Mark Price"
        elif "oi" in lower or "open_interest" in lower:
            col_map[col] = "OI Value"

    df = df.rename(columns=col_map)
    for c in ["Rate %", "Annualized %"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df
```
This is a quality of life function. Instead of reading rate_pct and oi_value in your terminal output, you see clean headers like "Rate %" and "OI Value". Small thing, but when you're scanning 200+ assets every 5 minutes, readability matters.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-funding-rate-scanner)

## Step 7: Displaying the Results

This is the main output function. It takes a DataFrame of funding rates, applies the OI filter, sorts by rate, and shows the top 30 highest and top 30 most negative funding rates. Color coded so you can spot opportunities instantly.

Display top and bottom funding rates

```python
def display_top_bottom(df, label):
    """Show top 30 highest and top 30 lowest funding for a category"""
    df = _standardize_df(df.copy())

    if "Rate %" not in df.columns:
        print(f"{Fore.YELLOW}No Rate % column for {label}")
        return

    df = df.dropna(subset=["Rate %"]).sort_values("Rate %", ascending=False)
    display_cols = [c for c in ["Symbol", "Rate %", "Annualized %", "OI Value"] if c in df.columns]

    # OI filter - only show assets with OI >= MIN_OI_VALUE
    if "OI Value" in df.columns:
        df["OI Value"] = pd.to_numeric(df["OI Value"], errors="coerce")
        before_count = len(df)
        df = df[df["OI Value"] >= MIN_OI_VALUE]
        print(f"{Fore.YELLOW}OI Filter: {before_count} -> {len(df)} assets (min OI: ${MIN_OI_VALUE:,.0f})")

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda x: f"{x:.6f}" if abs(x) < 1 else f"{x:.2f}")

    top_pos = df.head(30)
    top_neg = df.tail(30).sort_values("Rate %", ascending=True)

    print(f"\n{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.MAGENTA}  Moon Dev | {label} TOP 30 HIGHEST FUNDING")
    print(f"{Fore.GREEN}{'=' * 70}")
    print(top_pos[display_cols].to_string(index=False))

    print(f"\n{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.MAGENTA}  Moon Dev | {label} TOP 30 MOST NEGATIVE FUNDING")
    print(f"{Fore.GREEN}{'=' * 70}")
    print(top_neg[display_cols].to_string(index=False))
    print(f"{Fore.GREEN}{'=' * 70}")
```
The MIN_OI_VALUE filter is doing the real work here. Before displaying anything, it drops every asset with less than $5M in open interest. This is critical. A HIP3 asset could show -70% annualized funding, but if there's only $50k in OI, that rate is meaningless — there's no liquidity to actually trade it.

You get two tables per category: the top 30 highest funding (longs paying shorts — crowd is heavily long) and the top 30 most negative (shorts paying longs — crowd is heavily short). These extremes are where the opportunities live.

## Step 8: The Scan Function

This ties everything together. One function that fetches both crypto and HIP3 funding rates, parses them, and displays the results. Clean and simple.

Main scan function

```python
def scan():
    """Run one full funding rate scan"""
    print(f"\n{Fore.CYAN}{'=' * 90}")
    print(f"{Fore.YELLOW}  Moon Dev Funding Rate Scan | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'=' * 90}")

    # Fetch crypto perps
    crypto_data = fetch_crypto_funding()
    crypto_df = parse_rates_to_df(crypto_data, "crypto")

    # Fetch HIP3 tokenized assets
    hip3_data = fetch_hip3_funding()
    hip3_df = parse_rates_to_df(hip3_data, "hip3")

    # Show top 30 high & top 30 low for each category
    for label, df in [("Crypto Perps", crypto_df), ("HIP3 Tokenized", hip3_df)]:
        if df.empty:
            continue
        display_top_bottom(df, label)

    print(f"{Fore.YELLOW}Scan complete. Next scan in {LOOP_INTERVAL_SECONDS // 60} minutes.\n")
```
Each scan hits two endpoints and builds two separate tables. The crypto perps table shows you things like BTC, ETH, SOL, HYPE — the usual suspects. The HIP3 table shows you gold, oil, silver, Tesla, Nvidia, the S&P 500 — the stuff that Wall Street is trading without this data.

When you see something like xyz:BRENTOIL with +26% annualized funding, that means longs are paying an aggressive premium to hold their oil position on Hyperliquid. That's information no one on the CME or NYMEX has access to. That's your edge.

[Join tomorrow's live Zoom call here](https://moondev.com/t/blog/hip-3-funding-rate-scanner)

## Step 9: The Main Loop

The entry point runs one scan immediately on startup, then loops every 5 minutes. It prints the Moon Dev banner, kicks off the first scan, and runs until you hit Ctrl+C.

Main loop

```python
if __name__ == "__main__":
    print(MOON_DEV_BANNER)
    print(f"{Fore.GREEN}Moon Dev Funding Rate Scanner starting...")
    print(f"{Fore.YELLOW}   Scanning every {LOOP_INTERVAL_SECONDS // 60} minutes. Press Ctrl+C to stop.\n")

    scan()
    while True:
        time.sleep(LOOP_INTERVAL_SECONDS)
        scan()
```
That's the entire scanner. Run it, leave it in a terminal tab, and you've got a live dashboard of every funding rate on Hyperliquid. When you see an extreme rate on an HIP3 asset, you know the crowd is leaning hard in one direction — and that's information most traders in that market simply don't have.

## Running the Scanner

Set up your .env file with your Moon Dev API key and you're good to go.

.env file

```python
MOONDEV_API_KEY=your_moondev_api_key
```
Install dependencies and run

```python
pip install requests pandas python-dotenv colorama
python funding_rate_scanner.py
```
Every 5 minutes you'll see four tables in your terminal: top 30 highest crypto funding, top 30 most negative crypto funding, top 30 highest HIP3 funding, and top 30 most negative HIP3 funding. All filtered by OI so you're only seeing assets with real liquidity.

## Full Source Code

Here's the complete scanner in one block if you just want to grab it and go.

funding_rate_scanner.py (full)

```python
#!/usr/bin/env python3
"""
Moon Dev's Funding Rate Scanner

Scans ALL Hyperliquid funding rates (both crypto perps and HIP3 tokenized assets)
and displays them in a clean pandas table. Loops every 5 minutes.

Built by Moon Dev
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import colorama
import pandas as pd
import requests
from colorama import Fore
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

colorama.init(autoreset=True)
load_dotenv()

# ===== CONFIG =====
BASE_URL = "https://api.moondev.com"
LOOP_INTERVAL_SECONDS = 5 * 60  # 5 minutes
MIN_OI_VALUE = 5_000_000  # Minimum Open Interest value filter ($5M)

MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}Funding Rate Scanner{Fore.RESET}
{Fore.YELLOW}Scan all Hyperliquid funding rates - Crypto & HIP3{Fore.RESET}
"""

def _auth_headers():
    """Moon Dev API auth headers"""
    api_key = os.getenv("MOONDEV_API_KEY")
    return {"X-API-Key": api_key} if api_key else {}

def fetch_crypto_funding():
    """Fetch funding rates for all crypto perps"""
    print(f"{Fore.CYAN}Moon Dev fetching crypto perp funding rates...")
    response = requests.get(
        f"{BASE_URL}/api/hlp/funding",
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def fetch_hip3_funding():
    """Fetch funding rates for all HIP3 tokenized assets"""
    print(f"{Fore.CYAN}Moon Dev fetching HIP3 funding rates...")
    response = requests.get(
        f"{BASE_URL}/api/hlp/funding/hip3",
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def parse_rates_to_df(data, source_label):
    """Parse funding rate data into a pandas DataFrame"""
    rates = data.get("all_rates", [])

    if not rates:
        if isinstance(data, list):
            rates = data
        else:
            for key in ["current_rates", "rates", "data"]:
                if key in data and data[key]:
                    rates = data[key]
                    break

    if not rates:
        print(f"{Fore.YELLOW}Warning: No rates found in {source_label} response")
        print(f"{Fore.YELLOW}   Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return pd.DataFrame()

    if isinstance(rates, dict):
        rows = []
        for symbol, info in rates.items():
            if isinstance(info, dict):
                info["coin"] = symbol
                rows.append(info)
            else:
                rows.append({"coin": symbol, "rate_pct": info})
        rates = rows

    df = pd.DataFrame(rates)
    df["source"] = source_label
    return df

def _standardize_df(df):
    """Standardize column names and numeric types"""
    col_map = {}
    for col in df.columns:
        lower = col.lower()
        if "coin" in lower or "symbol" in lower or "name" in lower:
            col_map[col] = "Symbol"
        elif "rate_pct" in lower or ("rate" in lower and "annual" not in lower and "yearly" not in lower):
            col_map[col] = "Rate %"
        elif "annual" in lower or "yearly" in lower:
            col_map[col] = "Annualized %"
        elif "mark" in lower and "price" in lower:
            col_map[col] = "Mark Price"
        elif "oi" in lower or "open_interest" in lower:
            col_map[col] = "OI Value"

    df = df.rename(columns=col_map)
    for c in ["Rate %", "Annualized %"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def display_top_bottom(df, label):
    """Show top 30 highest and top 30 lowest funding for a category"""
    df = _standardize_df(df.copy())

    if "Rate %" not in df.columns:
        print(f"{Fore.YELLOW}No Rate % column for {label}")
        return

    df = df.dropna(subset=["Rate %"]).sort_values("Rate %", ascending=False)
    display_cols = [c for c in ["Symbol", "Rate %", "Annualized %", "OI Value"] if c in df.columns]

    # OI filter - only show assets with OI >= MIN_OI_VALUE
    if "OI Value" in df.columns:
        df["OI Value"] = pd.to_numeric(df["OI Value"], errors="coerce")
        before_count = len(df)
        df = df[df["OI Value"] >= MIN_OI_VALUE]
        print(f"{Fore.YELLOW}OI Filter: {before_count} -> {len(df)} assets (min OI: ${MIN_OI_VALUE:,.0f})")

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda x: f"{x:.6f}" if abs(x) < 1 else f"{x:.2f}")

    top_pos = df.head(30)
    top_neg = df.tail(30).sort_values("Rate %", ascending=True)

    print(f"\n{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.MAGENTA}  Moon Dev | {label} TOP 30 HIGHEST FUNDING")
    print(f"{Fore.GREEN}{'=' * 70}")
    print(top_pos[display_cols].to_string(index=False))

    print(f"\n{Fore.GREEN}{'=' * 70}")
    print(f"{Fore.MAGENTA}  Moon Dev | {label} TOP 30 MOST NEGATIVE FUNDING")
    print(f"{Fore.GREEN}{'=' * 70}")
    print(top_neg[display_cols].to_string(index=False))
    print(f"{Fore.GREEN}{'=' * 70}")

def scan():
    """Run one full funding rate scan"""
    print(f"\n{Fore.CYAN}{'=' * 90}")
    print(f"{Fore.YELLOW}  Moon Dev Funding Rate Scan | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.CYAN}{'=' * 90}")

    # Fetch crypto perps
    crypto_data = fetch_crypto_funding()
    crypto_df = parse_rates_to_df(crypto_data, "crypto")

    # Fetch HIP3 tokenized assets
    hip3_data = fetch_hip3_funding()
    hip3_df = parse_rates_to_df(hip3_data, "hip3")

    # Show top 30 high & top 30 low for each category
    for label, df in [("Crypto Perps", crypto_df), ("HIP3 Tokenized", hip3_df)]:
        if df.empty:
            continue
        display_top_bottom(df, label)

    print(f"{Fore.YELLOW}Scan complete. Next scan in {LOOP_INTERVAL_SECONDS // 60} minutes.\n")

if __name__ == "__main__":
    print(MOON_DEV_BANNER)
    print(f"{Fore.GREEN}Moon Dev Funding Rate Scanner starting...")
    print(f"{Fore.YELLOW}   Scanning every {LOOP_INTERVAL_SECONDS // 60} minutes. Press Ctrl+C to stop.\n")

    scan()
    while True:
        time.sleep(LOOP_INTERVAL_SECONDS)
        scan()
```
### Want to build this live with us?

We walk through tools like this on our live Zoom calls. Come hang out, ask questions, and build alongside the Moon Dev community.

[Join the Live Zoom Call](https://moondev.com/t/blog/hip-3-funding-rate-scanner)

Built with love by Moon Dev

### Related Resources

[HIP3 Liquidation Trading Bot](https://moondev.com/hip-3-liquidation-trading-bot)

— Trade liquidation cascades on HIP3 automatically

[Moon Dev API Documentation](https://moondev.com/docs)

— HIP3 funding rates, liquidation data, position snapshots, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations across exchanges

[Market Data Portal](https://moondev.com/data)

— Funding rates, open interest, and more
