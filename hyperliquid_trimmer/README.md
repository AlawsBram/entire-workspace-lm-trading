# HYPERLIQUID TRIMMER — the "whales don't get liquidated" bot

Built 2026-10-10 from the Moon Dev stream transcript (see
`uploads/NOTEGP~1.TXT` in the workspace). Folder is self-contained.

## What it is (plain language)

On Hyperliquid, if you trade with leverage and the price runs against you far
enough, the exchange force-closes your WHOLE position at the worst possible
moment (liquidation). For accounts under $100k, it's all at once — no second
chances.

This bot is an **airbag**. It watches your position every second and measures
how far the price is from your liquidation price. When that distance drops to
2%, it sells 5% of your position (or buys back 5% if you're short) — a small,
deliberate sacrifice that PUSHES YOUR LIQUIDATION PRICE FURTHER AWAY. Then it
waits 2 seconds, re-checks, and trims again only if still in danger. One trim
at the 2% trigger moves you back to ~3.1% away — more than the worst 1-minute
drop measured in the stream's data (1.82%).

## The strategy insight behind it

The streamer watched a ~$100M whale get pushed toward liquidation for MONTHS
— and never die. The whale kept trimming small slices, each trim moving his
liquidation price further away, until he exited in profit on his own terms.
Meanwhile, everyone smaller standing between the whale and the price got
liquidated. The lesson: **big players survive by converting "all-or-nothing"
risk into a ladder of small, chosen losses.** This bot automates that ladder,
unemotionally, 24/7 — a human can't do it because a human is asleep half the
time (his words).

## What it is NOT

It is NOT a money-making strategy. It has zero alpha. It's insurance: it
turns a possible −100% into a series of small −5% slices so your position
idea stays alive. If your underlying position has no edge, this bot only
makes you lose slower. (The streamer says this himself: "not get-rich-quick",
"not a side income", "if you got $10 you're not going to make any money".)

The offensive mirror of this bot — trading OTHER people's liquidation
cascades — is the "Liq Magnet" article, already archived at
`Moondev Roadmap/Code From Videos/hyperliquid-liquidation-magnet-bot.md`.

## Safety design (all in code)

1. **LIVE=false by default** — dry run only prints intended orders.
2. **Reduce-only IOC orders** — the exchange itself forbids the order from
   ever increasing the position or resting on the book.
3. **Never cancels, never adds.** Only one action exists: shrink.
4. Direction is enforced by sign of position: long → SELL, short → BUY.
5. Slippage capped (IOC limit at ±2% of mid).
6. Kill file → instant standby.
7. Reading positions is PUBLIC — dry-run needs no keys at all.
8. Rate use ~180 calls/min vs Hyperliquid's 1200/min cap; backoff on 429;
   optional Moon Dev API backup feed hook.

## Design decisions taken from the stream

- Use whichever of **mark or mid is closer to liquidation** (HL liquidates
  on MARK price — confirmed in their docs — but mid moves first; taking the
  more at-risk one is conservative).
- Trigger at **2%**, not 1%: after a 1%-trigger trim you're only ~2% away —
  one fast minute (worst measured: 1.82%) could jump straight to liquidation.
  At 2% trigger you land ~3.1% away after a trim.
- Trim **5%** per event, re-check after 2s, repeat while inside the zone.
- Slippage cap raised 1%→2% ("rather lose a little slippage than get liquidated").
- Hyperliquid only liquidates in 20% chunks for positions over $100k;
  smaller accounts are closed entirely at once — which is exactly why small
  accounts need early trimming most.

## Files

| File | Role |
|---|---|
| `trimmer.py` | the bot |
| `.env.example` | config template (copy to `.env`, chmod 600) |
| `instructions.md` | the test ladder — how to validate before trusting it |
| `HANDOFF-TO-AI.md` | exact prompt to hand to the VPS setup AI (rung-by-rung authority rules) |
| `SOURCE-TRANSCRIPT.txt` | the Moon Dev stream transcript this bot was built from |
| `requirements.txt` | deps (SDK only needed for LIVE) |
