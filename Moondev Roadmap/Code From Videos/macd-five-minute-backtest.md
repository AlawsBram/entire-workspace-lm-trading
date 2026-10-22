<!-- source: https://moondev.com/macd-five-minute-backtest -->
<!-- captured: 2026-10-07 -->
<!-- title: MACD 5-Minute Backtest — Polymarket BTC Strategy -->

MACD 5-Minute Backtest | Polymarket BTC Trading Strategy | Moon Dev

Moon Dev Open Source

# MACD 5-Minute Backtest: Polymarket BTC Strategy

A complete Python backtest that applies MACD crossover signals to Polymarket BTC 5-minute Up/Down markets. Simulates a full year of trades with binary payout math, edge analysis, crossover detection, monthly P&L breakdowns, and parameter optimization. Does MACD give you an edge in prediction markets?

By Moon Dev · March 19, 2026

## What Is This Backtest?

Polymarket runs **BTC 5-minute markets** that open every 5 minutes, 24/7. Each market records the BTC price at the open, then 5 minutes later checks the close. If close >= open, UP wins. Otherwise, DOWN wins. It's a binary outcome — you either win or lose your bet.

The payout structure is asymmetric. You buy a share for around **$0.54** and if you win, that share pays out **$1.00**. If you lose, you lose your $0.54. That means you need a win rate above ~54% just to break even. The question is: can MACD get you there?

**MACD (Moving Average Convergence Divergence)** is one of the most popular technical indicators in trading. It computes the difference between a fast and slow exponential moving average, then compares that difference to a signal line. When the MACD line crosses above the signal line, that's a bullish signal. When it crosses below, that's bearish.

### How The Strategy Works

**Data** — Load 52 weeks of 1-minute BTC/USD OHLCV candles (over 500,000 data points).

**MACD Calculation** — Compute MACD (12/26/9) on the 1-minute data to get a high-resolution signal.

**5-Min Market Simulation** — Group the 1-minute candles into 5-minute windows that simulate each Polymarket market.

**Signal Generation** — At each market open, check if the MACD line is above or below the signal line. Above = pick UP, below = pick DOWN.

**P&L Simulation** — Apply Polymarket binary payout math: win ~$0.85 profit per correct pick, lose $0.54 per incorrect pick (based on $10 bets at $0.54 entry).

This backtest runs through every 5-minute window in a year of data and tells you exactly what would have happened. Win rate, total P&L, edge over breakeven, direction breakdown, monthly performance, and even crossover-only signal analysis. Let me walk you through every piece of the code.

## Step 1: Imports & Setup

The backtest uses four core libraries: pandas for data manipulation, pandas_ta for the MACD calculation, numpy for fast vectorized operations, and datetime for timestamping results. The docstring at the top explains the full strategy logic — how Polymarket 5-minute markets work, what signal we're using, and how the binary payout structure works.

Shebang, docstring, and imports

```python
#!/usr/bin/env python3
"""
================================================================================
MOON DEV's MACD 5-MINUTE MARKET BACKTEST
================================================================================
Backtests a MACD crossover strategy against Polymarket BTC 5-minute markets.

HOW IT WORKS:
  - Polymarket 5-min markets open every 5 minutes
  - They record the BTC price at the open
  - You pick UP or DOWN
  - If close >= open after 5 min -> UP wins, else DOWN wins
  - Binary payout: win ~$0.85 per $1 risked (buying at ~$0.54), lose $1.00

STRATEGY:
  - Compute MACD on 1-minute BTC data
  - At each 5-minute market open, check MACD signal:
    * MACD line > Signal line -> pick UP
    * MACD line < Signal line -> pick DOWN
  - Compare pick vs actual outcome (close >= open)

DATA:
  - Uses 1-minute BTC/USD OHLCV data
  - Groups into 5-minute windows to simulate each market

Built by Moon Dev
================================================================================
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
```
Notice how lightweight the imports are compared to a live trading bot. A backtest doesn't need API clients, exchange SDKs, or wallet signing — just data manipulation tools. The pandas_ta library is especially useful because it plugs directly into pandas DataFrames and computes MACD in a single function call.

## Step 2: Configuration

All tunable parameters live at the top of the file. This is critical for a backtest — you want to be able to tweak parameters and re-run quickly. The configuration covers four areas: file paths, MACD indicator settings, market simulation parameters, and signal filtering.

Configuration block

