<!-- source: https://moondev.com/roadmap (section #alpha-strategies) -->
<!-- captured: 2026-10-07 · full catalog extracted verbatim -->

# 🔥 Alpha Generation & Strategies — edge ideas

> **Note:** We have backtested strategies in the bootcamp & quant elite, but below are
> just **strategy IDEAS** that I am looking into. These are not financial advice —
> they're research directions and concepts to explore.

---

## 🎲 Random Trading Ideas

- **Gaps** — Gap Trading Strategies. Trading gaps that occur between close and open. Look for gaps that fill vs gaps that run.
- **Trend Following** — Classic momentum strategies
- **Carry Trades** — Interest rate differentials
- **Mean Reversion** — Price returning to average
- **Pair Trading** — Long/short correlated assets
- **Arbitrage** — Price discrepancies across markets
- **Momentum Ignition** — Detecting fake breakouts
- **Volume Profile** — Trading around high volume nodes
- **VWAP Strategies** — Volume weighted average price
- **Opening Range Breakout (ORB)** — Trade breakouts from the first 15-30 minutes of trading range.
- **Market Making** — Providing liquidity for spread capture
- **Statistical Arbitrage** — Mean reversion on spreads
- **Event-Driven** — Trading around news/earnings
- **Sentiment Analysis** — Social media/news sentiment
- **Order Flow Analysis** — Reading tape/order book
- **Seasonality** — Day of week, month, year patterns
- **Volatility Trading** — VIX, options strategies
- **Correlation Breakdown** — When correlations fail
- **Liquidity Hunting** — Finding liquidity pools
- **Delta Neutral** — Hedged positions

## 📊 Technical Indicator Strategies

### StochRSI Strategy
Stochastic RSI combines RSI with Stochastic formula. Look for oversold bounces and overbought reversals.
```python
# StochRSI Backtest Setup
def STOCHRSI(data, period=14, k=3, d=3):
    rsi = ta.RSI(data['Close'], period)
    stoch = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min()) * 100
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

# Entry: K crosses above D below 20
# Exit: K crosses below D above 80
```

### MFI (Money Flow Index)
Volume-weighted RSI. Better than regular RSI because it incorporates volume.
```python
# MFI Strategy
def MFI(data, period=14):
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    money_flow = typical_price * data['Volume']
    # Positive/negative flow based on typical price direction
    return mfi

# Entry: MFI < 20 (oversold)
# Exit: MFI > 80 (overbought)
```

### Market Cipher Style
Combination of wave trend, money flow, and VWAP. Popular indicator recreated.
```python
# Market Cipher Components
# 1. Wave Trend (WT)
# 2. Money Flow (MFI)
# 3. VWAP Bands
# 4. Stochastic RSI

# Buy signals when multiple indicators align:
# - WT crosses up from oversold
# - MFI is oversold
# - Price below VWAP
```

- **RSI Divergence** — Price makes new high/low but RSI doesn't confirm. Classic divergence trading.
- **MACD Histogram** — Trade MACD histogram turning points rather than signal line crosses.
- **Bollinger Band Squeeze** — Low volatility (tight bands) often precedes big moves.
- **Keltner Channel Breakouts** — ATR-based channels for trend trading.
- **Ichimoku Cloud** — Multiple components: Tenkan, Kijun, Senkou Span A/B, Chikou.
- **ADX Trend Strength** — Only trade when ADX > 25 indicating strong trend.
- **CCI (Commodity Channel Index)** — Mean reversion indicator, overbought/oversold levels at +100/-100.
- **Williams %R** — Similar to Stochastic but inverted scale.
- **Parabolic SAR** — Trailing stop indicator for trend following.

## 📈 Volume & Order Flow

