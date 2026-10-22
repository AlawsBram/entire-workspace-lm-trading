<!-- source: https://moondev.com/xgboost-raw-candles-polymarket -->
<!-- captured: 2026-10-07 -->
<!-- title: XGBoost Raw Candle ML Model — Polymarket BTC 5-Min Pipeline -->

XGBoost Raw Candle ML Model for Polymarket BTC 5-Minute Markets | Moon Dev

Moon Dev Open Source

# XGBoost Raw Candle ML Model

A complete 3-script machine learning pipeline for Polymarket BTC 5-minute prediction markets. Step 1: prepare raw 1-minute data into 5-minute windows. Step 2: engineer features from backtest-proven signals. Step 3: train an XGBoost model on raw candle shapes — no indicators, just pure price action. Full Python code breakdown.

By Moon Dev · March 20, 2026

## What Is This Pipeline?

This is a **3-script ML pipeline** for Polymarket BTC 5-minute Up/Down markets. The goal is to predict whether BTC will go up or down in the next 5 minutes — and profit from it on Polymarket. Three approaches are combined into one pipeline:

**1. Data Prep** — Loads 1-minute BTC candles, groups every 5 consecutive candles into a single 5-minute window, and labels each window as UP (close >= open) or DOWN (close < open). This creates clean, labeled data ready for ML.

**2. Feature Engineering** — Computes backtest-proven indicators (MACD variants, EMA crossovers) from prior candles only. No future leakage. Only signals that have shown real edge in historical backtests make it into the feature set.

**3. XGBoost Raw Candles** — A completely different approach: instead of human-designed indicators, feed the model raw candle shapes (body size, wick percentages, volume ratios) and let it learn its own patterns. No MACD. No RSI. Just pure price action microstructure.

### Pipeline Overview

**Pipeline** — 3 scripts that build on each other: data prep → feature engineering → model training

**Philosophy** — Two approaches tested: human-designed indicators vs letting the model learn from raw candle microstructure

**Target** — Polymarket BTC 5-minute Up/Down markets at $0.54 entry (54% breakeven)

**No Leakage** — All features computed from PRIOR candles only. Time-series train/val/test split. No shuffling.

## Script 1 — Data Preparation

The first script is the foundation of the pipeline. It loads raw 1-minute OHLCV data for BTC/USD and groups every 5 consecutive candles into a single 5-minute window. Each window gets a label: 1 if close >= open (UP wins on Polymarket), 0 if close < open (DOWN wins). This matches the exact structure of Polymarket BTC 5-minute markets.

The logic is straightforward: load the CSV, sort by datetime, trim any leftover rows that don't fill a complete 5-candle group, then aggregate each group using first open, last close, max high, min low, and sum volume. The result is a clean DataFrame with one row per 5-minute window, ready for feature engineering.

data_prep.py — Complete source

```python
"""
Moon Dev's 5-Minute Window Data Preparation
================================================
Loads 1-min BTC/USD OHLCV data, groups into 5-minute windows,
labels UP/DOWN, and saves prepared dataset for ML models.

Author: Moon Dev
"""

import pandas as pd
import numpy as np
import os

# -- Paths -------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.join(SCRIPT_DIR, "BTCUSD-1m-200wks-data.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "prepared_5min_windows.csv")

def load_raw_data(path=RAW_DATA_PATH):
    """Load 1-min OHLCV CSV, parse dates, sort by time."""
    print("Moon Dev | Loading raw 1-min data...")
    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    print(f"   Loaded {len(df):,} rows | {df['datetime'].min()} to {df['datetime'].max()}")
    return df

def create_5min_windows(df):
    """
    Group every 5 consecutive 1-min candles into one 5-min window.
    Label: 1 if close >= open (UP wins), 0 if close < open (DOWN wins).
    """
    print("Moon Dev | Creating 5-minute windows...")

    # Number of complete 5-candle groups
    n_windows = len(df) // 5
    # Trim any leftover rows that don't fill a complete window
    trimmed = df.iloc[: n_windows * 5].copy()

    # Assign a group index to each row
    trimmed["window_id"] = np.arange(len(trimmed)) // 5

    windows = trimmed.groupby("window_id").agg(
        datetime=("datetime", "first"),
        open_price=("open", "first"),
        close_price=("close", "last"),
        high=("high", "max"),
        low=("low", "min"),
        volume=("volume", "sum"),
    ).reset_index(drop=True)

    # Label: 1 = UP (close >= open), 0 = DOWN
    windows["label"] = (windows["close_price"] >= windows["open_price"]).astype(int)

    return windows

def print_stats(windows):
    """Print summary statistics about the prepared windows."""
    total = len(windows)
    up = (windows["label"] == 1).sum()
    down = (windows["label"] == 0).sum()

    print("\n" + "=" * 60)
    print("Moon Dev | 5-Minute Window Stats")
    print("=" * 60)
    print(f"   Total windows:  {total:,}")
    print(f"   UP  (label=1):  {up:,}  ({100 * up / total:.1f}%)")
    print(f"   DOWN(label=0):  {down:,}  ({100 * down / total:.1f}%)")
    print(f"   Date range:     {windows['datetime'].min()} -> {windows['datetime'].max()}")
    print("=" * 60)

def main():
    print("\nMoon Dev's 5-Min Data Prep Starting...\n")

    df = load_raw_data()
    windows = create_5min_windows(df)
    print_stats(windows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    windows.to_csv(OUTPUT_PATH, index=False)
    print(f"\nMoon Dev | Saved {len(windows):,} windows -> {OUTPUT_PATH}")
    print("Moon Dev | Data prep complete!\n")

    return windows

if __name__ == "__main__":
    main()
```
Here is what each function does:

load_raw_data() loads the CSV with 1-minute BTC candles, parses the datetime column, and sorts by time. This ensures the data is in chronological order before grouping.