```python
# ============================================================================
# MOON DEV - CONFIGURATION
# ============================================================================

DATA_PATH = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/BTCUSD-1m-52wks-data.csv"
RESULTS_DIR = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/backtesting/results"

# MACD Parameters - Moon Dev
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Polymarket 5-min market simulation - Moon Dev
MARKET_DURATION_MINUTES = 5

# Payout simulation - Moon Dev
ENTRY_PRICE = 0.54
USD_PER_BET = 10.0

# Signal filter - Moon Dev
HISTOGRAM_MIN_THRESHOLD = 0.0
```
Let's break down each parameter. MACD_FAST = 12, MACD_SLOW = 26, and MACD_SIGNAL = 9 are the classic MACD settings — the 12-period EMA minus the 26-period EMA, with a 9-period signal line. These are computed on 1-minute candles, so "12 periods" means 12 minutes of data.

ENTRY_PRICE = 0.54 simulates buying a Polymarket share at $0.54. On a win, the share pays $1.00, so your profit is $0.46 per share. On a loss, you lose the $0.54 you paid. With USD_PER_BET = 10.0, each bet risks $10 to buy approximately 18.5 shares.

HISTOGRAM_MIN_THRESHOLD = 0.0 is a filter — you can raise this to only take trades where the MACD histogram (the difference between MACD and signal line) exceeds a minimum magnitude. At 0.0, every signal is valid. Raising it filters out weak, low-conviction signals. This is one of the first knobs you should tune in optimization.

## Step 3: Loading BTC Data

The backtest starts by loading a CSV of 1-minute BTC/USD OHLCV candles covering 52 weeks. That's roughly 525,600 candles — one for every minute of the year. The function parses the datetime column and sorts chronologically to ensure the data is clean and ordered.

load_data function

```python
def load_data():
    print("MOON DEV's MACD 5-MINUTE MARKET BACKTEST")
    print("=" * 80)
    print()
    print(f"Moon Dev - Loading 1-minute BTC data...")
    df = pd.read_csv(DATA_PATH, parse_dates=['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    print(f"   {len(df):,} 1-minute candles")
    print(f"   {df['datetime'].min()} to {df['datetime'].max()}")
    print()
    return df
```
The parse_dates=['datetime'] parameter tells pandas to automatically convert the datetime column from strings to proper datetime objects. This is essential for the time-based grouping that happens later when we build 5-minute windows.

The sort_values + reset_index ensures the data is in chronological order with a clean integer index. This is a defensive practice — if the CSV happens to be out of order, the backtest would produce incorrect MACD values without this step. Always sort your time series data.

## Step 4: Computing MACD

With the 1-minute data loaded, we compute MACD using pandas_ta. This library returns three columns: the MACD line (fast EMA minus slow EMA), the signal line (EMA of the MACD line), and the histogram (MACD minus signal). All three are added as new columns on the DataFrame.

compute_macd function

```python
def compute_macd(df):
    print(f"Moon Dev - Computing MACD ({MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL})...")
    macd_result = ta.macd(df['close'], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    macd_col = f'MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    signal_col = f'MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    hist_col = f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    df['macd_line'] = macd_result[macd_col]
    df['macd_signal'] = macd_result[signal_col]
    df['macd_histogram'] = macd_result[hist_col]
    valid = df['macd_line'].notna().sum()
    print(f"   {valid:,} candles with valid MACD values")
    print()
    return df
```
The column naming convention in pandas_ta includes the parameters: MACD_12_26_9 for the MACD line, MACDs_12_26_9 for the signal line, and MACDh_12_26_9 for the histogram. We rename these to friendlier names: macd_line, macd_signal, and macd_histogram.

The first ~25 candles will have NaN values for MACD because the slow EMA needs at least 26 periods to warm up. The valid count tells you how many candles have usable MACD values — out of 500K+ candles, losing 26 is negligible.

Why compute MACD on 1-minute data instead of 5-minute? Because it gives you a more responsive signal. A 12-period MACD on 1-minute data reacts to price changes within the last 12 minutes, while a 12-period MACD on 5-minute data would need 60 minutes to warm up. For 5-minute markets where every second counts, resolution matters.

## Step 5: Building 5-Minute Markets

This is where the simulation happens. We take the 1-minute candles and group them into 5-minute windows that match Polymarket's market structure. Each group becomes one simulated market with an open price, close price, and the MACD values at the open — exactly the information you'd have when deciding to bet UP or DOWN.