- **Volume Spread Analysis (VSA)** — Analyzing the relationship between price spread (high-low), volume, and close location.
- **On-Balance Volume (OBV)** — Cumulative volume indicator - volume added on up days, subtracted on down days.
- **Accumulation/Distribution Line** — Similar to OBV but weights volume by close location within the bar.
- **Chaikin Money Flow** — Measures buying/selling pressure over a period.
- **Force Index** — Elder's indicator combining price change and volume.
- **VWAP Reversion** — Price tends to revert to VWAP, especially intraday.
- **Volume Profile POC** — Point of Control - highest volume price level attracts price.
- **Delta Analysis** — Difference between buying and selling volume at each price.
- **Footprint Charts** — See actual buy/sell volume at each price level.
- **Order Book Imbalance** — Large bid/ask imbalances can predict short-term direction.

## 🪙 Crypto-Specific Strategies

- **Funding Rate Arbitrage** — When funding is very positive/negative, fade the crowd. High funding = short, low funding = long.
- **Open Interest Analysis** — Rising OI with price = strong trend. Falling OI with price = weak trend.
- **Liquidation Hunting** — Price tends to hunt liquidity at liquidation levels. Trade the bounce after liquidation cascade.
- **CVD (Cumulative Volume Delta)** — Track aggressive buying vs selling. Divergence from price = potential reversal.
- **Exchange Flow Analysis** — Large inflows to exchange = potential selling. Large outflows = accumulation.
- **Whale Wallet Tracking** — Follow large wallets, trade their movements.
- **DeFi Yield Arbitrage** — Borrow low, lend high across protocols.
- **MEV Strategies** — Triangular arbitrage, cross-DEX arbitrage, and other positive-sum MEV strategies. We don't do sandwich attacks or front-running - bad vibes only hurt others.
- **Basis Trading** — Spot vs perpetual price differences.
- **Cross-Exchange Arbitrage** — Price differences between exchanges.

## 🔄 Mean Reversion Strategies

- **Z-Score Mean Reversion** — Calculate z-score of price, trade when > 2 std devs from mean.
- **RSI Mean Reversion** — Buy RSI < 30, sell RSI > 70. Simple but effective in ranging markets.
- **Bollinger Band Bounce** — Buy at lower band, sell at upper band in ranging markets.
- **Distance from MA** — When price is X% from moving average, expect reversion.
- **Pair Trading** — Long underperformer, short outperformer when spread is extended.
- **Calendar Spread Reversion** — Front month vs back month futures spreads mean reversion.
- **Sector Rotation** — Sectors that underperform tend to catch up.
- **VIX Mean Reversion** — VIX tends to revert to mean - sell spikes, buy dips.

## 🚀 Momentum Strategies

- **52-Week High Breakout** — Stocks at 52-week highs tend to continue higher.
- **Relative Strength** — Buy strongest stocks vs market, avoid weakest.
- **Dual Momentum** — Absolute and relative momentum combined for better results.
- **Time Series Momentum** — If positive returns over lookback, stay long. Otherwise, go to cash.
- **Cross-Sectional Momentum** — Long top performers, short bottom performers in a universe.
- **Earnings Momentum** — Stocks that beat earnings tend to continue outperforming.
- **Price Rate of Change** — Simple ROC indicator for momentum measurement.
- **Acceleration** — Not just momentum, but change in momentum.

## 📜 Options & Derivatives

- **Covered Calls** — Own stock, sell calls against it for income.
- **Cash-Secured Puts** — Sell puts on stocks you want to own at lower prices.
- **Iron Condor** — Sell both call and put spreads, profit from low volatility.
- **Straddle/Strangle** — Buy both calls and puts, profit from big moves either direction.
- **Calendar Spreads** — Profit from time decay differences between near and far expiry options.
- **Butterfly Spreads** — Profit from price staying at a specific level.
- **Vertical Spreads** — Defined risk directional bets.
- **Volatility Arbitrage** — Trade implied vs realized volatility differences.
- **Gamma Scalping** — Delta hedge options position, profit from realized vol.

## 🏗️ Market Structure

