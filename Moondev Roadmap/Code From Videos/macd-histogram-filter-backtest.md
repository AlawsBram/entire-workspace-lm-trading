<!-- source: https://moondev.com/macd-histogram-filter-backtest -->
<!-- captured: 2026-10-07 -->
<!-- title: MACD Histogram Filter Backtest — Signal Quality Filter -->

MACD Histogram Filter Backtest | Polymarket BTC Signal Quality | Moon Dev

Moon Dev Open Source

# MACD Histogram Filter Backtest

A Python backtest that adds a histogram strength threshold to MACD crossover signals, filtering out weak and noisy trades on Polymarket BTC 5-minute Up/Down markets. Tests 12 parameter combos to find the highest edge. Variation 2 of the MACD backtest series.

By Moon Dev · March 19, 2026

## What Is This Backtest?

[This is **Variation 2** of the MACD backtest series. The [base MACD backtest](https://moondev.com/macd-five-minute-backtest)

tested raw MACD crossover signals on Polymarket BTC 5-minute markets. It worked, but raw crossovers include a lot of noise — weak signals where the MACD line barely crosses the signal line, producing low-conviction trades.

The idea behind this variation is simple: **only trade when the MACD histogram absolute value exceeds a threshold**. The histogram is the difference between the MACD line and the signal line. When the histogram is large, the crossover has real momentum behind it. When the histogram is tiny, the crossover might just be random noise.

By requiring the histogram to exceed a minimum strength before taking a trade, we filter out the weak crossovers and only act on signals that have genuine momentum. The tradeoff is fewer trades — but the question is whether those remaining trades have a higher win rate and a better edge.

### The Core Hypothesis

**Problem** — Raw MACD crossovers fire too often. Many are weak, noisy, and low-conviction.

**Filter** — Use the absolute value of the MACD histogram as a quality gate. Only trade when |histogram| exceeds a threshold.

**Tradeoff** — Fewer total trades, but each trade should be higher quality. Signal quality vs quantity.

**Test** — Try thresholds of 1, 5, 10, 20, 50, and 100 across two MACD parameter sets to find the sweet spot.

This backtest runs against 52 weeks of 1-minute BTC candle data, grouping candles into 5-minute windows that match the Polymarket market structure. Let me walk you through every piece of the code.

## Step 1: Imports & Setup

The backtest starts with a detailed docstring that explains the hypothesis, lists the combos being tested, and gives credit. Then we import the four core libraries: pandas for data manipulation, pandas_ta for computing MACD indicators, numpy for vectorized comparisons, and datetime for timestamping the output file.

Shebang, docstring, and imports

```python
#!/usr/bin/env python3
"""
================================================================================
Moon Dev's MACD HISTOGRAM FILTER BACKTEST - Variation 2
================================================================================
Tests MACD + histogram threshold filter on Polymarket BTC 5-minute markets.

IDEA: Only trade when MACD histogram absolute value exceeds a threshold.
This filters out weak/noisy crossovers and should improve signal quality.

COMBOS TESTED:
  - MACD(6/20/5) with histogram thresholds: 1, 5, 10, 20, 50, 100
  - MACD(6/26/5) with histogram thresholds: 1, 5, 10, 20, 50, 100

Built by Moon Dev
================================================================================
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
```
Notice the shebang line #!/usr/bin/env python3 — this lets you run the script directly from the command line on macOS or Linux without prefixing python. The imports are minimal because this is a pure backtest — no API calls, no exchange connections, no real-time data. Everything runs locally against a CSV file.

## Step 2: Configuration

All tunable parameters live in a clean configuration block at the top. This is where you define the data path, the MACD parameter combos, the histogram thresholds to sweep, and the Polymarket payout structure. Changing any of these and re-running the script gives you a completely different backtest.

Configuration block

```python
# ============================================================================
# Moon Dev - CONFIGURATION
# ============================================================================

DATA_PATH = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/BTCUSD-1m-52wks-data.csv"
RESULTS_DIR = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/backtesting/results"

MARKET_DURATION_MINUTES = 5

# Polymarket payout structure - Moon Dev
ENTRY_PRICE = 0.54
USD_PER_BET = 10.0

# MACD parameter combos to test - Moon Dev
MACD_COMBOS = [
    (6, 20, 5),
    (6, 26, 5),
]

# Histogram thresholds to test - Moon Dev
HIST_THRESHOLDS = [1, 5, 10, 20, 50, 100]
```
Let's break down the key parameters. MACD_COMBOS defines two MACD configurations to test: (6, 20, 5) and (6, 26, 5). Each tuple is (fast_period, slow_period, signal_period). Both use a fast EMA of 6 and a signal period of 5, but the slow EMA differs — 20 vs 26. The 6/26/5 is closer to the traditional MACD(12/26/9) but with faster parameters tuned for 5-minute markets.

HIST_THRESHOLDS is the sweep array — we test six different histogram strength gates: 1, 5, 10, 20, 50, and 100. A threshold of 1 is barely filtering anything (almost every crossover will have a histogram larger than 1). A threshold of 100 is extremely strict — only the strongest momentum moves will pass. The question is: where is the sweet spot?

ENTRY_PRICE at $0.54 means we're buying Polymarket outcome tokens at 54 cents. If the market resolves YES, each token pays $1.00. If it resolves NO, the token is worth $0. This binary payout structure is what makes the breakeven math so important — and that's what comes next.

## Step 3: Payout Math

Before running a single trade, the backtest calculates the breakeven win rate. This is the most important number in any binary prediction market strategy — it tells you the minimum win rate required to avoid losing money. Every percentage point of win rate above breakeven is your **edge**.

Payout math and breakeven calculation

```python
    # Payout math - Moon Dev
    shares_per_bet = USD_PER_BET / ENTRY_PRICE
    win_profit = (1.0 - ENTRY_PRICE) * shares_per_bet
    loss_amount = ENTRY_PRICE * shares_per_bet
    breakeven_wr = loss_amount / (win_profit + loss_amount) * 100

    print(f"Moon Dev - Payout: win +${win_profit:.2f} | loss -${loss_amount:.2f} | breakeven WR: {breakeven_wr:.2f}%")
```
Here's the math. With $10 per bet at $0.54 per share, you buy 10 / 0.54 = 18.52 shares. If you **win**, each share pays $1.00, so profit is (1.00 - 0.54) * 18.52 = $8.52. If you **lose**, each share is worthless, so you lose your entire stake: 0.54 * 18.52 = $10.00.

The breakeven win rate is loss / (win + loss) = 10.00 / (8.52 + 10.00) = 54.0%. This makes sense — the entry price literally IS the implied probability. At $0.54, the market says there's a 54% chance of YES. To profit, your signal needs to be right more than 54% of the time.

The **edge** metric used throughout the results is simply win_rate - breakeven_wr. An edge of +2% means you're winning 56% of the time against a 54% breakeven — that's 2% of pure alpha. Small edges compound into serious profits over hundreds of trades.

## Step 4: Computing MACD for Each Combo

The outer loop iterates over each MACD parameter combination. For each combo, we compute the full MACD indicator on the raw 1-minute data using pandas_ta, which returns three columns: the MACD line, the signal line, and the histogram.

MACD computation loop

```python
    for fast, slow, signal in MACD_COMBOS:
        print(f"Moon Dev - Computing MACD({fast}/{slow}/{signal})...")

        macd_result = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
        macd_col = f'MACD_{fast}_{slow}_{signal}'
        signal_col = f'MACDs_{fast}_{slow}_{signal}'
        hist_col = f'MACDh_{fast}_{slow}_{signal}'

        df_temp = df.copy()
        df_temp['macd_line'] = macd_result[macd_col]
        df_temp['macd_signal'] = macd_result[signal_col]
        df_temp['macd_histogram'] = macd_result[hist_col]
```
pandas_ta returns a DataFrame with specifically named columns. For MACD(6, 20, 5), the columns are MACD_6_20_5, MACDs_6_20_5 (the signal), and MACDh_6_20_5 (the histogram). We construct these column names dynamically so the same code works for any parameter set.

The df.copy() is important — we don't want to pollute the original DataFrame when testing different MACD parameters. Each combo gets a fresh copy with its own indicator columns attached.

## Step 5: Building 5-Minute Markets

Polymarket BTC markets last exactly 5 minutes. To simulate this, we group the 1-minute candles into 5-minute windows using dt.floor(). Each group becomes a simulated market where we know the open price, close price, and the MACD values at the moment the market opened.

5-minute market construction

```python
        df_temp['market_start'] = df_temp['datetime'].dt.floor(f'{MARKET_DURATION_MINUTES}min')

        markets = df_temp.groupby('market_start').agg(
            market_open=('open', 'first'),
            market_close=('close', 'last'),
            candle_count=('close', 'count'),
            macd_at_open=('macd_line', 'first'),
            signal_at_open=('macd_signal', 'first'),
            histogram_at_open=('macd_histogram', 'first'),
        ).reset_index()

        markets = markets[markets['candle_count'] == MARKET_DURATION_MINUTES].copy()
        markets = markets.dropna(subset=['macd_at_open', 'signal_at_open', 'histogram_at_open'])

        markets['actual'] = np.where(markets['market_close'] >= markets['market_open'], 'UP', 'DOWN')

        print(f"  {len(markets):,} valid 5-min markets")
```
The dt.floor('5min') call rounds each timestamp down to the nearest 5-minute boundary. So candles at 10:01, 10:02, 10:03, 10:04 all get assigned to the 10:00 market. The groupby then aggregates each group: first open is the market open, last close is the market close, and the first MACD/signal/histogram values are what we'd see at market open time.

The filter candle_count == MARKET_DURATION_MINUTES drops incomplete windows (like the first and last of the dataset). The dropna removes markets where the MACD hadn't accumulated enough data yet (the first few markets in the dataset will have NaN indicators).

Finally, the actual column records the ground truth: did BTC go UP or DOWN in that 5-minute window? This is what we compare our signal against.

## Step 6: The Histogram Filter

This is the core innovation of Variation 2. The inner loop sweeps through each histogram threshold and filters the market set to only include markets where the histogram absolute value exceeds the threshold. This is the quality gate that separates strong momentum signals from noise.

Histogram threshold filter loop

```python
        for threshold in HIST_THRESHOLDS:
            filtered = markets[markets['histogram_at_open'].abs() > threshold].copy()

            if len(filtered) < 10:
                continue
```
The filter is one line: markets['histogram_at_open'].abs() > threshold. We use the absolute value because we care about the **magnitude** of the histogram, not its sign. A histogram of +50 (strong bullish) and -50 (strong bearish) are both high-conviction signals — we just need to trade in the right direction.

The minimum 10-trade guard (len(filtered) < 10) prevents us from drawing conclusions from tiny sample sizes. If a threshold of 100 only produces 3 trades in 52 weeks of data, the win rate is statistically meaningless — so we skip it.

As the threshold increases, fewer and fewer markets pass the filter. At threshold=1, almost every market passes (the histogram is almost always bigger than 1). At threshold=100, only the most explosive momentum moves survive. This creates a clear tradeoff curve: more trades with a weaker edge vs fewer trades with (hopefully) a stronger edge.

## Step 7: Signal Generation & Edge Calculation

For each market that passes the histogram filter, the signal is simple: if MACD line is above the signal line, pick UP. If MACD line is below, pick DOWN. Then we compare the pick to what actually happened and compute win rate, edge, and total P&L.

Signal generation and edge calculation

```python
            filtered['pick'] = np.where(
                filtered['macd_at_open'] > filtered['signal_at_open'], 'UP', 'DOWN'
            )
            filtered['win'] = filtered['pick'] == filtered['actual']

            trades = len(filtered)
            wins = filtered['win'].sum()
            win_rate = wins / trades * 100
            edge = win_rate - breakeven_wr
            total_pnl = wins * win_profit - (trades - wins) * loss_amount

            all_results.append({
                'fast': fast,
                'slow': slow,
                'signal_period': signal,
                'hist_threshold': threshold,
                'trades': trades,
                'wins': wins,
                'win_rate': round(win_rate, 2),
                'edge': round(edge, 2),
                'pnl': round(total_pnl, 2),
            })
```
[The signal logic is identical to the [base MACD backtest](https://moondev.com/macd-five-minute-backtest)

— MACD above signal means bullish, below means bearish. The difference is that we're only applying this logic to the **filtered** set of markets that passed the histogram strength test.

The edge calculation is the money line: win_rate - breakeven_wr. If your win rate is 56.5% and breakeven is 54.0%, your edge is +2.5%. That edge multiplied by the number of trades and the bet size gives you total P&L.

Each combo's results get appended to all_results. With 2 MACD combos and 6 thresholds, we get up to 12 rows (minus any skipped for insufficient sample size). This is the full parameter sweep.

## Step 8: Results Analysis

After all combos have been tested, the results are sorted by edge and filtered to show only the positive-edge configurations. This is where you find out which histogram thresholds actually improve signal quality, and which ones filter too aggressively or not aggressively enough.

Results analysis and output

```python
    print()
    print("=" * 80)
    print("Moon Dev's RESULTS - POSITIVE EDGE COMBOS ONLY")
    print("=" * 80)
    print()

    results_df = pd.DataFrame(all_results).sort_values('edge', ascending=False)

    positive = results_df[results_df['edge'] > 0]

    if len(positive) == 0:
        print("Moon Dev - No combos with positive edge found.")
    else:
        for _, row in positive.iterrows():
            print(f"MACD({row['fast']}/{row['slow']}/{row['signal_period']}) hist>{row['hist_threshold']} | "
                  f"Trades: {row['trades']} | WR: {row['win_rate']:.2f}% | "
                  f"Edge: +{row['edge']:.2f}% | P&L: ${row['pnl']:,.2f}")

    print()
    print(f"Moon Dev - {len(positive)} of {len(results_df)} combos have positive edge")
    print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"{RESULTS_DIR}/macd_variation_2_{timestamp}.csv"
    results_df.to_csv(output_path, index=False)
    print(f"Moon Dev - Results saved to: {output_path}")
    print()
    print("Moon Dev - Histogram filter backtest complete!")
```
The results DataFrame gets sorted by edge in descending order, so the best-performing combo appears first. Only positive-edge combos are printed to the console — these are the configurations that would have made money over the 52-week backtest period.

Each result line shows the MACD parameters, the histogram threshold, the number of trades, win rate, edge, and total P&L. This tells you everything at a glance: MACD(6/20/5) hist>10 | Trades: 5420 | WR: 55.12% | Edge: +1.12% | P&L: $480.00 means that MACD(6/20/5) with a histogram threshold of 10 produced 5,420 trades at a 55.12% win rate, beating the 54% breakeven by 1.12%.

The full results (including negative-edge combos) are saved to a timestamped CSV for later analysis. You can open this in Excel or pandas and visualize how edge changes as you increase the histogram threshold — the classic signal quality vs quantity curve.

## Full Source Code

Here's the complete backtest in a single file. , update DATA_PATH and RESULTS_DIR to your local paths, and run it. The entire backtest completes in seconds.

macd_histogram_filter_backtest.py — Complete source

```python
#!/usr/bin/env python3
"""
================================================================================
Moon Dev's MACD HISTOGRAM FILTER BACKTEST - Variation 2
================================================================================
Tests MACD + histogram threshold filter on Polymarket BTC 5-minute markets.

IDEA: Only trade when MACD histogram absolute value exceeds a threshold.
This filters out weak/noisy crossovers and should improve signal quality.

COMBOS TESTED:
  - MACD(6/20/5) with histogram thresholds: 1, 5, 10, 20, 50, 100
  - MACD(6/26/5) with histogram thresholds: 1, 5, 10, 20, 50, 100

Built by Moon Dev
================================================================================
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

# ============================================================================
# Moon Dev - CONFIGURATION
# ============================================================================

DATA_PATH = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/BTCUSD-1m-52wks-data.csv"
RESULTS_DIR = "/Users/md/Dropbox/dev/github/Polymarket-Trading-Bots/backtesting/results"

MARKET_DURATION_MINUTES = 5

# Polymarket payout structure - Moon Dev
ENTRY_PRICE = 0.54
USD_PER_BET = 10.0

# MACD parameter combos to test - Moon Dev
MACD_COMBOS = [
    (6, 20, 5),
    (6, 26, 5),
]

# Histogram thresholds to test - Moon Dev
HIST_THRESHOLDS = [1, 5, 10, 20, 50, 100]

# ============================================================================
# Moon Dev - MAIN BACKTEST
# ============================================================================

def main():
    print("=" * 80)
    print("Moon Dev's MACD HISTOGRAM FILTER BACKTEST - Variation 2")
    print("=" * 80)
    print()

    # Load data - Moon Dev
    print("Moon Dev - Loading 1-minute BTC data...")
    df = pd.read_csv(DATA_PATH, parse_dates=['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    print(f"  {len(df):,} candles loaded | {df['datetime'].min()} to {df['datetime'].max()}")
    print()

    # Payout math - Moon Dev
    shares_per_bet = USD_PER_BET / ENTRY_PRICE
    win_profit = (1.0 - ENTRY_PRICE) * shares_per_bet
    loss_amount = ENTRY_PRICE * shares_per_bet
    breakeven_wr = loss_amount / (win_profit + loss_amount) * 100

    print(f"Moon Dev - Payout: win +${win_profit:.2f} | loss -${loss_amount:.2f} | breakeven WR: {breakeven_wr:.2f}%")
    print()

    all_results = []

    for fast, slow, signal in MACD_COMBOS:
        print(f"Moon Dev - Computing MACD({fast}/{slow}/{signal})...")

        macd_result = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
        macd_col = f'MACD_{fast}_{slow}_{signal}'
        signal_col = f'MACDs_{fast}_{slow}_{signal}'
        hist_col = f'MACDh_{fast}_{slow}_{signal}'

        df_temp = df.copy()
        df_temp['macd_line'] = macd_result[macd_col]
        df_temp['macd_signal'] = macd_result[signal_col]
        df_temp['macd_histogram'] = macd_result[hist_col]

        df_temp['market_start'] = df_temp['datetime'].dt.floor(f'{MARKET_DURATION_MINUTES}min')

        markets = df_temp.groupby('market_start').agg(
            market_open=('open', 'first'),
            market_close=('close', 'last'),
            candle_count=('close', 'count'),
            macd_at_open=('macd_line', 'first'),
            signal_at_open=('macd_signal', 'first'),
            histogram_at_open=('macd_histogram', 'first'),
        ).reset_index()

        markets = markets[markets['candle_count'] == MARKET_DURATION_MINUTES].copy()
        markets = markets.dropna(subset=['macd_at_open', 'signal_at_open', 'histogram_at_open'])

        markets['actual'] = np.where(markets['market_close'] >= markets['market_open'], 'UP', 'DOWN')

        print(f"  {len(markets):,} valid 5-min markets")

        for threshold in HIST_THRESHOLDS:
            filtered = markets[markets['histogram_at_open'].abs() > threshold].copy()

            if len(filtered) < 10:
                continue

            filtered['pick'] = np.where(
                filtered['macd_at_open'] > filtered['signal_at_open'], 'UP', 'DOWN'
            )
            filtered['win'] = filtered['pick'] == filtered['actual']

            trades = len(filtered)
            wins = filtered['win'].sum()
            win_rate = wins / trades * 100
            edge = win_rate - breakeven_wr
            total_pnl = wins * win_profit - (trades - wins) * loss_amount

            all_results.append({
                'fast': fast,
                'slow': slow,
                'signal_period': signal,
                'hist_threshold': threshold,
                'trades': trades,
                'wins': wins,
                'win_rate': round(win_rate, 2),
                'edge': round(edge, 2),
                'pnl': round(total_pnl, 2),
            })

    print()
    print("=" * 80)
    print("Moon Dev's RESULTS - POSITIVE EDGE COMBOS ONLY")
    print("=" * 80)
    print()

    results_df = pd.DataFrame(all_results).sort_values('edge', ascending=False)

    positive = results_df[results_df['edge'] > 0]

    if len(positive) == 0:
        print("Moon Dev - No combos with positive edge found.")
    else:
        for _, row in positive.iterrows():
            print(f"MACD({row['fast']}/{row['slow']}/{row['signal_period']}) hist>{row['hist_threshold']} | "
                  f"Trades: {row['trades']} | WR: {row['win_rate']:.2f}% | "
                  f"Edge: +{row['edge']:.2f}% | P&L: ${row['pnl']:,.2f}")

    print()
    print(f"Moon Dev - {len(positive)} of {len(results_df)} combos have positive edge")
    print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"{RESULTS_DIR}/macd_variation_2_{timestamp}.csv"
    results_df.to_csv(output_path, index=False)
    print(f"Moon Dev - Results saved to: {output_path}")
    print()
    print("Moon Dev - Histogram filter backtest complete!")

if __name__ == "__main__":
    main()
```
## Key Takeaways

The histogram filter teaches a fundamental lesson about trading system design: **signal quality vs signal quantity is always a tradeoff**. Here's what to look for in the results:

### What the Results Tell You

**Low thresholds (1-5)** — Barely any filtering. You get almost as many trades as the base MACD strategy. If the edge improves even slightly, the filter is removing the worst noise without costing you much volume.

**Medium thresholds (10-20)** — The sweet spot for most strategies. Meaningful noise reduction while retaining enough trades for statistical significance. Watch for the edge peaking here.

**High thresholds (50-100)** — Aggressive filtering. Very few trades remain. The win rate might look great, but with only 20-50 trades over 52 weeks, the results are noisy. Be careful about overfitting to a small sample.

**Diminishing returns** — If edge peaks at threshold=10 and then drops at threshold=50, you've found the diminishing returns point. Beyond that threshold, you're filtering out good trades along with the noise.

The histogram is fundamentally a measure of **momentum conviction**. A large positive histogram means the MACD line is far above the signal line — the fast EMA is pulling away from the slow EMA with authority. A tiny histogram means the two lines are barely separated, which usually means the crossover is tentative and could easily reverse.

This same filtering concept applies beyond MACD. Any indicator that produces a continuous signal can be filtered by strength: RSI divergence filtered by magnitude, volume spikes filtered by multiple of average, Bollinger Band touches filtered by how far outside the band price went. The histogram filter is a template for improving any noisy signal.

## Getting Started

This backtest is self-contained and runs entirely offline. No API keys, no exchange accounts, no real money. Just Python and data.

### Requirements

**1. Python 3.10+** — Any recent Python version works. Use conda or venv for environment management.

**2. Install dependencies** — pip install pandas pandas_ta numpy

**3. BTC 1-minute candle data** — You need a CSV file with at least datetime, open, and close columns. The more data the better — 52 weeks gives you roughly 100,000+ 5-minute markets to backtest against.

**4. Update paths** — Change DATA_PATH to point to your CSV file and RESULTS_DIR to where you want results saved.

**5. Run it** — python macd_histogram_filter_backtest.py — results appear in seconds.

To extend this backtest, try adding more MACD combos to MACD_COMBOS, finer histogram thresholds (like 2, 3, 7, 15), or different entry prices. You can also modify the market duration to test 1-minute or 15-minute windows if your prediction market offers those.

## Want to learn more?

Join the Moon Dev community to discuss backtesting strategies, share results, and build better trading systems together.

[Visit Moon Dev](https://moondev.com)

Built with love by Moon Dev

### Related Resources

[MACD 5-Minute Backtest — Base Strategy](https://moondev.com/macd-five-minute-backtest)

— The original MACD crossover backtest that this variation builds upon

[CVD 5-Minute Bot — Order Flow Alpha](https://moondev.com/cvd-five-minute-bot)

— Fully automated bot using CVD divergence signals on Polymarket with Hyperliquid hedging

[Polymarket 5-Minute Bot — Easy Hyper Gambler](https://moondev.com/polymarket-five-minute-bot)

— The keyboard-controlled bot for manual BTC 5-minute market trading

[Polymarket Hyperliquid Liquidation Statistical Arbitrage](https://moondev.com/polymarket-hyperliquid-liquidation-statistical-arbitrage)

— Advanced bot using liquidation data to trade Polymarket and hedge on Hyperliquid

[Moon Dev API Documentation](https://moondev.com/docs)

— Tick data, liquidation data, funding rates, position snapshots, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations across exchanges
