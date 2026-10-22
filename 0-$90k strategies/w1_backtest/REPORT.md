# Q1 REPORT — W1 weather bucket backtest (holdout only)
window 2026-09-14 → 2026-10-14 · cities 14 · model rows 6790 · priced-fresh 850 (stale-skipped 5940)
fit/holdout split 60% of days per city·lead · slippage +0.02

| θ | n buys | hit rate | EV per $1 | total PnL @$1 | mean prob | mean ask |
|---|---|---|---|---|---|---|
| 0.1 | 240 | 6.2% | -0.69 | -164.9 | 0.27 | 0.09 |
| 0.15 | 151 | 6.0% | -0.70 | -105.0 | 0.31 | 0.09 |
| 0.2 | 77 | 3.9% | -0.78 | -60.3 | 0.34 | 0.08 |

## calibration (holdout, all priced rows, no trade filter)
| prob/price bin | our n | our hit | crowd n | crowd hit |
|---|---|---|---|---|
| 0-10% | 61 | 0.10 | 325 | 0.02 |
| 10-20% | 306 | 0.14 | 110 | 0.16 |
| 20-30% | 234 | 0.26 | 95 | 0.37 |
| 30-40% | 195 | 0.34 | 114 | 0.37 |
| 40-50% | 37 | 0.43 | 117 | 0.38 |
| 50-60% | 17 | 0.47 | 65 | 0.62 |
| 60-70% | 0 | nan | 19 | 0.63 |
| 70-80% | 0 | nan | 3 | 0.67 |
| 80-90% | 0 | nan | 1 | 1.00 |

Brier — our model 0.1697 vs crowd price 0.1401 (holdout)

## VERDICT vs pre-registered criteria: **KILL**
(PASS needs n≥100 AND EV/$≥+0.20 on holdout; KILL if EV≤0)