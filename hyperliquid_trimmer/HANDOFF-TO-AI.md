# HANDOFF-TO-AI.md — give this text to the AI setting up the VPS

You are setting up the HYPERLIQUID TRIMMER on my VPS. The bundle is in
`~/hyperliquid_trimmer` (or attached as `hyperliquid_trimmer.zip`). Read
`README.md` first (what the bot is and is NOT — it is insurance, not a profit
strategy), then work through the test ladder in `instructions.md` in order.

Standing rules:

1. **FIRST TASK — survey before installing.** Check what else runs on this VPS:
   - Other Hyperliquid bots or heavy API users (`ps aux`, crontab, tmux
     sessions). Hyperliquid's rate cap is ~1200 calls/min and the trimmer uses
     ~180/min — report anything that would squeeze that budget. Do NOT kill or
     modify other bots without asking me first; just report.
   - Any existing `.env` files, wallet addresses, or positions I already have
     on this machine. Report paths (NEVER print private keys — not even
     partially).
2. **The ladder is authority-boundary:**
   - Rungs 0–1 (watch mode + trigger math, LIVE=false, no keys) — yours to run.
   - Rung 2 (testnet drill) — yours ONLY with a testnet key I provide, against
     `https://api.hyperliquid-testnet.xyz`. Never point a testnet drill at
     mainnet.
   - Rungs 3–4 (micro-live mainnet, production) — **STOP and report to me.
     I approve each one explicitly. You never set LIVE=true on mainnet on your
     own authority.**
3. `LIVE` stays `false` until I say otherwise. You never touch `.env`
   credentials — I fill those myself (chmod 600). If a step needs a key, ask;
   never invent, reuse, or request one in chat.
4. **Rung 0 acceptance:** run ≥10 minutes against the wallet address I give
   you (reading is public — any address works for practice). Verify the
   printed distance% roughly matches the Hyperliquid UI for the same
   position, and that the status line shows: coin, side, size, entry, mid,
   mark, liq, dist%, uPnL ($ and %), next-trim size.
5. **Kill-switch drill before any live request:** `touch KILL` → bot stands
   by → `rm KILL` → resumes. Report the result.
6. **Verification checklist to include in your Rung 2/3 report** (every item
   must be checked, from the exchange's own trade history, not the bot's log):
   - every fill is reduce-only (position never grows, never flips side)
   - after a long-side trim the liquidation price moved AWAY (and vice versa)
   - order type was IOC with the slippage cap respected
   - the bot never cancelled anything and never placed a resting order
7. **Production ops (only after my Rung-4 approval):** run under tmux or
   systemd (restart=always). Daily 1-minute check: loop still printing, no
   constant THROTTLED messages, every trade-history entry reduce-only.
8. **Report format (short):** current rung · PASS/FAIL per rung with evidence ·
   distance% cross-check · throttle count · anything weird. When a rung fails,
   stop and report — do not improvise around a FAIL.

Parameter lock: TRIGGER_PERCENT=2.0, TRIM_PERCENT=5.0, SLIPPAGE_PERCENT=2.0,
LOOP_SECONDS=1.0, TRIM_WAIT_SECONDS=2.0, MAX_TRIMS=0 in production. These are
the values validated in the source stream (see SOURCE-TRANSCRIPT.txt). Do not
"improve" them without telling me why and getting approval. MAX_TRIMS>0 is a
drill-only setting — never in production.

Constraints: no installs beyond requirements.txt; no uploading my data
anywhere; measure, don't attack — public read endpoints plus (only when I
approve live) reduce-only order placement.