create_5min_windows() groups every 5 rows into one window. It takes the first open, last close, max high, min low, and sum of volume from each group. Any leftover rows that don't fill a complete 5-candle window are trimmed.

Labels are simple: 1 = UP (close >= open), 0 = DOWN (close < open). This directly maps to the Polymarket market outcome.

The output is a clean CSV saved to data/prepared_5min_windows.csv, ready to be consumed by the feature engineering script.

## Script 2 — Feature Engineering

The second script takes the prepared 5-minute windows and the original 1-minute data, then computes features from **prior candles only**. The key insight: only backtest-proven indicators are included. No random features, no noise, no filler — just the signals that demonstrated real edge in historical backtests.

The script starts with helper functions for computing indicators: ema() for exponential moving averages, rsi() for relative strength index, macd_histogram() for MACD histogram values, and atr() for average true range. These are all vectorized operations on the full 1-minute series.

The compute_1min_features() function builds only the proven signals: **MACD(3,15,3)** at 60.18% win rate, **MACD(4,16,3)** at 59.18% win rate, **MACD(6,20,5)** at 63.70% win rate, and **EMA(3,8) crossover** at 58.66% win rate. These all exceeded the 54% breakeven threshold in prior backtests.

The build_features() function samples these features at the candle BEFORE each window opens — specifically at row (i*5 - 1), the last 1-minute candle before the 5-minute window starts. This prevents any future data leakage. It also adds the hour as a time-based feature, since BTC behaves differently during different trading sessions.

The final feature list: macd_3_15_3, macd_4_16_3, macd_6_20_5, macd_6_26_5, ema3_vs_ema8, return_5, return_15, atr_14, and hour.

feature_engineering.py — Complete source

```python
"""
Moon Dev's Feature Engineering for 5-Min ML Models
=======================================================
Loads prepared 5-min windows + original 1-min data, builds features
from PRIOR candles only (no future leakage), and saves final dataset.

Imported by all model training scripts via:
    from feature_engineering import build_features

Author: Moon Dev
"""

import pandas as pd
import numpy as np
import os

# -- Paths -------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.join(SCRIPT_DIR, "BTCUSD-1m-200wks-data.csv")
WINDOWS_PATH = os.path.join(SCRIPT_DIR, "data", "prepared_5min_windows.csv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "features_dataset.csv")

# ===========================================================================
#  Helper: compute indicators on the full 1-min series (vectorized)
# ===========================================================================

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd_histogram(series, fast, slow, signal):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    return macd_line - signal_line

def atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ===========================================================================
#  Build all features on the 1-min dataframe, then sample at window boundaries
# ===========================================================================

def compute_1min_features(df):
    """
    Moon Dev - Compute ONLY the features that PROVED themselves in backtests.
    No noise. No filler. Just the signals with real edge.

    Backtest-proven signals:
      - MACD(3,15,3) histogram > 0 -> 60.18% WR, +$119K P&L
      - MACD(4,16,3) line vs signal -> 59.18% WR
      - MACD(6,20,5) histogram with thresholds -> 63.70% WR
      - EMA(3,8) crossover -> 58.66% WR
    """
    print("Moon Dev | Computing BACKTEST-PROVEN features only (no noise)...")

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # -- MACD variants (ALL proven in backtests) ------------------------------
    # #1 strategy: MACD(3,15,3) - 60.18% WR, +$119K
    df["macd_3_15_3"] = macd_histogram(close, 3, 15, 3)
    # #2 strategy: MACD(4,16,3) - 59.18% WR, +$100K
    df["macd_4_16_3"] = macd_histogram(close, 4, 16, 3)
    # #3 strategy: MACD(6,20,5) - 63.70% WR with thresholds
    df["macd_6_20_5"] = macd_histogram(close, 6, 20, 5)
    # MACD(6,26,5) - used in threshold variations
    df["macd_6_26_5"] = macd_histogram(close, 6, 26, 5)

    # -- EMA crossover (proven: 58.66% WR) ------------------------------------
    ema3 = ema(close, 3)
    ema8 = ema(close, 8)
    df["ema3_vs_ema8"] = ema3 - ema8  # raw difference, model learns the threshold

    # -- Momentum (simple, proven useful in feature importance) ----------------
    df["return_5"] = close.pct_change(5)
    df["return_15"] = close.pct_change(15)

    # -- Volatility (one clean measure) ----------------------------------------
    df["atr_14"] = atr(high, low, close, 14)

    return df

def build_features(raw_df=None, windows_df=None):
    """
    Main function called by training scripts.

    Args:
        raw_df: 1-min OHLCV DataFrame (loaded if None)
        windows_df: prepared 5-min windows (loaded if None)

    Returns:
        DataFrame with all features + label, no NaN rows.
    """
    print("\nMoon Dev's Feature Engineering Starting...\n")

    # -- Load data if not provided ---------------------------------------------
    if raw_df is None:
        print("Moon Dev | Loading raw 1-min data...")
        raw_df = pd.read_csv(RAW_DATA_PATH, parse_dates=["datetime"])
        raw_df = raw_df.sort_values("datetime").reset_index(drop=True)
        print(f"   Loaded {len(raw_df):,} 1-min rows")

    if windows_df is None:
        print("Moon Dev | Loading prepared 5-min windows...")
        windows_df = pd.read_csv(WINDOWS_PATH, parse_dates=["datetime"])
        print(f"   Loaded {len(windows_df):,} windows")

    # -- Compute indicators on 1-min data --------------------------------------
    raw_df = compute_1min_features(raw_df)

    # -- Sample features at the candle BEFORE each window opens ----------------
    # Each window starts at row i*5 in the trimmed raw data.
    # We take features from row (i*5 - 1), the last candle before the window.
    print("Moon Dev | Sampling features at window boundaries (no future leakage)...")

    n_windows = len(windows_df)
    # Index into raw_df for the candle just before each window opens
    sample_indices = [i * 5 - 1 for i in range(n_windows)]

    # First window (i=0) has index -1 -> no prior candle, will be NaN anyway
    # We'll handle it by clamping to 0 and letting NaN drop take care of it
    sample_indices[0] = 0

    # Identify feature columns (everything we added, not the original OHLCV cols)
    original_cols = {"datetime", "open", "high", "low", "close", "volume", "window_id"}
    feature_cols = [c for c in raw_df.columns if c not in original_cols]

    features_at_boundary = raw_df.iloc[sample_indices][feature_cols].reset_index(drop=True)

    # -- Combine with window info ----------------------------------------------
    result = pd.concat([windows_df.reset_index(drop=True), features_at_boundary], axis=1)

    # -- Time features (hour showed some signal in backtests) ------------------
    print("Moon Dev | Adding time feature...")
    result["hour"] = result["datetime"].dt.hour

    # -- Drop NaN rows from lookback calculations ------------------------------
    before_drop = len(result)
    result = result.dropna().reset_index(drop=True)
    after_drop = len(result)
    print(f"Moon Dev | Dropped {before_drop - after_drop:,} NaN rows")

    # -- Identify final feature list -------------------------------------------
    meta_cols = {"datetime", "open_price", "close_price", "high", "low", "volume", "label"}
    final_feature_cols = [c for c in result.columns if c not in meta_cols]

    # -- Print stats -----------------------------------------------------------
    up = (result["label"] == 1).sum()
    down = (result["label"] == 0).sum()
    total = len(result)

    print("\n" + "=" * 60)
    print("Moon Dev | Feature Engineering Complete")
    print("=" * 60)
    print(f"   Total features:  {len(final_feature_cols)}")
    print(f"   Total samples:   {total:,}")
    print(f"   UP  (label=1):   {up:,}  ({100 * up / total:.1f}%)")
    print(f"   DOWN(label=0):   {down:,}  ({100 * down / total:.1f}%)")
    print(f"   Date range:      {result['datetime'].min()} -> {result['datetime'].max()}")
    print(f"\n   Feature names:")
    for i, col in enumerate(final_feature_cols, 1):
        print(f"     {i:2d}. {col}")
    print("=" * 60)

    return result, final_feature_cols

def main():
    result, feature_cols = build_features()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"\nMoon Dev | Saved {len(result):,} samples -> {OUTPUT_PATH}")
    print("Moon Dev | Feature engineering complete!\n")

    return result, feature_cols

if __name__ == "__main__":
    main()
```
The key design decisions in this script:

