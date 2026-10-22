<!-- source: https://moondev.com/roadmap (section #rbi-system) -->
<!-- captured: 2026-10-07 · incl. both expandable code examples -->

# 🔬 My RBI System for Algo Trading

> The process of automating your trading starts with research of trading strategies,
> then backtest those strategies to see if they actually work in the past. If they do,
> they are not guaranteed, but much more likely to work in the future.

## RBI = Research, Backtest, Incubate

| Stage | What happens |
|---|---|
| 📘 **Research** | Research trading strategies and alpha generation techniques (google scholar, books, podcasts, youtube) |
| 🧪 **Backtest** | Use OHLCV data to backtest the strategy and see if it actually worked in the past |
| 📈 **Incubate** | If the backtest is profitable, incubate in a trading bot with tiny size & scale slowly |

---

## 📘 Research Strategies & Alpha Generation

- **Google Scholar** has PhDs writing about trading strategies
- Read **books** on trading and traders
- Study **podcasts** of traders
- Watch trading **videos**
- Create a **backlog of ideas** to backtest

## 🧪 Backtest with Good Data Across Multiple Timeframes

- Use **backtesting.py** to backtest your strategies
- Get **great data** to test on multiple timeframes
- **Optimize** the backtest to find best variables + analyze matrix
- Backtest on **multiple symbols and timeframes** to build confidence

### Example Backtest Code (expandable on the page)

```python
import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Load the filtered data
data_path = '/path/to/your/BTC-USD-1h-data.csv'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')

# Bollinger Band Breakout Strategy (Short Only)
class BollingerBandBreakoutShort(Strategy):
    window = 21
    num_std = 2.7
    take_profit = 0.05  # 5%
    stop_loss = 0.03    # 3%

    def init(self):
        # Calculate Bollinger Bands using TA-Lib
        self.upper_band, self.middle_band, self.lower_band = self.I(
            talib.BBANDS, self.data.Close, self.window, self.num_std, self.num_std
        )

    def next(self):
        if len(self.data) < self.window:
            return

        # Check for breakout below lower band
        if self.data.Close[-1] < self.lower_band[-1] and not self.position:
            self.sell(sl=self.data.Close[-1] * (1 + self.stop_loss),
                      tp=self.data.Close[-1] * (1 - self.take_profit))

# Ensure necessary columns are present
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Create and configure the backtest
bt = Backtest(data, BollingerBandBreakoutShort, cash=100000, commission=0.002)

# Run the backtest with default parameters
stats_default = bt.run()
print("Default Parameters Results:")
print(stats_default)

# Perform optimization
optimization_results = bt.optimize(
    window=range(10, 20, 5),
    num_std=[round(i, 1) for i in np.arange(1.5, 3.5, 0.1)],
    take_profit=[i / 100 for i in range(1, 7, 1)],
    stop_loss=[i / 100 for i in range(1, 7, 1)],
    maximize='Equity Final [$]',
    constraint=lambda param: param.window > 0 and param.num_std > 0
)

print("Best Parameters:")
print("Window:", optimization_results._strategy.window)
print("Num Std:", optimization_results._strategy.num_std)
print("Take Profit:", optimization_results._strategy.take_profit)
print("Stop Loss:", optimization_results._strategy.stop_loss)
```

## 📈 Incubate in Trading Bot with Tiny Size

- Add **risk controls** to bot
- Add **strategy** to bot
- How are we entering? **Limit or market?**
- Check position and only enter if none — `get_position()`
- Cancel all orders before opening — `n.cancel_all_orders()`
- **Decimal adjustments** for size and price (all floats)
- Use `n.open_order_deluxe()` for SL orders
- Set up the **while True schedule** to run every minute or so
- Turn any debugging `> <` back to normal
- Launch bot with **tiny size** ($10 is HyperLiquid min)
- Check in after first few hours, then **every 12 hours**

### Bot Schedule Loop (expandable on the page)

```python
print('running algo...')
main()
schedule.every(15).minutes.do(main)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(f"Encountered an error: {e}")
        time.sleep(10)
```

---

## 💡 The Key Insight

> Strategies that worked in the past are **not guaranteed** to work in the future,
> but they are **much more likely** to work than strategies you haven't tested.
> **That's the edge.**
