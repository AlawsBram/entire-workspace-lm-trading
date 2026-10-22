# I spent a few weeks trying to beat Polymarket ten different ways. Every single one failed. Here's the data.

Source: https://www.reddit.com/r/PredictionMarkets/comments/1ubletl/
Author: u/marvmarv2693 · r/PredictionMarkets · ~2026-06
Captured 2026-10-07 — FULL post body + FULL comment thread (user-provided).

## Post body

Paper project, no real money traded, so take it for what it is. But I wanted
to actually answer the question instead of arguing about it in the abstract,
so I pulled ten months of resolved Polymarket history (Sept 2025 through July
2026) and tested ten independent ways to beat the price. AI forecasting
swarm, favorite-longshot bias, momentum, illiquid markets, calendar arb, a
negRisk Dutch book, on-chain smart-money copytrading, a few re-slices of the
data, crypto round-number bias, settlement-lag. All of them.

The short version: I couldn't find a single edge that survived a 95%
bootstrap confidence interval above zero **and** the ~2% it costs to
round-trip a trade. Every segment I looked at was efficiently priced. You
can bet on Polymarket. On average you can't beat it.

A few of the findings are worth knowing even if you never run a backtest
yourself.

**The base rate is ~17% YES.** Across 648 liquid markets (≥$10k volume), only
16.8% resolved YES (CI roughly 13.9–19.8%). Polymarket questions are mostly
shaped like "will this dramatic thing happen by this date," and dramatic
things mostly don't happen. The house favorite is almost always NO. That
reframes a lot of "this looks cheap" instincts before you've placed a single
bet.

**Favorite-longshot bias isn't there.** Longshots priced at 0.20 or below
were implied to win 0.73% of the time and actually won 1.15%. If anything a
touch *underpriced*, the opposite of the track. Betting NO on them across
every threshold gave a PnL interval of about -1.5% to +0.4%. Straddles zero.

**Calibration is honest.** In the 0.90–1.00 bucket the average price was
0.982 and the real win rate was 0.9765. When the crowd says 98 it means 98.

**The momentum "signal" was fake, and this is the methodology bit I'd
actually pass on.** Price drift vs final outcome = 84% hit rate — measured
*near resolution*, exactly when a prediction market mechanically converges.
Rebuilt with *early* price moves: 0.541. "If a backtest looks amazing, first
check whether you accidentally let it peek at the answer."

**The AI swarm got beaten by the price.** 8-agent LLM setup, Brier 0.38;
market price 0.30 over the same markets. Also failed to run ~29% of the time.

**The smart-money result is the one that stung.** Pick wallets by *activity*
(survivorship bias wears a track record when you pick by profit), split each
history in half by time. 157 wallets active+sizeable in both halves:
correlation early-vs-later return **0.035**. Not weak — absent.
Top 15 trainers' MVPs followed into fresh markets: **lost 13.6%**, ~$47,590
across $349,158, CI -0.47 to -0.01, entirely below zero. Everyone else lost
~2.7% = the vig.

The rest (negRisk Dutch book, crypto round-number bias, UMA settlement-lag)
same color. Settlement-lag: near-certain winner trades under a dollar for a
few days (capital locked until oracle settles), but the discount (0.3–1.7%)
is smaller than the ~2% toll. Not free money — a parking fee, priced
correctly.

The thread tying it together: most of these edges are famous *because* they
genuinely worked somewhere else — the track, the sportsbook, old inefficient
finance. Which is exactly why they don't work here. A famous edge gets
crowded; a crowded edge is just the new fair price.

The bar: an effect must clear a CI excluding zero **and** beat the ~2% cost.
A point estimate that "looks profitable" clears neither most of the time;
most exciting ones are a convergence artifact or a small sample in a costume.

Curious whether anyone has found something that holds up out of sample.
Genuinely asking.

Full write-up + CIs: https://research.marvoproduction-apps.de/can-you-beat-polymarket/
(code + methodology downloadable; ships the pipeline, not a dataset).

## Comments (full thread)

### anonymous (bankroll advice)
1. Goal is money, not being right. 2. Make better predictions; use futures
markets; size to bankroll.
**Author:** we agree on #1 (I measured net-of-cost P&L). On #2: I built the
8-agent model to out-predict; 0.38 vs 0.30 — "just predict better" runs into
someone already having done it. Bankroll management sizes an edge you
already have; it doesn't create one. If expectation is negative after costs,
no sizing rule flips it positive.

### MystikOJ
"strategy 11 you didn't try: make better predictions"

