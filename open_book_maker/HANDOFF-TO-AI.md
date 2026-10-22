# HANDOFF-TO-AI.md — give this text to the AI setting up the VPS

> **MISSION UPDATE 2026-10-14 (supersedes the phase plan below where they conflict):**
> Strategy #11 OPEN-BOOK-MAKER is **CLOSED** (live loss −$32.60 on 2026-10-10 after a
> gate-FAILED backtest; see `postmortem-2026-10-10/`). The current mission is
> **`VARIANT-EXPERIMENT-PLAN.md`: simulation-only experiments, zero dollars.**
> Standing rules 2, 6 and 7 below still apply; rule 5's gate is replaced by the welded
> revival criteria R1–R10 in the plan (including R8: the bot must mechanically refuse
> LIVE mode without a fresh `gate_pass.json`). A failed gate is a verdict, not a
> hypothesis — live money never validates a backtest. If you distrust the data, audit
> the pipeline against the REVIEW E1–E12 checklist; you do not trade it.

You are setting up the OPEN-BOOK-MAKER experiment on my VPS. The bundle is in
`~/open_book_maker` (or attached as `open_book_maker.tar.gz`). Work through
`instructions.md` in order, with these standing rules:

1. **FIRST TASK — before any setup:** check whether this VPS already has
   BTC 5-minute market data from my earlier collection bots (instructions.md,
   Step 0). Search home dirs, common data dirs, cron, and running processes.
   Report what you find (paths, schemas, date ranges, row counts). If data
   exists, reuse it for the backtest instead of re-collecting; convert
   schemas if needed; NEVER delete existing data.
2. You are in Phase A: **capture + simulation only. No live trading.**
   `DRY_RUN` stays `true`. You do not touch `.env` credentials — I fill those
   myself. Ask me if a step needs keys; never invent or request them in chat.
3. Run `book_recorder.py` under tmux or systemd so it survives reboots;
   confirm records are being written within 2 minutes (one JSON line per
   second per round in `book_data/YYYY-MM-DD.jsonl`).
4. Each day: `python maker_sim.py --replay book_data/*.jsonl` then
   `python chain_verify.py --csv sim_rounds.csv`. Keep a running tally of
   settled rounds and net PnL.
5. The Phase-A gate (DECISION.md): ≥200 settled rounds, PnL above the −5.5%
   passive-MM benchmark with confidence, adverse-selection edge ≥ 0. When
   reached — or if 7 days pass without reaching it — stop and report to me
   with the numbers. Do NOT proceed to live on your own authority.
6. Kill-switch drill before ANY live discussion: with the bot running in
   DRY RUN, `touch KILL`, confirm standby behavior, `rm KILL`.
7. Report format (daily, short): rounds captured, rounds settled, sim PnL,
   adverse-selection edge, feed uptime, anything weird.

Constraints: no package installs beyond requirements.txt; no external data
uploads; all keys stay in `.env` (chmod 600); measure, don't attack — public
endpoints only, no authenticated probing beyond what order placement needs.
