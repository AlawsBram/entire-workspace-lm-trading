# I Built an Army of AI Pundits to Beat a Prediction Market. They Lost to a Single Number. (Part 1)

Source: https://research.marvoproduction-apps.de/ai-swarm-vs-polymarket/
Captured 2026-10-07, verbatim (footer cards trimmed).

Found MiroFish (GitHub): hand it a question about the future and it builds a
tiny society of AIs — eight personas with names and backstories arguing on a
simulated Twitter/Reddit for 30 rounds; then reads the room and outputs a
probability. Question: could it TRADE? Tested on paper against Polymarket:
harness wakes daily, picks fresh questions, writes the swarm's prediction
BEFORE the outcome, plus two controls — a single cold AI ("baseline") and the
market price at that moment.

## Setup facts
- Cost: ~**27 cents per run** (10× under budget).
- Reliability: **29% of runs (9/31) crashed** mid-simulation, usually while
  building the knowledge graph. One morning in three, the synthetic
  civilization didn't show up to work.

## The night it resolved at 23:43
One beautiful exception: a peace-deal market where the swarm went hard
against a falling price and nailed it: **+81.74 €** on paper.
Honest accounting: total paper profit across everything = **+61.70 €** — so
remove that one lucky call and the rest of the confident simulated opinions
summed to about **minus twenty euros**. "One good night carried the whole
thing. That's not a strategy. That's a slot machine that happened to pay out
while I was watching."

## The number that actually mattered (Brier score, lower = better)
- Lone AI asked cold: **0.42**
- Eight-agent swarm (graphs, personas, 30 rounds): **0.38**
- The market price, free, one second, no server: **0.30**

The swarm beat the dumb baseline (a tenth of a point — mediocre to
slightly-less-mediocre). The market crushed both, not close. "I had built an
elaborate machine to be reliably worse than just looking at the price."

## Why it lost: the drama problem
The swarm was bad in a DIRECTION: systematically over-predicted dramatic,
escalatory, news-cycle outcomes. Control test on boring low-probability
markets (resolve "no" 95/100): the swarm overshot them by a factor of
**three to seven**. "It could not look at a quiet room without imagining a
fire." Eight copies of an internet-trained model amplifying the internet's
most expensive bias, "and charged me 27 cents for the privilege."
The market doesn't do this: real people take the boring side of dramatic
bets and usually win. That's the 0.30. Not magic — many informed people,
none able to monetize panic the way a Reddit thread can.

## What I'm doing about being wrong
Pre-registered nine live swarm predictions in a timestamped, uneditable file
before outcomes exist; settling end of month; stated expectation in writing:
the swarm loses (its escalation wave already passed). "If it wins anyway,
that's the first real argument against everything I just told you, and I'll
report it honestly. I don't think it will."

## The takeaway
A prediction-market price isn't a starting point you can out-think with
cleverness; it's the aggregated, money-weighted, continuously updated opinion
of a crowd that includes people who know more than you. The fancy model was
worse, and broke a third of the time.
(Leads to Part 2: the quant approach — six classic edges vs ten months of
history.)