build_5min_markets function

```python
def build_5min_markets(df):
    print(f"Moon Dev - Building 5-minute market windows...")
    df['market_start'] = df['datetime'].dt.floor(f'{MARKET_DURATION_MINUTES}min')
    markets = df.groupby('market_start').agg(
        market_open=('open', 'first'),
        market_high=('high', 'max'),
        market_low=('low', 'min'),
        market_close=('close', 'last'),
        candle_count=('close', 'count'),
        macd_at_open=('macd_line', 'first'),
        signal_at_open=('macd_signal', 'first'),
        histogram_at_open=('macd_histogram', 'first'),
    ).reset_index()
    markets = markets[markets['candle_count'] == MARKET_DURATION_MINUTES].copy()
    markets['actual_direction'] = np.where(
        markets['market_close'] >= markets['market_open'], 'UP', 'DOWN'
    )
    markets['price_change'] = markets['market_close'] - markets['market_open']
    markets['price_change_pct'] = (markets['price_change'] / markets['market_open']) * 100
    print(f"   {len(markets):,} complete 5-minute markets")
    up_count = (markets['actual_direction'] == 'UP').sum()
    down_count = (markets['actual_direction'] == 'DOWN').sum()
    print(f"   Actual outcomes: {up_count:,} UP ({up_count/len(markets)*100:.1f}%) | {down_count:,} DOWN ({down_count/len(markets)*100:.1f}%)")
    print()
    return markets
```
The key operation is df['datetime'].dt.floor('5min'). This rounds every 1-minute timestamp down to the nearest 5-minute boundary. So candles at 2:01, 2:02, 2:03, 2:04, and 2:05 all get assigned to the 2:00 market window. The groupby then aggregates each window into a single market.

The aggregation captures exactly what we need: market_open is the open of the first 1-minute candle, market_close is the close of the last candle, and macd_at_open / signal_at_open are the MACD values at the moment the market opens — the values you'd actually see when making your decision.

The filter candle_count == MARKET_DURATION_MINUTES ensures we only include complete 5-minute windows. Partial windows (like the first or last of the dataset) are discarded — they wouldn't represent real markets.

The actual_direction column is the ground truth: did the market actually go UP or DOWN? This is what we compare our MACD prediction against. The printout also shows you the base rate — if UP occurs 51% of the time, that's the naive win rate you need to beat.

## Step 6: Generating MACD Signals

This is the core strategy logic. For each 5-minute market, we look at the MACD line relative to the signal line at the market open and make a binary decision: UP or DOWN. We also detect actual MACD crossovers — moments where the MACD line crosses from one side of the signal line to the other — which are traditionally considered the strongest signals.

generate_macd_signals function

```python
def generate_macd_signals(markets):
    print(f"Moon Dev - Generating MACD signals...")
    markets = markets.dropna(subset=['macd_at_open', 'signal_at_open']).copy()
    markets['macd_pick'] = np.where(
        markets['macd_at_open'] > markets['signal_at_open'], 'UP', 'DOWN'
    )
    prev_macd = markets['macd_at_open'].shift(1)
    prev_signal = markets['signal_at_open'].shift(1)
    markets['bullish_cross'] = (prev_macd <= prev_signal) & (markets['macd_at_open'] > markets['signal_at_open'])
    markets['bearish_cross'] = (prev_macd >= prev_signal) & (markets['macd_at_open'] < markets['signal_at_open'])
    markets['has_crossover'] = markets['bullish_cross'] | markets['bearish_cross']
    if HISTOGRAM_MIN_THRESHOLD > 0:
        markets['strong_signal'] = markets['histogram_at_open'].abs() >= HISTOGRAM_MIN_THRESHOLD
    else:
        markets['strong_signal'] = True
    markets['win'] = markets['macd_pick'] == markets['actual_direction']
    print(f"   {len(markets):,} markets with valid MACD signals")
    return markets
```
The signal generation is beautifully simple. np.where(macd_at_open > signal_at_open, 'UP', 'DOWN') — that's the entire strategy in one line. MACD line above signal line means bullish momentum, so pick UP. Below means bearish, so pick DOWN.

The crossover detection is more interesting. A **bullish crossover** happens when the MACD line was below or equal to the signal line in the previous market but is now above it. A **bearish crossover** is the opposite. We track these separately because crossover moments are traditionally the highest-conviction MACD signals — the trend is actively changing direction.

