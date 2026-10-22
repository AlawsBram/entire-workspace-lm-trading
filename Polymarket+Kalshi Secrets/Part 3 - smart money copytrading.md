# Can You Copy Polymarket's Best Traders? (Part 3)

Source: https://research.marvoproduction-apps.de/polymarket-smart-money/
Captured 2026-10-07, verbatim (footer cards trimmed).

## The trap I almost walked straight into
Sorting wallets by current profit and copying the top = selecting for the
outcome then acting amazed by it. Survivorship bias in a convincing costume.
The only honest test: pick by ACTIVITY, split each wallet's history in half
by time, ask whether first-half skill predicts second-half. Real skill
persists; luck doesn't make appointments.

## 105,885 wallets walk into a bar
600 markets, 105,885 distinct wallets; top 1,200 by activity; after filtering
for genuine activity+size in both halves: 157 wallets.
**Correlation early-return vs later-return: 0.035.** Not weak — absent.
Confession: an early 16-wallet pilot showed 0.43 and he started mentally
spending the money. At real sample size the 0.43 vanished. "The gap between
0.43 and 0.035 is the whole reason you don't trust a result until it's tired
of being tested."

## Then it got mean
Top 15 traders of the training period followed into fresh markets: **lost
13.6%** — −0.229 out-of-sample return on $349,158 of bets, CI −0.47 to −0.01,
entirely below zero. Copying last season's winners reliably lost.
Everyone else lost ~2.7% on average = the vig. "An efficient market, written
in one number, in money."

## Seven more doors, all locked
Re-slices (open vs settle prices, short vs long markets, category, liquidity
tier) — every candidate edge handed to paid independent skeptics; all seven
killed.
The closest thing to a real finding: **opening prices are about twice as
noisy as later prices** (cold start). A true inefficiency — under two cents
wide, and it costs ~2.7% to trade. "You can see the twenty-dollar bill on
the sidewalk. Bending down costs twenty-five."

## Two more, because I couldn't help it
1. Round-number bias (crypto strikes): proper vol model, no bias found; round
   vs ragged strikes mispriced a quarter-cent apart. The strategy only
   "worked" because the sample sat in a bull run — betting yes on everything
   beat the model; its genuinely contrarian calls lost 8%.
2. Settlement-lag discount: real and measurable — the near-certain winner
   trades under $1 for ~4 days until the oracle settles. Discount 0.3–1.7%,
   smaller than the 2.7% toll. "It isn't a mispricing. It's a parking fee."

## What the whole thing actually found
AI swarm lost to the price. Six textbook edges lost to the price. The
on-chain elite didn't just fail to beat it — they lost money, significantly,
out of sample. Ten independent angles, same answer: Polymarket is efficient;
the price is smarter than the smartest individuals tracked across seasons.
"That's the result. It's also exactly the result nobody posts, because 'I
tested the dream rigorously and it isn't real' doesn't sell a course."
Code + methodology open; data rebuilt from public APIs by a one-command
collector. "Go prove me wrong. I'd genuinely love it. I just wouldn't bet
on it."