**Only backtest-proven signals are included.** No RSI, no Bollinger Bands, no random indicators thrown in for good measure. Every feature earned its place by demonstrating a win rate above 54% (the Polymarket breakeven) in historical backtests.

**Features are sampled at row (i*5 - 1)** — the last 1-minute candle BEFORE each 5-minute window opens. This is critical for preventing future leakage. If you sample features from within the prediction window, you are cheating — the model would see information that didn't exist when the trade decision was made.

**No future leakage.** The model only sees data that existed before the prediction window opened. The first window (index 0) has no prior candle, so it gets NaN values and is dropped. Every other window uses strictly historical data.

The build_features() function is designed to be importable by any training script via from feature_engineering import build_features. This makes it easy to swap in different models without rewriting the feature pipeline.

## Script 3 — XGBoost Raw Candle Model

This is the main event. Instead of hand-picked indicators like MACD and EMA, this script takes a fundamentally different approach: **feed the model raw candle data and let it learn its own patterns**. No MACD. No RSI. No Bollinger Bands. Just pure price action — candle bodies, wicks, and volume. The philosophy is simple: let the model decide what matters.

Here is how it works:

**1. Raw Candle Features** — For each of the 15 candles immediately before the prediction window, the script computes 4 values: body_pct (how much the candle moved as a percentage of open), upper_wick_pct (rejection from highs), lower_wick_pct (rejection from lows), and volume_ratio (volume relative to a 30-candle rolling average). That is 60 raw features.

**2. Aggregate Features** — On top of the individual candles, the script adds about 15 aggregate statistics: green candle counts, average body sizes, wick ratios, body trend (are candles getting bigger or smaller?), consecutive same-direction streaks, return skewness and kurtosis, autocorrelation, distance to round numbers ($100 and $1000 levels), and time features (hour and session).

**3. Time-Series Split** — The data is split 70/15/15 into train, validation, and test sets by time order. The model trains on the oldest data, validates on the middle, and is tested on the most recent data. No shuffling — ever. This simulates real trading where you always predict the future using the past.

**4. XGBoost Training** — The classifier uses conservative hyperparameters: max_depth=4, learning_rate=0.01, subsample=0.7, colsample_bytree=0.5, min_child_weight=100, and early stopping after 100 rounds without improvement.

**5. Polymarket P&L Simulation** — Every prediction on the test set is simulated as a $10 bet at $0.54 entry on Polymarket. Wins pay +$8.52, losses cost -$10.00. The script calculates total P&L and maximum drawdown.

**6. Feature Importance** — The top 20 features by gain are displayed, showing what the model actually learned. Are individual candle shapes more important, or aggregate statistics? The answer might surprise you.

**7. Confidence Thresholds** — Win rate at different confidence levels (0.55, 0.60, 0.65, 0.70) is analyzed. By only trading when the model is highly confident, you can potentially increase win rate at the cost of fewer trades.

**8. Time Breakdown** — Win rate by session (Asia 0-8 UTC, Europe 8-16 UTC, US 16-24 UTC) and by individual hour, revealing when the model performs best.

xgb_raw_candles.py — Complete source