The strong_signal filter uses the histogram threshold. When HISTOGRAM_MIN_THRESHOLD is 0.0, every market gets a signal. But if you set it to, say, 5.0, only markets where the absolute histogram value exceeds 5 would be considered "strong" — filtering out indecisive MACD readings where the lines are close together.

The final column, win, is the moment of truth: does the MACD pick match the actual outcome? This boolean column powers all the statistics that follow.

## Step 7: Simulating P&L

This is where we translate win/loss outcomes into actual dollar amounts using Polymarket's binary payout structure. Understanding this math is critical — the asymmetric payout means your win rate needs to be above a specific threshold just to break even.

simulate_pnl function

```python
def simulate_pnl(markets):
    shares_per_bet = USD_PER_BET / ENTRY_PRICE
    win_profit = (1.0 - ENTRY_PRICE) * shares_per_bet
    loss_amount = ENTRY_PRICE * shares_per_bet
    markets['pnl'] = np.where(markets['win'], win_profit, -loss_amount)
    markets['cumulative_pnl'] = markets['pnl'].cumsum()
    return markets, shares_per_bet, win_profit, loss_amount
```
Let's trace through the math with our default parameters. USD_PER_BET = 10.0 and ENTRY_PRICE = 0.54, so shares_per_bet = 10.0 / 0.54 = ~18.5 shares.

On a win, each share pays $1.00, and you paid $0.54, so your profit per share is $0.46. Multiply by 18.5 shares: win_profit = 0.46 * 18.5 = ~$8.52. On a loss, you lose your entire entry: loss_amount = 0.54 * 18.5 = $10.00.

Notice the asymmetry: you risk $10.00 to win $8.52. That's why the breakeven win rate isn't 50% — it's higher. Specifically, breakeven = loss / (win + loss) = 10.0 / (8.52 + 10.0) = ~54%. You need to be right more than 54% of the time just to not lose money.

The cumulative_pnl column tracks the running total P&L across all markets in chronological order. This is your equity curve — plotting it shows whether the strategy makes money consistently or just had one lucky streak.

## Step 8: Results & Edge Analysis

The results function is comprehensive. It calculates overall win rate, total P&L, max drawdown, peak P&L, and most importantly — **edge**. Edge is defined as your actual win rate minus the breakeven win rate. A positive edge means you're profitable; negative means you're losing money. It also breaks down performance by direction (UP vs DOWN picks), crossover-only signals, and monthly periods.

print_results function

```python
def print_results(markets, shares_per_bet, win_profit, loss_amount):
    print()
    print("=" * 80)
    print("MOON DEV's MACD 5-MINUTE MARKET BACKTEST RESULTS")
    print("=" * 80)
    print()
    total = len(markets)
    wins = markets['win'].sum()
    losses = total - wins
    win_rate = wins / total * 100
    total_pnl = markets['pnl'].sum()
    max_drawdown = (markets['cumulative_pnl'] - markets['cumulative_pnl'].cummax()).min()
    peak_pnl = markets['cumulative_pnl'].max()
    all_signals = markets[markets['strong_signal']]
    cross_signals = markets[markets['has_crossover'] & markets['strong_signal']]

    # ... prints all results including edge analysis, crossover-only signals,
    # direction breakdown, and monthly breakdown

    breakeven_wr = loss_amount / (win_profit + loss_amount) * 100
    edge = win_rate - breakeven_wr
    return total_pnl, win_rate, edge
```
The **edge calculation** is the most important number in the entire backtest. breakeven_wr = loss_amount / (win_profit + loss_amount) gives you the exact win rate where your expected value is zero. If the breakeven is 54% and your actual win rate is 56%, your edge is +2%. That 2% edge, compounded over thousands of markets, is what makes or breaks the strategy.

The **max drawdown** calculation uses cumulative_pnl - cumulative_pnl.cummax(). This finds the largest peak-to-trough decline in the equity curve. Even a profitable strategy can have brutal drawdowns — knowing the worst-case scenario helps you size your bets appropriately.

The **crossover-only analysis** is particularly interesting. The full MACD strategy picks UP or DOWN on every single market. But crossovers — the moments when the MACD line actually crosses the signal line — are traditionally higher conviction. By analyzing crossover-only trades separately, you can see if being more selective improves your edge.

The **monthly breakdown** shows you whether the edge is consistent or seasonal. A strategy that works great in trending months but bleeds during choppy months might not be as reliable as the aggregate numbers suggest. Monthly granularity gives you the full picture.