- **Break of Structure (BOS)** — When price breaks previous swing high/low, indicating trend continuation.
- **Change of Character (CHoCH)** — First sign of potential reversal - breaking recent swing in opposite direction.
- **Order Blocks** — Areas where institutional orders were placed, price tends to revisit.
- **Fair Value Gaps (FVG)** — Imbalanced price areas that often get filled.
- **Liquidity Pools** — Areas where stop losses cluster, price hunts these levels.
- **Premium vs Discount Zones** — Only buy in discount (below equilibrium), sell in premium (above).
- **Swing Failure Pattern** — Price breaks swing but fails to continue - reversal signal.
- **Equal Highs/Lows** — Double tops/bottoms are liquidity targets.

## 🧮 Quantitative Strategies

- **Factor Investing** — Value, momentum, size, quality, low vol factors.
- **Risk Parity** — Allocate based on risk contribution, not capital.
- **Black-Litterman** — Combine market equilibrium with investor views.
- **Kelly Criterion** — Optimal position sizing based on edge and odds.
- **Monte Carlo Simulation** — Simulate thousands of scenarios for risk analysis.
- **Regime Detection** — Use HMM or other models to detect market regime changes.
- **Cointegration Trading** — Find pairs that are cointegrated for stat arb.
- **Principal Component Analysis** — Reduce dimensionality, find hidden factors.

## 📚 Trading Ideas from Books

- **Turtle Trading (Way of the Turtle)** — Donchian channel breakout system. 20-day breakout entry, 10-day breakout exit.
- **CAN SLIM (How to Make Money in Stocks)** — O'Neil's system: Current earnings, Annual earnings, New products, Supply/demand, Leader, Institutional, Market.
- **Livermore's Pivotal Points (Reminiscences)** — Trade breakouts from consolidation, add to winners.
- **Elder's Triple Screen (Trading for a Living)** — Weekly trend, daily timing, intraday entry. Multiple timeframe analysis.
- **Minervini's SEPA (Trade Like a Stock Market Wizard)** — Specific Entry Point Analysis - tight consolidations, volatility contraction.
- **VSA (Master the Markets - Tom Williams)** — Volume Spread Analysis - read effort vs result in bars.
- **Market Profile (Mind Over Markets)** — TPO charts, value area, initial balance concepts.
- **Wyckoff Method** — Accumulation, markup, distribution, markdown phases.
- **RSI Strategy (New Concepts - Connors)** — Short-term RSI strategies, 2-period RSI for mean reversion.
- **The Alchemy of Finance (Soros)** — Reflexivity - price affects fundamentals which affects price.
- **Market Wizards Ideas** — Various strategies from interviewed traders - trend following, discretionary, systematic.

## 🛡️ Risk Management Ideas

- **ATR-Based Position Sizing** — Size positions based on volatility so each trade has similar risk.
- **Correlation Management** — Don't take multiple correlated positions - diversify exposure.
- **Maximum Drawdown Limits** — Stop trading when drawdown exceeds threshold.
- **Volatility Scaling** — Reduce size in high vol, increase in low vol environments.
- **Time-Based Exits** — Exit trades that don't work within X bars/days.
- **Equity Curve Trading** — Reduce size when equity curve below its own MA.
- **Portfolio Heat** — Track total portfolio risk, not just per-trade risk.
- **Asymmetric Risk/Reward** — Only take trades with at least 2:1 or 3:1 R/R.

## 🔬 Experimental Ideas

- **Lunar Cycles** — Some studies show correlation with market behavior.
- **Social Sentiment** — Twitter/Reddit sentiment as contrarian indicator.
- **Weather Patterns** — Some commodities correlate with weather.
- **Google Trends** — Search volume as leading indicator.
- **Satellite Data** — Parking lot traffic, ship movements for fundamentals.
- **Alternative Data** — Credit card data, app downloads, job postings.
- **Cross-Asset Signals** — Bonds predicting stocks, commodities predicting forex.
- **Network Analysis** — Whale wallet connections, institutional holdings overlap.

---

## 💡 Remember

> These are **ideas to research**, not proven strategies. Always backtest extensively
> before risking real capital. No strategy works in all market conditions. The edge is
> in the execution and risk management, not just the idea itself.