```python
"""
Moon Dev's RAW CANDLE XGBoost - No Indicators, Just Shapes
==========================================================
A completely different approach: instead of indicators (MACD, RSI, etc),
we feed the model RAW CANDLE DATA and let it learn its own patterns.
No human bias about what matters.

Features: 15 raw candle shapes (body, wicks, volume) + aggregate stats
Total: ~75 features. All raw. No indicators. Just candle microstructure.

Author: Moon Dev
"""

import pandas as pd
import numpy as np
import os
import xgboost as xgb
from scipy.stats import skew, kurtosis
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from termcolor import colored

# -- Paths ------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "BTCUSD-1m-200wks-data.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgb_raw_candles_5min.json")

# -- Polymarket Sim Params --------------------------------------------------
ENTRY_PRICE = 0.54
USD_PER_BET = 10.00
SHARES_PER_BET = USD_PER_BET / ENTRY_PRICE
WIN_PROFIT = (1.00 - ENTRY_PRICE) * SHARES_PER_BET
LOSS_AMOUNT = ENTRY_PRICE * SHARES_PER_BET
BREAKEVEN_PCT = ENTRY_PRICE * 100  # 54%

# -- Lookback config --------------------------------------------------------
LOOKBACK = 15  # number of 1-min candles to look back
VOL_ROLLING = 30  # rolling window for volume mean

def print_header():
    """Print the big colorful header."""
    print(colored("\n" + "=" * 75, "cyan", attrs=["bold"]))
    print(colored("  MOON DEV's RAW CANDLE XGBoost - No Indicators, Just Shapes", "cyan", attrs=["bold"]))
    print(colored("=" * 75, "cyan", attrs=["bold"]))
    print(colored("  Philosophy: Let the model learn what matters from raw candle shapes.", "yellow"))
    print(colored("  No MACD. No RSI. No Bollinger Bands. Just pure price action.", "yellow"))
    print(colored("  15 candles x 4 features + aggregate stats = ~75 raw features", "yellow"))
    print(colored("=" * 75, "cyan", attrs=["bold"]))

def load_raw_data():
    """Load the 1-minute OHLCV CSV."""
    print(colored("\n" + "=" * 75, "magenta", attrs=["bold"]))
    print(colored("  Moon Dev | Loading Raw 1-Minute BTC Data", "magenta", attrs=["bold"]))
    print(colored("=" * 75, "magenta", attrs=["bold"]))

    if not os.path.exists(DATA_PATH):
        print(colored(f"\n  ERROR: {DATA_PATH} not found!", "red", attrs=["bold"]))
        print(colored("  Moon Dev says: no data, no model!", "red"))
        exit(1)

    df = pd.read_csv(DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    print(colored(f"  Moon Dev | Loaded {len(df):,} rows of 1-minute data", "green", attrs=["bold"]))
    print(colored(f"  Moon Dev | Date range: {df['datetime'].min()} to {df['datetime'].max()}", "green"))
    print(colored(f"  Moon Dev | Columns: {list(df.columns)}", "green"))
    print(colored(f"  Moon Dev | Price range: ${df['close'].min():,.2f} to ${df['close'].max():,.2f}", "green"))

    return df

def build_features(df):
    """
    Build raw candle features from 1-minute data.
    Group every 5 rows for labels, look back 15 candles for features.
    """
    print(colored("\n" + "=" * 75, "yellow", attrs=["bold"]))
    print(colored("  Moon Dev | Building Raw Candle Features (NO INDICATORS!)", "yellow", attrs=["bold"]))
    print(colored("=" * 75, "yellow", attrs=["bold"]))

    # Pre-compute per-candle values for the whole dataframe
    print(colored("  Moon Dev | Pre-computing candle metrics...", "yellow"))
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values
    datetimes = df["datetime"].values

    # Body pct for each 1-min candle
    body_pct = (closes - opens) / opens * 100
    # Upper wick pct
    max_oc = np.maximum(opens, closes)
    min_oc = np.minimum(opens, closes)
    upper_wick_pct = (highs - max_oc) / opens * 100
    # Lower wick pct
    lower_wick_pct = (min_oc - lows) / opens * 100
    # Rolling volume mean (30 candles)
    vol_series = pd.Series(volumes)
    vol_rolling_mean = vol_series.rolling(VOL_ROLLING, min_periods=1).mean().values
    vol_ratio = volumes / np.where(vol_rolling_mean > 0, vol_rolling_mean, 1.0)
    # 1-min returns for skew/kurtosis/autocorr
    returns_1m = np.diff(closes) / closes[:-1]
    returns_1m = np.concatenate([[0.0], returns_1m])
    # Is green
    is_green = (closes > opens).astype(float)

    # Group every 5 rows for 5-minute windows
    n_rows = len(df)
    n_windows = n_rows // 5
    print(colored(f"  Moon Dev | Total 1-min candles: {n_rows:,}", "yellow"))
    print(colored(f"  Moon Dev | Potential 5-min windows: {n_windows:,}", "yellow"))

    # We need at least LOOKBACK + VOL_ROLLING candles before the window
    min_start = max(LOOKBACK, VOL_ROLLING)

    rows = []
    skipped = 0

    for w in range(n_windows):
        window_start = w * 5
        window_end = window_start + 5  # exclusive

        # Need LOOKBACK candles before window_start
        if window_start < min_start:
            skipped += 1
            continue

        # Label: 1 if last close >= first open of the 5-min window
        first_open = opens[window_start]
        last_close = closes[window_end - 1]
        label = 1 if last_close >= first_open else 0

        row = {}
        row["datetime"] = datetimes[window_start]
        row["label"] = label

        # -- 15 individual candle features -----------------------------------
        # candle_1 = most recent (right before window), candle_15 = oldest
        for i in range(1, LOOKBACK + 1):
            idx = window_start - i  # candle_1 is at window_start-1
            row[f"candle_{i}_body"] = body_pct[idx]
            row[f"candle_{i}_upper_wick"] = upper_wick_pct[idx]
            row[f"candle_{i}_lower_wick"] = lower_wick_pct[idx]
            row[f"candle_{i}_vol"] = vol_ratio[idx]

        # -- Aggregate features ----------------------------------------------
        lb_start = window_start - LOOKBACK  # index of oldest lookback candle
        lb_slice = slice(lb_start, window_start)
        lb5_start = window_start - 5
        lb5_slice = slice(lb5_start, window_start)

        # Green counts
        row["green_count_15"] = is_green[lb_slice].sum()
        row["green_count_5"] = is_green[lb5_slice].sum()

        # Average body/wick sizes (absolute)
        abs_body_15 = np.abs(body_pct[lb_slice])
        row["avg_body_size_15"] = abs_body_15.mean()
        row["avg_upper_wick_15"] = upper_wick_pct[lb_slice].mean()
        row["avg_lower_wick_15"] = lower_wick_pct[lb_slice].mean()

        # Wick ratio (buy vs sell pressure)
        avg_lower = row["avg_lower_wick_15"]
        row["wick_ratio_15"] = row["avg_upper_wick_15"] / avg_lower if avg_lower > 0 else 1.0

        # Body trend: are bodies getting bigger or smaller?
        abs_body_5 = np.abs(body_pct[lb5_slice])
        avg_body_5 = abs_body_5.mean()
        row["body_trend"] = avg_body_5 / row["avg_body_size_15"] if row["avg_body_size_15"] > 0 else 1.0

        # Consecutive same direction (streak ending at most recent candle)
        streak = 1
        last_dir = is_green[window_start - 1]
        for j in range(window_start - 2, max(window_start - LOOKBACK - 1, -1), -1):
            if is_green[j] == last_dir:
                streak += 1
            else:
                break
        row["consecutive_same"] = streak

        # Return stats (last 30 candles)
        ret_start = max(0, window_start - 30)
        ret_slice = returns_1m[ret_start:window_start]
        row["return_skew_30"] = skew(ret_slice) if len(ret_slice) >= 3 else 0.0
        row["return_kurt_30"] = kurtosis(ret_slice) if len(ret_slice) >= 3 else 0.0

        # Autocorrelation of last 15 returns
        ret_15 = returns_1m[window_start - LOOKBACK:window_start]
        if len(ret_15) >= 2 and np.std(ret_15) > 0:
            row["autocorr_15"] = np.corrcoef(ret_15[:-1], ret_15[1:])[0, 1]
        else:
            row["autocorr_15"] = 0.0

        # Round number distances
        price = closes[window_start - 1]
        nearest_100 = round(price / 100) * 100
        nearest_1000 = round(price / 1000) * 1000
        row["round_100_dist"] = abs(price - nearest_100) / price * 100
        row["round_1000_dist"] = abs(price - nearest_1000) / price * 100

        # Time features
        dt = pd.Timestamp(datetimes[window_start])
        hour = dt.hour
        row["hour"] = hour
        if hour < 8:
            row["session"] = 0  # Asia
        elif hour < 16:
            row["session"] = 1  # Europe
        else:
            row["session"] = 2  # US

        rows.append(row)

        # Progress
        if (w + 1) % 100000 == 0:
            print(colored(f"  Moon Dev | Processed {w + 1:,} / {n_windows:,} windows...", "yellow"))

    features_df = pd.DataFrame(rows)

    # Drop any NaN/inf rows
    before_clean = len(features_df)
    features_df = features_df.replace([np.inf, -np.inf], np.nan)
    features_df = features_df.dropna().reset_index(drop=True)
    after_clean = len(features_df)

    print(colored(f"\n  Moon Dev | Skipped {skipped:,} windows (insufficient lookback)", "yellow"))
    print(colored(f"  Moon Dev | Cleaned {before_clean - after_clean:,} rows with NaN/inf", "yellow"))
    print(colored(f"  Moon Dev | Final dataset: {after_clean:,} rows", "green", attrs=["bold"]))

    # Feature columns
    feature_cols = [c for c in features_df.columns if c not in ["datetime", "label"]]
    print(colored(f"  Moon Dev | Total features: {len(feature_cols)}", "green", attrs=["bold"]))
    print(colored(f"  Moon Dev | Features: {feature_cols[:8]}...", "green"))

    # Label distribution
    counts = features_df["label"].value_counts().sort_index()
    total = len(features_df)
    for lv, cnt in counts.items():
        tag = "UP" if lv == 1 else "DOWN"
        print(colored(f"  Moon Dev | {tag} (label={lv}): {cnt:,} ({100 * cnt / total:.1f}%)", "green"))

    return features_df, feature_cols

def time_series_split(df):
    """Split into train/val/test by time order. NEVER shuffle."""
    print(colored("\n" + "-" * 75, "cyan"))
    print(colored("  Moon Dev | Time-Series Split (70/15/15) - NO SHUFFLE", "cyan", attrs=["bold"]))
    print(colored("-" * 75, "cyan"))

    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    for name, split, color in [("TRAIN", train, "green"), ("VAL", val, "yellow"), ("TEST", test, "magenta")]:
        print(colored(f"  {name:5s}: {len(split):>9,} rows | {split['datetime'].min()} to {split['datetime'].max()}", color, attrs=["bold"]))

    return train, val, test

def train_model(train, val, feature_cols):
    """Train XGBoost with raw candle features."""
    print(colored("\n" + "=" * 75, "cyan", attrs=["bold"]))
    print(colored("  Moon Dev | Training RAW CANDLE XGBoost Classifier", "cyan", attrs=["bold"]))
    print(colored("=" * 75, "cyan", attrs=["bold"]))

    X_train = train[feature_cols].values
    y_train = train["label"].values
    X_val = val[feature_cols].values
    y_val = val["label"].values

    print(colored(f"  Moon Dev | Train shape: {X_train.shape}", "cyan"))
    print(colored(f"  Moon Dev | Val shape:   {X_val.shape}", "cyan"))
    print(colored(f"  Moon Dev | Hyperparameters:", "cyan"))
    print(colored(f"    n_estimators=1000, max_depth=4, lr=0.01", "cyan"))
    print(colored(f"    subsample=0.7, colsample_bytree=0.5", "cyan"))
    print(colored(f"    min_child_weight=100, early_stopping=100", "cyan"))

    model = xgb.XGBClassifier(
        n_estimators=1000,
        max_depth=4,
        learning_rate=0.01,
        subsample=0.7,
        colsample_bytree=0.5,
        min_child_weight=100,
        eval_metric="logloss",
        early_stopping_rounds=100,
        random_state=42,
        verbosity=1,
    )

    print(colored("\n  Moon Dev | Fitting model with early stopping...", "cyan", attrs=["bold"]))
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=50,
    )

    print(colored(f"\n  Moon Dev | Best iteration: {model.best_iteration}", "green", attrs=["bold"]))
    print(colored(f"  Moon Dev | Best score: {model.best_score:.6f}", "green", attrs=["bold"]))

    return model

def evaluate_model(model, train, val, test, feature_cols):
    """Full evaluation with all the stats Moon Dev wants to see."""
    print(colored("\n" + "=" * 75, "green", attrs=["bold"]))
    print(colored("  Moon Dev | MODEL EVALUATION - RAW CANDLE XGBoost", "green", attrs=["bold"]))
    print(colored("=" * 75, "green", attrs=["bold"]))

    # -- Accuracy on each split ------------------------------------------------
    results = {}
    for name, split, color in [("TRAIN", train, "green"), ("VAL", val, "yellow"), ("TEST", test, "magenta")]:
        X = split[feature_cols].values
        y = split["label"].values
        preds = model.predict(X)
        acc = accuracy_score(y, preds)
        results[name] = {"acc": acc, "preds": preds, "y": y, "X": X}
        acc_color = "green" if acc > 0.54 else "red"
        print(colored(f"  {name:5s} Accuracy: {acc * 100:.2f}% ({(y == preds).sum():,}/{len(y):,})", acc_color, attrs=["bold"]))

    # -- Classification report on test -----------------------------------------
    print(colored("\n" + "-" * 75, "yellow"))
    print(colored("  Moon Dev | Classification Report (TEST SET)", "yellow", attrs=["bold"]))
    print(colored("-" * 75, "yellow"))
    report = classification_report(results["TEST"]["y"], results["TEST"]["preds"],
                                   target_names=["DOWN (0)", "UP (1)"])
    print(colored(report, "yellow"))

    # -- Confusion matrix ------------------------------------------------------
    print(colored("  Moon Dev | Confusion Matrix (TEST SET)", "yellow", attrs=["bold"]))
    cm = confusion_matrix(results["TEST"]["y"], results["TEST"]["preds"])
    print(colored(f"                Predicted DOWN  Predicted UP", "white"))
    print(colored(f"  Actual DOWN:    {cm[0][0]:>7,}        {cm[0][1]:>7,}", "white"))
    print(colored(f"  Actual UP:      {cm[1][0]:>7,}        {cm[1][1]:>7,}", "white"))

    # -- Polymarket P&L Simulation ---------------------------------------------
    print(colored("\n" + "=" * 75, "magenta", attrs=["bold"]))
    print(colored("  Moon Dev | POLYMARKET P&L SIMULATION (TEST SET)", "magenta", attrs=["bold"]))
    print(colored("=" * 75, "magenta", attrs=["bold"]))

    test_preds = results["TEST"]["preds"]
    test_y = results["TEST"]["y"]

    correct = (test_preds == test_y)
    total_trades = len(test_preds)
    wins = correct.sum()
    losses = total_trades - wins
    win_rate = wins / total_trades * 100

    pnl_per_trade = np.where(correct, WIN_PROFIT, -LOSS_AMOUNT)
    cumulative_pnl = np.cumsum(pnl_per_trade)
    total_pnl = cumulative_pnl[-1]

    # Max drawdown
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = running_max - cumulative_pnl
    max_drawdown = drawdowns.max()

    print(colored(f"  Entry Price:     ${ENTRY_PRICE:.2f}", "magenta"))
    print(colored(f"  USD per Bet:     ${USD_PER_BET:.2f}", "magenta"))
    print(colored(f"  Shares per Bet:  {SHARES_PER_BET:.2f}", "magenta"))
    print(colored(f"  Win Profit:      ${WIN_PROFIT:.2f}", "magenta"))
    print(colored(f"  Loss Amount:     ${LOSS_AMOUNT:.2f}", "magenta"))
    print(colored(f"  Breakeven:       {BREAKEVEN_PCT:.0f}%", "magenta"))
    print()

    pnl_color = "green" if total_pnl > 0 else "red"
    print(colored(f"  Total Trades:    {total_trades:,}", "white", attrs=["bold"]))
    print(colored(f"  Wins:            {wins:,}", "green", attrs=["bold"]))
    print(colored(f"  Losses:          {losses:,}", "red", attrs=["bold"]))
    print(colored(f"  Win Rate:        {win_rate:.2f}%", pnl_color, attrs=["bold"]))
    print(colored(f"  Edge over BEV:   {win_rate - BREAKEVEN_PCT:+.2f}%", pnl_color, attrs=["bold"]))
    print(colored(f"  Total P&L:       ${total_pnl:,.2f}", pnl_color, attrs=["bold"]))
    print(colored(f"  Max Drawdown:    ${max_drawdown:,.2f}", "red", attrs=["bold"]))

    # -- Top 20 features by gain -----------------------------------------------
    print(colored("\n" + "=" * 75, "cyan", attrs=["bold"]))
    print(colored("  Moon Dev | TOP 20 FEATURES BY GAIN", "cyan", attrs=["bold"]))
    print(colored("=" * 75, "cyan", attrs=["bold"]))

    importance = model.get_booster().get_score(importance_type="gain")
    fname_map = {f"f{i}": col for i, col in enumerate(feature_cols)}
    importance_named = {fname_map.get(k, k): v for k, v in importance.items()}
    sorted_imp = sorted(importance_named.items(), key=lambda x: x[1], reverse=True)[:20]

    print(colored(f"  {'Rank':<6}{'Feature':<35}{'Gain':>12}", "white", attrs=["bold"]))
    print(colored("  " + "-" * 53, "white"))
    for i, (feat, gain) in enumerate(sorted_imp, 1):
        # Color code: candle features vs aggregate features
        if feat.startswith("candle_"):
            c = "cyan"
        else:
            c = "yellow"
        print(colored(f"  {i:<6}{feat:<35}{gain:>12.2f}", c))

    # -- Confidence analysis ---------------------------------------------------
    print(colored("\n" + "=" * 75, "yellow", attrs=["bold"]))
    print(colored("  Moon Dev | CONFIDENCE THRESHOLD ANALYSIS (TEST SET)", "yellow", attrs=["bold"]))
    print(colored("=" * 75, "yellow", attrs=["bold"]))

    X_test = test[feature_cols].values
    y_test = test["label"].values
    proba = model.predict_proba(X_test)
    max_proba = np.max(proba, axis=1)

    thresholds = [0.55, 0.60, 0.65, 0.70]
    print(colored(f"  {'Threshold':<12}{'Trades':>10}{'Win Rate':>12}{'Edge':>10}{'% of Total':>14}", "white", attrs=["bold"]))
    print(colored("  " + "-" * 58, "white"))
    for thresh in thresholds:
        mask = max_proba >= thresh
        if mask.sum() == 0:
            print(colored(f"  >{thresh:.2f}       {'0':>10}{'N/A':>12}{'N/A':>10}{'0.0%':>14}", "yellow"))
            continue
        filtered_preds = model.predict(X_test[mask])
        filtered_correct = (filtered_preds == y_test[mask])
        wr = filtered_correct.mean() * 100
        n_trades = mask.sum()
        pct_total = n_trades / len(y_test) * 100
        edge = wr - BREAKEVEN_PCT
        wr_color = "green" if wr > BREAKEVEN_PCT else "red"
        print(colored(f"  >{thresh:.2f}       {n_trades:>10,}{wr:>11.2f}%{edge:>+9.2f}%{pct_total:>13.1f}%", wr_color))

    # -- Time breakdown --------------------------------------------------------
    print(colored("\n" + "=" * 75, "green", attrs=["bold"]))
    print(colored("  Moon Dev | TIME BREAKDOWN (TEST SET)", "green", attrs=["bold"]))
    print(colored("=" * 75, "green", attrs=["bold"]))

    test_df = test.copy()
    test_df["pred"] = test_preds
    test_df["correct"] = (test_df["pred"] == test_df["label"]).astype(int)

    # Session breakdown
    session_names = {0: "Asia (0-8 UTC)", 1: "Europe (8-16 UTC)", 2: "US (16-24 UTC)"}
    print(colored("\n  Win Rate by Session:", "green", attrs=["bold"]))
    if "session" in test_df.columns:
        session_stats = test_df.groupby("session")["correct"].agg(["mean", "count"])
        for sess, row in session_stats.iterrows():
            name = session_names.get(int(sess), f"Session {sess}")
            wr_color = "green" if row["mean"] * 100 > BREAKEVEN_PCT else "red"
            bar = "#" * int(row["mean"] * 50)
            print(colored(f"    {name:<20}: {row['mean'] * 100:5.1f}% ({int(row['count']):>6} trades) {bar}", wr_color))

    # Hour breakdown
    if "hour" in test_df.columns:
        print(colored("\n  Win Rate by Hour:", "green", attrs=["bold"]))
        hour_stats = test_df.groupby("hour")["correct"].agg(["mean", "count"])
        for hour, row in hour_stats.iterrows():
            bar = "#" * int(row["mean"] * 50)
            wr_color = "green" if row["mean"] * 100 > BREAKEVEN_PCT else "red"
            print(colored(f"    Hour {int(hour):>2}: {row['mean'] * 100:5.1f}% ({int(row['count']):>5} trades) {bar}", wr_color))

    return results, total_pnl, win_rate, total_trades

def save_model(model):
    """Save trained model."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_model(MODEL_PATH)
    print(colored(f"\n  Moon Dev | Model saved to {MODEL_PATH}", "green", attrs=["bold"]))

def print_summary(test_acc, win_rate, total_pnl, total_trades, n_features):
    """Print the final summary box."""
    edge = win_rate - BREAKEVEN_PCT

    print(colored("\n", "white"))
    print(colored("  +=========================================================+", "cyan", attrs=["bold"]))
    print(colored("  |  Moon Dev's RAW CANDLE XGBoost Results                   |", "cyan", attrs=["bold"]))
    print(colored("  +=========================================================+", "cyan", attrs=["bold"]))
    print(colored(f"  |  Approach:       No indicators, raw candle shapes       |", "yellow", attrs=["bold"]))
    print(colored(f"  |  Features:       {n_features:>3} raw features                   |", "yellow", attrs=["bold"]))
    print(colored(f"  |  Test Accuracy:  {test_acc * 100:>6.2f}%                          |", "cyan", attrs=["bold"]))
    print(colored(f"  |  Test Win Rate:  {win_rate:>6.2f}%                          |", "cyan", attrs=["bold"]))

    pnl_color = "green" if total_pnl > 0 else "red"
    print(colored(f"  |  Polymarket P&L: ${total_pnl:>10,.2f}                    |", pnl_color, attrs=["bold"]))
    print(colored(f"  |  Breakeven:      {BREAKEVEN_PCT:.0f}% | Edge: {edge:+.2f}%               |", "cyan", attrs=["bold"]))
    print(colored(f"  |  Total Trades:   {total_trades:>6,}                           |", "cyan", attrs=["bold"]))
    print(colored("  +=========================================================+", "cyan", attrs=["bold"]))
    print()

def main():
    print_header()

    # 1. Load raw 1-min data
    df = load_raw_data()

    # 2. Build raw candle features
    features_df, feature_cols = build_features(df)

    # 3. Time-series split
    train, val, test = time_series_split(features_df)

    # 4. Train
    model = train_model(train, val, feature_cols)

    # 5. Evaluate
    results, total_pnl, win_rate, total_trades = evaluate_model(model, train, val, test, feature_cols)

    # 6. Save
    save_model(model)

    # 7. Summary
    test_acc = results["TEST"]["acc"]
    print_summary(test_acc, win_rate, total_pnl, total_trades, len(feature_cols))

    print(colored("  Moon Dev | Raw candle training complete! Pure price action, no indicator bias.", "green", attrs=["bold"]))
    print(colored("  Moon Dev | Let the candles speak for themselves.\n", "green", attrs=["bold"]))

if __name__ == "__main__":
    main()
```
Here are the key insights from this approach:

