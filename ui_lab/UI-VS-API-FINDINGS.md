# UI vs API — FINDINGS (first full-round audit)

**Round audited:** `btc-updown-5m-1790431800` (2026-09-26 14:10–14:15Z) · 436 paired DOM/API observations at ~4 Hz headless-browser polling · CSV: `ui_vs_api_5m_1790431800.csv`

## 1. The UI "Current Price" is the settlement TWAP, not the spot
- UI price matched `round2(Chainlink 60s TWAP)` **exactly, to the cent, on 397/428 samples (92.8%)**; mean |diff| $0.01, max $0.29 (the misses are just UI refresh latency between TWAP ticks).
- Against Chainlink **spot** the UI price was off by mean **$2.24, max $9.04** — decisively a different series.
- **Implication:** the number a retail user watches is the *smoothed settlement average itself*. It moves slowly and lags real price by construction. When BTC spikes late in a round, the UI price barely moves while the *book* reprices instantly — which is exactly the confusion our S1 edge lives in. The UI is honest about the feed, misleading about the speed.

## 2. "Price To Beat" = open TWAP print, rounded to cents
- UI showed **$83,916.98**; our independent arbiter snap = **83916.97705691744** → identical after rounding. Our settlement reconstruction and the venue's displayed reference are the same number. ✔

## 3. Rounding: display 2dp, settlement full precision
- 428/428 UI prices had exactly 2 decimal places. Settlement uses full precision (our raw feeds), so the display can disagree with the true value by up to half a cent.
- Only dangerous in razor-thin rounds (|final gap| < ~$0.50): the cents display can show one direction while full-precision settlement goes the other. This round: +$22.22 gap, no ambiguity; official `Up` = our reconstruction `Up`. ✔
- The "rounding" lore is real but tiny in dollar terms; the *bigger* UI distortion is #1 and #4.

## 4. The UI odds labels (Up/Down ¢) are NOT the live book
- UI Up¢ sat inside the CLOB [bid,ask] only **244/397 (61%)** of samples; mean |UI − book mid| = **1.8¢**; **82 samples > 2¢ off**.
- Worst case: **t=0–3s after the bell, book jumped to 64/65¢ while the UI still showed 51¢ — a 13.5¢ lag** during the open print. Mid-round, UI ran +2.5…+4.5¢ above mid persistently (it behaves like a last-trade print in a trending round, not a mid).
- **Implication:** never trade off the displayed ¢; our stack correctly reads the CLOB book directly. A human tapping buttons off those labels is quoting 2–13¢ blind.

## 5. Misc verified
- `crypto_prices` (exchange spot) RTDS topic delivered nothing — the UI's spot-ish source, if any, is elsewhere; irrelevant given #1.
- "Go to live market" button appears **after** the round closes (True in final rows) — matches the UI flow you described; the comparator targets the next round's slug at the bell instead.
- Final-resolution banner text was not captured by the regex (page shows result via a fresh render); official gamma resolution and our reconstruction agreed (`Up`/`Up`), so resolution integrity is verified by the two authoritative series, not the banner.

## Bottom line for the stack
The UI layer adds zero information we don't already have from the APIs — but it *quantifies* the retail experience: a smoothed, rounded, lagging view of a market whose book moves in real time. That is the structural edge we trade against, now measured rather than assumed. Keep this lab running on the VPS as a standing control: any future divergence between UI-rendered series and API series (new rounding, new delay, new source) is itself a regime signal.