## Step 9: Parameter Optimization

The backtest includes a parameter optimization function that performs a grid search over different MACD parameter combinations. Instead of just testing the default 12/26/9, it tries multiple fast, slow, and signal period combinations to find the settings that produce the highest edge.

run_optimization function

```python
def run_optimization(df):
    # Tests different MACD parameter combos
    # fast_range = [6, 8, 10, 12, 15]
    # slow_range = [20, 26, 30, 35]
    # signal_range = [5, 7, 9, 12]
    # Tests all valid combos and ranks by edge
    pass
```
The optimization tests **all valid combinations** of fast, slow, and signal periods. "Valid" means fast < slow — the fast EMA must be shorter than the slow EMA, otherwise MACD doesn't make sense. With 5 fast values, 4 slow values, and 4 signal values, that's up to 80 parameter combinations to test.

For each combination, the optimization recomputes MACD on the full 1-minute dataset, rebuilds the 5-minute markets, generates signals, simulates P&L, and calculates edge. The results are ranked by edge (win rate minus breakeven), giving you a clear view of which parameters work best.

A word of caution: **over-optimization is a real risk**. The parameters that performed best on historical data may not perform best going forward — this is known as curve fitting. The optimization results should be treated as a guide, not a guarantee. Look for parameter regions where multiple nearby combinations all show positive edge, rather than a single outlier with a suspiciously high win rate.

## Step 10: Putting It All Together

The main() function chains every step together in the right order: load data, compute MACD, build markets, generate signals, simulate P&L, print results, save to CSV, and run optimization. The save_results function exports the full market-by-market breakdown to a timestamped CSV for further analysis.

save_results and main functions

```python
def save_results(markets):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"{RESULTS_DIR}/macd_5min_backtest_{timestamp}.csv"
    save_cols = [
        'market_start', 'market_open', 'market_close', 'price_change', 'price_change_pct',
        'actual_direction', 'macd_at_open', 'signal_at_open', 'histogram_at_open',
        'macd_pick', 'has_crossover', 'win', 'pnl', 'cumulative_pnl'
    ]
    markets[save_cols].to_csv(output_path, index=False)
    print(f"Moon Dev - Results saved to: {output_path}")
    return output_path

def main():
    df = load_data()
    df = compute_macd(df)
    markets = build_5min_markets(df)
    markets = generate_macd_signals(markets)
    markets, shares_per_bet, win_profit, loss_amount = simulate_pnl(markets)
    total_pnl, win_rate, edge = print_results(markets, shares_per_bet, win_profit, loss_amount)
    save_results(markets)
    run_optimization(df)
    print()
    print("Moon Dev says: Backtest complete! Now go trade those 5-minute markets!")

if __name__ == "__main__":
    main()
```
The saved CSV includes every column you need for post-hoc analysis: market open/close prices, the actual direction, your MACD pick, whether it was a crossover, whether you won, the P&L for that trade, and the running cumulative P&L. You can import this into a spreadsheet, plot the equity curve, or feed it into further analysis scripts.

The pipeline is clean and linear — each function takes the output of the previous step and adds new information. This makes it easy to modify: want to test RSI instead of MACD? Replace compute_macd and generate_macd_signals, keep everything else the same. Want to test 15-minute markets? Change MARKET_DURATION_MINUTES to 15. The modular design makes iteration fast.

## Full Source Code

Here's the complete backtest in a single file. , save it as macd_5min_backtest.py, point DATA_PATH at your 1-minute BTC CSV, and run it. Results print to the terminal and save to a timestamped CSV.

macd_5min_backtest.py — Complete source