**Why raw candles?** Traditional indicators like MACD and RSI are designed by humans with specific assumptions about what drives price. Those assumptions might be right, or they might introduce bias. By feeding the model raw candle shapes, we remove human assumptions entirely. The model might find patterns in wick ratios or body trends that no human trader would think to look for.

**Feature design:** 4 values per candle (body %, upper wick %, lower wick %, volume ratio) multiplied by 15 candles gives 60 individual candle features. On top of that, about 15 aggregate features (green counts, body trends, return statistics, round number distances, time features) bring the total to roughly 75. Every feature is normalized — percentages and ratios instead of raw prices — so the model can generalize across different price levels.

**Anti-overfitting:** Several mechanisms prevent the model from memorizing the training data. max_depth=4 keeps trees shallow so they can't learn hyper-specific patterns. min_child_weight=100 prevents the model from making decisions based on tiny samples. subsample=0.7 and colsample_bytree=0.5 add randomness to each tree. Early stopping after 100 rounds without improvement on the validation set prevents overtraining.

**P&L simulation:** Every prediction on the test set is simulated as a $10 bet at $0.54 entry on Polymarket. A correct prediction pays +$8.52 (you paid $5.40 for shares worth $1.00 each, so you profit $4.60 per share times 18.52 shares). An incorrect prediction loses -$10.00 (your $10 bet goes to zero). Breakeven is 54%. Any win rate above that generates profit.