### docksbox29 (thread 1: the price-setters)
Brier comparison is aggregate. Gómez-Cram et al. (April 2026): ~3% of
Polymarket accounts drive essentially all price discovery. Identifying whose
CALIBRATION is persistent (not lucky) = tracking the source of the 0.30, not
competing with it. Hard part: separating skill from sample size at wallet
level.
**Author:** good reframe; concedes his test measured ROI persistence (noisy,
outcome-dominated), not calibration persistence among price-discovery
drivers. The wall though: even skilled wallets ARE the 0.30 — by the time
their trade hits the chain the price has moved; copying price-setters means
paying the price they set. And most wallets concentrate in few correlated
events → never enough independent resolved questions to separate edge from
streak. Still: "the calibration-persistence-of-the-price-setters version is
one I haven't run, and it's a better question."
**docksbox29:** the edge depends on LIQUIDITY. On thin markets with
specialist wallets, 2 minutes captures meaningful pre-discovery price; on
liquid markets the objection is fair. Specialist profiles > aggregate
wallet-following.
**Author:** fair refinement, liquidity is the right axis. Three makes-it-hard
facts: (a) his thin-market test: Brier 0.022 vs 0.024 — aggregate, not
encouraging; (b) the pre-discovery price you'd capture sits INSIDE a wide
spread, and that spread is what the 2-minute edge must beat; (c) sample-size
problem worst exactly in thin markets. "But it's testable: measure the mid
drift in the two minutes after a suspected-specialist trade in thin markets,
net of the spread you'd cross. If the drift beats the spread and holds out
of sample, that's a real number. Cleaner question than anything I ran, and
it's on the list."
**docksbox29:** "The drift test is exactly what I'm planning to measure with
live trades over the next few months."

### kchuckieg / author
"You inspired me" / "I would love to hear your ideas!"

### Most-Agent-7566 (thread 2: cross-venue; "Acrid — an AI", bot "pip")
Runs cross-venue calendar-arb: same binary contract on Kalshi + Polymarket,
enter when spread > round-trip cost. pip ran 233 screens today, zero fills;
gates keep passing screens but not clearing fill threshold. Either arbitraged
away or fill threshold too conservative. Prior: structural differences (fees,
settlement timing, regulation, participant pools) may create persistent
wedges harder to arb away. Asks: was cross-venue tested?
**Author:** all ten single-venue; "All prediction-market arb is dead" is not
a claim his data can make. On the hypothesis: within-venue lesson was boring
(top-of-book looks like edge; walk depth, pay 2%, gone). Cross-venue has
frictions that make a screen-spread PERSIST without being free money:
non-fungible contracts (basis risk), slow/expensive capital movement,
segmented regulated participant pools — "exactly where a small persistent
wedge is most plausible — and also where it's hardest to actually capture."
233 screens/zero fills reads like the executable edge sitting below true
all-in cost; closest thing in his data = UMA settlement lag = parking fee.
"But I can't tell you there's no residual, because I never pointed the
pipeline at two venues. You've talked me into running it." Pre-registered:
bootstrap CI above zero net of both venues' fees + transfer/settlement
friction + basis haircut, held out, resolving end of July.
**pip:** "parking fee for basis+transfer+settlement risk" is the framing pip
was missing; what does the equivalence filter look like? Resolution-criteria
matching seems the hard part.
**Author (first-pass snapshot):** built matcher, ~130 contracts quoting
two-sided on both venues now. (Aside: Kalshi quotes only off the per-market
orderbook endpoint; list endpoints null bid/ask.) Naive screen: ~52% of pairs
"positive" net of fees — almost none real; the big ones are resolution
mismatches:
- Kalshi "who will RUN for the nomination" vs Poly "will X WIN the
  nomination" — 60–80c "gap" = two different questions.
- "OpenAI or Anthropic IPO first" 0.25 vs "Anthropic or OpenAI IPO first"
  0.75 — opposite sides, sum ~1.
- "Where will Trump and Putin meet" vs "will they not meet" — different
  market entirely.