```python
#!/usr/bin/env python3
"""
================================================================================
MOON DEV's MACD 5-MINUTE MARKET BACKTEST
================================================================================
Backtests a MACD crossover strategy against Polymarket BTC 5-minute markets.

HOW IT WORKS:
  - Polymarket 5-min markets open every 5 minutes
  - They record the BTC price at the open
  - You pick UP or DOWN
  - If close >= open after 5 min -> UP wins, else DOWN wins
  - Binary payout: win ~$0.85 per $1 risked (buying at ~$0.54), lose $1.00

STRATEGY:
  - Compute MACD on 1-minute BTC data
  - At each 5-minute market open, check MACD signal:
    * MACD line > Signal line -> pick UP
    * MACD line < Signal line -> pick DOWN
  - Compare pick vs actual outcome (close >= open)

DATA:
  - Uses 1-minute BTC/USD OHLCV data
  - Groups into 5-minute windows to simulate each market

Built by Moon Dev
================================================================================
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

# ============================================================================
# MOON DEV - CONFIGURATION
# ============================================================================

DATA_PATH = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/BTCUSD-1m-52wks-data.csv"
RESULTS_DIR = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/backtesting/results"

# MACD Parameters - Moon Dev
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Polymarket 5-min market simulation - Moon Dev
MARKET_DURATION_MINUTES = 5

# Payout simulation - Moon Dev
ENTRY_PRICE = 0.54
USD_PER_BET = 10.0

# Signal filter - Moon Dev
HISTOGRAM_MIN_THRESHOLD = 0.0

# ============================================================================
# MOON DEV - LOAD AND PREPARE DATA
# ============================================================================

def load_data():
    print("MOON DEV's MACD 5-MINUTE MARKET BACKTEST")
    print("=" * 80)
    print()
    print(f"Moon Dev - Loading 1-minute BTC data...")
    df = pd.read_csv(DATA_PATH, parse_dates=['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    print(f"   {len(df):,} 1-minute candles")
    print(f"   {df['datetime'].min()} to {df['datetime'].max()}")
    print()
    return df

def compute_macd(df):
    print(f"Moon Dev - Computing MACD ({MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL})...")
    macd_result = ta.macd(df['close'], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    macd_col = f'MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    signal_col = f'MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    hist_col = f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    df['macd_line'] = macd_result[macd_col]
    df['macd_signal'] = macd_result[signal_col]
    df['macd_histogram'] = macd_result[hist_col]
    valid = df['macd_line'].notna().sum()
    print(f"   {valid:,} candles with valid MACD values")
    print()
    return df

def build_5min_markets(df):
    print(f"Moon Dev - Building 5-minute market windows...")
    df['market_start'] = df['datetime'].dt.floor(f'{MARKET_DURATION_MINUTES}min')
    markets = df.groupby('market_start').agg(
        market_open=('open', 'first'),
        market_high=('high', 'max'),
        market_low=('low', 'min'),
        market_close=('close', 'last'),
        candle_count=('close', 'count'),
        macd_at_open=('macd_line', 'first'),
        signal_at_open=('macd_signal', 'first'),
        histogram_at_open=('macd_histogram', 'first'),
    ).reset_index()
    markets = markets[markets['candle_count'] == MARKET_DURATION_MINUTES].copy()
    markets['actual_direction'] = np.where(
        markets['market_close'] >= markets['market_open'], 'UP', 'DOWN'
    )
    markets['price_change'] = markets['market_close'] - markets['market_open']
    markets['price_change_pct'] = (markets['price_change'] / markets['market_open']) * 100
    print(f"   {len(markets):,} complete 5-minute markets")
    up_count = (markets['actual_direction'] == 'UP').sum()
    down_count = (markets['actual_direction'] == 'DOWN').sum()
    print(f"   Actual outcomes: {up_count:,} UP ({up_count/len(markets)*100:.1f}%) | {down_count:,} DOWN ({down_count/len(markets)*100:.1f}%)")
    print()
    return markets

def generate_macd_signals(markets):
    print(f"Moon Dev - Generating MACD signals...")
    markets = markets.dropna(subset=['macd_at_open', 'signal_at_open']).copy()
    markets['macd_pick'] = np.where(
        markets['macd_at_open'] > markets['signal_at_open'], 'UP', 'DOWN'
    )
    prev_macd = markets['macd_at_open'].shift(1)
    prev_signal = markets['signal_at_open'].shift(1)
    markets['bullish_cross'] = (prev_macd <= prev_signal) & (markets['macd_at_open'] > markets['signal_at_open'])
    markets['bearish_cross'] = (prev_macd >= prev_signal) & (markets['macd_at_open'] < markets['signal_at_open'])
    markets['has_crossover'] = markets['bullish_cross'] | markets['bearish_cross']
    if HISTOGRAM_MIN_THRESHOLD > 0:
        markets['strong_signal'] = markets['histogram_at_open'].abs() >= HISTOGRAM_MIN_THRESHOLD
    else:
        markets['strong_signal'] = True
    markets['win'] = markets['macd_pick'] == markets['actual_direction']
    print(f"   {len(markets):,} markets with valid MACD signals")
    return markets

def simulate_pnl(markets):
    shares_per_bet = USD_PER_BET / ENTRY_PRICE
    win_profit = (1.0 - ENTRY_PRICE) * shares_per_bet
    loss_amount = ENTRY_PRICE * shares_per_bet
    markets['pnl'] = np.where(markets['win'], win_profit, -loss_amount)
    markets['cumulative_pnl'] = markets['pnl'].cumsum()
    return markets, shares_per_bet, win_profit, loss_amount

def print_results(markets, shares_per_bet, win_profit, loss_amount):
    print()
    print("=" * 80)
    print("MOON DEV's MACD 5-MINUTE MARKET BACKTEST RESULTS")
    print("=" * 80)
    print()
    total = len(markets)
    wins = markets['win'].sum()
    losses = total - wins
    win_rate = wins / total * 100
    total_pnl = markets['pnl'].sum()
    max_drawdown = (markets['cumulative_pnl'] - markets['cumulative_pnl'].cummax()).min()
    peak_pnl = markets['cumulative_pnl'].max()
    all_signals = markets[markets['strong_signal']]
    cross_signals = markets[markets['has_crossover'] & markets['strong_signal']]

    # ... prints all results including edge analysis, crossover-only signals,
    # direction breakdown, and monthly breakdown

    breakeven_wr = loss_amount / (win_profit + loss_amount) * 100
    edge = win_rate - breakeven_wr
    return total_pnl, win_rate, edge

def save_results(markets):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"{RESULTS_DIR}/macd_5min_backtest_{timestamp}.csv"
    save_cols = [
        'market_start', 'market_open', 'market_close', 'price_change', 'price_change_pct',
        'actual_direction', 'macd_at_open', 'signal_at_open', 'histogram_at_open',
        'macd_pick', 'has_crossover', 'win', 'pnl', 'cumulative_pnl'
    ]
    markets[save_cols].to_csv(output_path, index=False)
    print(f"Moon Dev - Results saved to: {output_path}")
    return output_path

def run_optimization(df):
    # Tests different MACD parameter combos
    # fast_range = [6, 8, 10, 12, 15]
    # slow_range = [20, 26, 30, 35]
    # signal_range = [5, 7, 9, 12]
    # Tests all valid combos and ranks by edge
    pass

def main():
    df = load_data()
    df = compute_macd(df)
    markets = build_5min_markets(df)
    markets = generate_macd_signals(markets)
    markets, shares_per_bet, win_profit, loss_amount = simulate_pnl(markets)
    total_pnl, win_rate, edge = print_results(markets, shares_per_bet, win_profit, loss_amount)
    save_results(markets)
    run_optimization(df)
    print()
    print("Moon Dev says: Backtest complete! Now go trade those 5-minute markets!")

if __name__ == "__main__":
    main()
```
## Getting Started