## Key Takeaways

### What to Take Away

**Three scripts, one pipeline** — Data prep creates clean 5-minute windows. Feature engineering adds proven signals. The XGBoost model trains on raw shapes. Each script is standalone but they build on each other.

**Two philosophies** — The feature engineering script uses human-selected indicators (MACD, EMA) that proved themselves in backtests. The raw candle model throws all of that away and lets XGBoost discover patterns in candle microstructure. Both approaches have merit — and you can compare their results.

**No future leakage** — Every feature is computed from data that existed before the prediction window opened. The time-series split means the model is always tested on future data it has never seen. No shuffling, no random splits, no cheating.

**Confidence filtering** — The model outputs probabilities, not just binary predictions. By only trading when confidence exceeds 60% or 65%, you can potentially increase win rate at the cost of fewer trades. The confidence threshold analysis in the output helps you find the right balance.

**Session awareness** — BTC behaves differently during Asia, Europe, and US sessions. The model learns this implicitly through the hour and session features. The time breakdown in the evaluation shows you exactly when the model performs best and worst.

## Getting Started

This pipeline runs entirely offline. No API keys, no exchange accounts, no real money. Just Python, data, and your terminal.

### Requirements

**1. Python 3.10+** — Any recent Python version works. Use conda or venv for environment management.

