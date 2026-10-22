# instructions.md — the test ladder (run every rung before trusting it)

Golden rule: the bot earns the right to go LIVE one rung at a time.
Each rung has a PASS condition. Any FAIL → fix → repeat the rung.

---

## Rung 0 — Watch mode (no keys, no risk, 10+ minutes)

Reading Hyperliquid positions is PUBLIC. Point it at your own wallet (or any
address with an open position) and just watch the prints.

```bash
cp .env.example .env            # set HL_WALLET_ADDRESS only. LIVE stays false.
python trimmer.py
```

PASS when, every second, it prints: coin, side, size, entry, mid, mark,
liq price, distance%, unrealized PnL ($ and %), and the size of the NEXT
trim it would send. Check the distance% against the Hyperliquid UI for the
same position — they must roughly match (it uses mark/mid, UI uses mark).

## Rung 1 — Trigger math (dry run, still no risk)

Temporarily set `TRIGGER_PERCENT=99` in `.env` (so the zone is always "inside")
and restart. LIVE is still false.

PASS when it prints `[DRY] WOULD SELL ...` (for a long) or `WOULD BUY ...`
(for a short), size ≈ 5% of current position, reduce-only IOC, price cap =
mid ∓ 2%. Then it must WAIT 2s and print another would-trim (streak
behavior). Restore `TRIGGER_PERCENT=2.0` after.

## Rung 2 — Testnet live drill (free money, real mechanics)

Hyperliquid has a testnet. Give it a fake key there and watch REAL
reduce-only orders flow without risking a cent:

```
HL_API=https://api.hyperliquid-testnet.xyz
LIVE=true            # testnet key only!
```
Open a small testnet position first (testnet UI, 5x leverage), let price move
or set TRIGGER_PERCENT high to fire the trim.

PASS when: orders are accepted as reduce-only IOC, position SHRINKS (never
grows, never flips side), liq price moves AWAY after a long-sell trim.

## Rung 3 — Micro-live drill on mainnet (the streamer's own beta test)

Exactly what the stream did before trusting it, with real money but a size
too small to matter:

```
LIVE=true
TRIM_PERCENT=0.01         # hundredth of a percent — cents, not dollars
MAX_TRIMS=3               # hard cap for the drill
TRIGGER_PERCENT=<current distance + 1>   # forces it to fire immediately
```

Watch it fire 2–3 times. Verify in the Hyperliquid trade history:
1. fills are tiny (cents), reduce-only, position NOT closed, side unchanged
2. after each fill the liq price moved away
3. it stops at MAX_TRIMS

Then KILL it (`touch KILL`) and restore production parameters.

## Rung 4 — Production

```
LIVE=true  TRIGGER_PERCENT=2.0  TRIM_PERCENT=5.0  SLIPPAGE_PERCENT=2.0
LOOP_SECONDS=1.0  TRIM_WAIT_SECONDS=2.0  MAX_TRIMS=0
```
Run it under tmux/systemd for the lifetime of the position. It does nothing
until danger; that's the point.

## Ongoing checks (daily, 1 minute)

- Is the loop still printing? (stalled bot = no airbag)
- Any THROTTLED messages? (backoff handles it; if constant, free up rate
  budget — don't run other heavy bots on the same IP/key)
- Trade history: every fill must be reduce-only and small.

## Never

- Run with MAX_TRIMS>0 in production (that cap is a drill tool).
- Put the private key anywhere except `.env` (chmod 600).
- Assume it works because it printed nicely — Rung 3 exists for a reason.
- Treat it as a profit strategy. It is insurance. See README.