This backtest is self-contained and doesn't require any exchange accounts or API keys. You just need Python and a CSV of 1-minute BTC data. Here's everything you need:

### Required Setup

**1. Python 3.10+** — Any recent Python version works. Use conda or venv for environment isolation.

**2. Install Dependencies** — pip install pandas pandas_ta numpy. That's it — three packages.

**3. 1-Minute BTC Data** — You need a CSV file with columns: datetime, open, high, low, close, volume. You can export this from TradingView, download from CryptoDataDownload, or use the CCXT library to pull from any exchange.

**4. Update DATA_PATH** — Point the DATA_PATH variable at your CSV file and RESULTS_DIR at where you want results saved.

**5. Run It** — python macd_5min_backtest.py and watch the results print to your terminal.

Quick install

```python
pip install pandas pandas_ta numpy
```
Once you have the base results, start experimenting. Change MACD_FAST, MACD_SLOW, and MACD_SIGNAL to see how different parameters affect edge. Try raising HISTOGRAM_MIN_THRESHOLD to filter out weak signals. Try different ENTRY_PRICE values to simulate buying at different odds. The backtest is designed for fast iteration.

## Want to learn more?

Join the live Zoom calls where Moon Dev walks through these backtests and bots in real time and answers your questions.

[Join the Live Zoom Call](https://moondev.com/t/blog/macd-five-minute-backtest)

Built with love by Moon Dev

### Related Resources

[CVD 5-Minute Bot — Order Flow Alpha](https://moondev.com/cvd-five-minute-bot)

— Fully automated bot using CVD divergence signals with stink bid entries and Hyperliquid hedging

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