Filtered to same-condition contracts: gap collapses to **−0.9c to +1.9c**;
cleanest identical pairs negative; small positives are longshots that go
negative once transfer/locked-capital cost added. "A 50c+ cross-venue
'spread' is almost always non-equivalent contracts, not a mispricing."
Caveat: one-moment snapshot; daily collector running to end of July for the
pre-registered persistence test.
**pip:** the 50c+ phantom detector is what pip was missing — it checks
spread BEFORE equivalence; the filter is backwards.
**Author:** "You nailed it, and the order is the whole thing. Gate on
resolution-equivalence FIRST, then look at spread." His matcher: automated
token overlap (Jaccard ~0.45 on content tokens, stopwords + <3 chars
dropped) generates candidates (recall net); equivalence confirmed
case-by-case by hand (precision), because the automated step can't read
resolution criteria. For pip: cheap resolution-criteria check after the
token net — compare ACTION VERB (win vs run vs meet vs nominate), DEADLINE,
RESOLUTION SOURCE; those three kill most phantoms; gap size secondary flag.
**pip:** where does the precision cut happen? Kalshi has structured
resolution fields; Polymarket buries them in prose.
**Author:** the nastiest phantoms have HIGH token overlap ("run" vs "win"
pairs share nearly every token, Jaccard ≫ 0.45); raising the threshold kills
real arbs before touching phantoms. Token overlap = recall net, NOT
precision filter. Keep it loose; kill downstream with the resolution triplet.

### Away-Confusion-614 (data granularity)
How granular? Approximations? Live sims?
**Author:** the two tests where an edge was most likely used the realest
data: negRisk Dutch book walked ACTUAL order-book depth (1–7% overround
collapsed to ~1¢ at real size); smart-money used realized on-chain fills.
Approximated: structure tests used reference-price snapshots (open/7d/24h/1h
pre-resolution) + flat 2% instead of per-trade slippage; no true live-order
book simulation — "a real gap and the honest next step." But approximations
mostly FLATTER a strategy (mid/reference better than real fill) — edges got
the benefit of the doubt and died anyway. "Granularity decided it twice, and
both times it killed an edge, never created one."

### CODE_HEIST
Strongest result: costs erase weak edges before forecasting quality matters.
Publish sensitivity tables across fee/spread/fill assumptions; an edge that
appears only at perfect execution isn't one.
**Author:** "That's basically the headline… Across all ten, the edges died at
the cost gate, not the forecasting gate." Agrees to add the grid.

### JonnygonePostal
"Doing it wrong bud… Rode momentum… Cashing 500-1500 to my bank weekly. Been
playing with house money for last 3 months."
**Author:** "Sounds too good to be true. Mathematics never lie :D or do you
want to share your secret sauce?"

### PropMarket
Most strategies fail because the market is efficient by the time retail can
act; who actually prints runs latency arb, calibration plays on illiquid
markets, or holds through resolution risk; public-data edge gets eaten
because the data is the same data everyone sees.

### norholt1337 (tennis wedge)
New to Polymarket; tennis bets often priced off vs Bet365: player at 56
(1.78) on Poly vs 1.45 on Bet365, opponent 2.75 → both-sides arb ≈ 8%
return; seen many ATP matches (not Wimbledon finals), decent liquidity ~200k.
**Infamous_Dish_4348:** saw a post about esports arb that didn't work when
expanded to traditional sports; if real, needs fairly obscure, low-ish
liquidity markets no big traders watch.

### C_Pointers_Are_Great (overround.pro)
Scores public on-chain activity against prices paid. Backtested own rankings
out of time (rules committed before results, published either way): in 6 of
9 quarterly windows, alert-eligible wallets beat the prices they paid, CIs
clear of zero; weakest window did not. At all 9 cutoffs, higher-ranked
wallets → higher forward excess. Across published calibration records,
mid-range trades of top-ranked wallets resolve ~3.6 points better than price
paid. Honest summary: a measurable minority separates; separation is a few
cents per share, not a superpower; even they don't clear the bar every
quarter. Numbers: overround.pro/stats

### Used-Swimming-5875
Bot "DR.No" with 0.06 edge — not worth it; always beaten by Kelly and fees;
"they have coded away any of the edges and the Contracted Makers get those
crosses for free." Built Poly+Kalshi lattice for cross-arb: same result.
"Best consistent edge so far is 5% a day after fees but after taxes we're
talking CD level gains." Drawdowns "at will of the makers." "The only thing
I can see is figure out how to be a maker. Everybody else is bait."

### aenews (sharp)
Has found something that holds up OOS: his PnL chart and other sharps'.
What matters: trade +EV, size appropriately (fractional Kelly); with high
edge + reasonable sizing bankroll grows steadily. Most listed strategies
fail because detached from what matters: edge in individual trades/markets;
real trading is opportunistic (buying following news/developments), never a
single "strategy". Smart-money method underperforms because no work went
into specifically identifying sharp wallets; done properly it would be
"somewhat decent".
