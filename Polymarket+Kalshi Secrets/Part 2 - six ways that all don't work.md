# Six Ways to Beat Polymarket That All Fail (Part 2)

Source: https://research.marvoproduction-apps.de/six-ways-to-beat-polymarket/
Captured 2026-10-07, verbatim (footer cards trimmed).

648 resolved Polymarket markets, each ≥ $10k volume, Sept 2025–July 2026.
Paper project, no real money, not advice.

## First, the body on the table
Of those 648 markets, only 16.82 percent resolved YES (CI ~13.9–19.8%).
Polymarket questions are overwhelmingly "will this dramatic thing happen by
this date" — dramatic thresholds mostly don't get crossed. The house
favorite, the thing you'd win by betting against the headline, is NO.

## Autopsy one: the longshot that wasn't overpriced
Longshots priced ≤ 0.20: market implied 0.73% wins; they actually won 1.15%.
Slightly UNDERpriced — opposite of the track. Sweeping NO thresholds across
0.05/0.10/0.15/0.20: P&L CI −1.5% to +0.4%. Straddling zero. No edge.

## Autopsy two: the prices are just honest
0.90–1.00 bucket (85 markets): average price 0.982, actual win rate 0.9765.
The crowd telling the truth to within half a percentage point.

## Autopsy three: momentum, and the mirage that fooled me for an afternoon
Price drift vs final outcome: 0.8386 — momentum "picked the winner five times
out of six". But the drift was measured NEAR RESOLUTION — when the market
mechanically converges. Rebuilt honestly (early drift → predict end): 0.541.
A coin flip with a slight limp. "The most exciting result is usually the one
where you forgot to check your own clock."

## Autopsy four: heavy favorites, already spoken for
Favorites ≥ 0.90: expected value after paying the price = −0.6%. You're
buying a dollar of probability for a dollar and change.

## Autopsy five: the thin markets weren't sloppy either
290 thin markets ($500–$10k volume): Brier 0.022 vs liquid 0.024 — if
anything a hair SHARPER. The "28/28 heavy favorites resolved" streak = 28
bets in a market thin enough that one motivated trader explains it. A small
number wearing a costume.

## Autopsy six: the calendar arbitrage that was my own bug
"Trump does X by March" vs "by June" logic-chain arb across ~2,100 live
markets: every hit was a false alarm from sloppy string matching (different
thresholds/opponents/events). Tightened matching → opportunities evaporated.
The market wasn't broken. My script was.

## A seventh thing, briefly: public "trading bot strategies" repo audit
Ten advertised strategies: zero net-profitable once costs counted honestly;
README returns came from forgetting to subtract costs; generated orders
weren't even cryptographically signed (Polymarket would reject them
outright). Verdict: don't run it.

## Why every door was locked
~40 statistical tests → chance hands you exciting false positives; held to a
corrected bar; nothing cleared it. Every one of these edges is famous because
it genuinely worked somewhere else (the track, the sportsbook, old
inefficient finance) — which is exactly why they don't anymore. Famous edges
get crowded, and a crowded edge is just the new fair price. Polymarket
already ate all six.

Which finally forced the obvious move: if the prices are this honest, stop
staring at prices. Start staring at people. (→ Part 3)