**2. Install dependencies** — pip install pandas numpy xgboost scikit-learn scipy termcolor

**3. BTC 1-minute candle data** — You need a CSV file with datetime, open, high, low, close, and volume columns. The more data the better — 200 weeks gives you hundreds of thousands of 5-minute windows.

**4. Run in order** — python data_prep.py, then python feature_engineering.py, then python xgb_raw_candles.py

**5. Model output** — The trained model is saved to models/xgb_raw_candles_5min.json for use in live trading or further analysis.

## Want to learn more?

Join the Moon Dev community to discuss backtesting strategies, share results, and build better trading systems together.

[Visit Moon Dev](https://moondev.com)

Built with love by Moon Dev

### Related Resources

[MACD 5-Minute Backtest — Base Strategy](https://moondev.com/macd-five-minute-backtest)

— The original MACD crossover backtest for Polymarket BTC markets

[MACD Histogram Filter Backtest — Signal Quality Filter](https://moondev.com/macd-histogram-filter-backtest)

— Adding histogram strength thresholds to filter noisy MACD signals

[CVD 5-Minute Bot — Order Flow Alpha](https://moondev.com/cvd-five-minute-bot)

— Fully automated bot using CVD divergence signals

[Polymarket 5-Minute Bot — Easy Hyper Gambler](https://moondev.com/polymarket-five-minute-bot)

— The keyboard-controlled bot for manual trading

[Moon Dev API Documentation](https://moondev.com/docs)

— Tick data, liquidation data, funding rates, and more

[Live Liquidation Dashboard](https://moondev.com/liquidations)

— Watch real time liquidations
