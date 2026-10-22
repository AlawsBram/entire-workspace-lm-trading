# 🌎 Moon Dev Trading Bot Roadmap — complete capture

**Source:** https://moondev.com/roadmap · **Captured:** 2026-10-07
**Method:** the roadmap page is a client-rendered Next.js app — every section's content
was extracted verbatim from its JS bundle (build `Xljc0SpR_GIMGvGtUwCax`, chunk
`2871.02b36884e91e57ea.js`), including expandable/dropdown content (FAQ accordion,
RBI code examples, strategy catalog). All 17 "Code From Videos" pages that open in
new tabs were then crawled as full pages (article + all code blocks). All 88
testimonial screenshots downloaded.

**Page metadata (verbatim):**
- Title: *Algorithmic Trading Roadmap | Learn Trading Automation | Moon Dev*
- Description: "Learn how to automate your trading with AI and machine learning. The
  ultimate roadmap for building trading bots, algo trading strategies, and automated
  systems using Python, PyTorch, and scikit-learn."
- OG: "The ultimate resource for algo traders. Curated videos, strategy ideas,
  backtested systems, and a complete trading automation framework."

---

## Folder map

| File | Contents |
|---|---|
| `01 - Where to start (the 8 steps).md` | The roadmap's 8 steps: 4 videos (Stop Trading By Hand; How to Build a Trading Bot; Generate 90+ Strategies; How to Actually Use AI in Trading — with YouTube IDs), Discord, FAQs, YouTube channel ("1,700+ hours"), daily private Zooms + the live question widget (`POST /api/roadmap/questions`) |
| `02 - FAQ (35 questions).md` | **All 35 FAQ Q&A verbatim**, including the 4 with links (Algo Trade Camp, CCXT exchange list, free Discord, Stripe billing portal) |
| `03 - RBI System.md` | **RBI = Research → Backtest → Incubate**: full method, both expandable code examples (Bollinger breakout backtest w/ optimization; bot schedule loop), incubation checklist ($10 tiny size, check every 12h), "Key Insight" |
| `04 - Alpha Generation & Strategies.md` | **~150 strategy ideas** in 13 categories (random ideas, technical indicators w/ 3 code snippets, volume/order flow, crypto-specific incl. funding-rate & liquidation hunting, mean reversion, momentum, options, market structure, quant, book-derived, risk management, experimental incl. **weather patterns**) + the "ideas to research" disclaimer |
| `05 - Book List.md` | 19 trading books, 5 technical, 14 mind books (with his "not read yet" notes) |
| `06 - Moon Dev AI Agents.md` | "This is War" section — agents GitHub now lifetime-members-only after a hack claim |
| `07 - Crypto Data (OHLCV downloader).md` | The OHLCV downloader: 30 symbols, 7 timeframes, weeks selector, API endpoints (`/api/data-downloader/download`, `/status/`), CSV format `timestamp,open,high,low,close,volume` from Coinbase |
| `08 — see subfolder` | → `Code From Videos/` |
| `09 - Reviews & Testimonials/` | README + **88 testimonial screenshots** in `images/` |
| `10 - Contact, official links & disclaimer.md` | Footer: warning banner, email, twitter, YouTube, Discord, full disclaimer + CFTC disclaimer |
| `11 - Site nav (Apps dropdown).md` | The header "Apps" dropdown (14 site-wide app links) — recorded, not crawled |
| `Code From Videos/` | **17 full bot tutorial pages** (article + complete source code each, ~700KB of markdown) — see its README for the table |

## Code From Videos — the 17 pages (quick list)

1. `hip-3-liquidation-trading-bot` — trades HIP3 liquidation cascades (Mar 7 2026)
2. `hip-3-funding-rate-scanner` — funding scanner for every HIP3 asset (Mar 8)
3. `polymarket-hyperliquid-liquidation-statistical-arbitrage` — liquidation stink bids on Polymarket hedged on Hyperliquid (Mar 11)
4. `polymarket-five-minute-bot` — "Easy Hyper Gambler": B/S/X keyboard bot, limit orders at 10% discount under bid (Mar 15)
5. `cvd-five-minute-bot` — order-flow alpha on 5-min markets (Mar 16)
6. `macd-five-minute-backtest` — Polymarket BTC MACD backtest (Mar 19)
7. `macd-histogram-filter-backtest` — signal-quality filter (Mar 19)
8. `xgboost-raw-candles-polymarket` — XGBoost raw-candle ML pipeline for BTC 5-min (Mar 20)
9. `polymarket-redemption-bot` — multi-account & batch MultiSend redemption (Mar 23)
10. `polymarket-weather-scanner` — mispriced temperature markets, 51-model ensemble forecasts (Mar 27)
11. `polymarket-whale-scanner` — live $1,000+ trade WebSocket stream (May 17)
12. `polymarket-smart-money-whale-scanner` — live $2K+ buys from profitable traders only (May 31)
13. `polymarket-95-cent-bid-sniper` — patient, **maker-only** bot (Jun 7)
14. `btc-etf-flow-tracker` — terminal chart + live OLS flow estimator (Jul 6)
15. `polymarket-strike-cross-sniper` — **mid-price lag taker** bot (Jul 17)
16. `hyperliquid-liquidation-magnet-bot` — liquidation imbalance trading (Jul 29)
17. `jev-astra-fable-polymarket-5-minute-bot` — three-agent 5-minute bot (Sep 26)

## External links found on the roadmap page (complete inventory)

| Link | Where |
|---|---|
| https://moondev.com/discord → https://discord.gg/gQv5sqZkkn | Step 5, FAQ #23, banner card |
| https://www.youtube.com/@moondevonyt/videos | Step 7 |
| https://www.youtube.com/watch?v=xSaNOtqEeN4 / jz3tEsCcie0 / h5rufR8asM0 / JwGfdnnyUAs | Steps 1–4 videos |
| https://moondev.com/live | Step 8, AI Agents CTA |
| https://algotradecamp.com/?utm_source=roadmap | FAQ #2, testimonials CTA |
| https://github.com/ccxt/ccxt/wiki/Exchange-Markets | FAQ #18 |
| https://billing.stripe.com/p/login/bIY4h63H89bKdQ4000 | FAQ #25 |
| mailto:moon@algotradecamp.com | FAQ #26/#27, footer |
| https://twitter.com/MoonDevOnYT · https://www.youtube.com/@moondevonyt · https://moondev.com | footer |
| 2 clickfunnels screenshot images (RBI section proof shots) | inline — included among the 88 downloaded (`testimonial-21`, `testimonial-75`) |

## Why this folder matters to our stack (annotations)

1. **`polymarket-five-minute-bot`** is the public reference for exactly our venue:
   288 BTC 5-min markets/day, and his entry trick is *limit orders 10% under bid* —
   a maker-fishing pattern, consistent with our maker-first design. He calls it
   gambling ("Easy Hyper Gambler") — see `VENUE-TRUST-MODEL.md` for why ours isn't:
   he taker-gambles, we measure-then-make.
2. **`polymarket-95-cent-bid-sniper`** is explicitly *maker-only* and patient — the
   same "be a maker" convergence we found in the Reddit thread; his −5.5% passive-MM
   result (marv Part 4) is the bar our OPEN-BOOK-MAKER sim must beat.
3. **`polymarket-strike-cross-sniper`** ("mid-price lag taker") is an independent
   public confirmation that **book-vs-fair-value lag exists and is exploitable** on
   these markets — the same edge family as our fourth witness (Chainlink-vs-book skew).
4. **`polymarket-weather-scanner`** validates our weather thesis: he scrapes tomorrow's
   temperature markets, ensembles **51 Open-Meteo models**, and flags forecast-vs-price
   edges. Independent prior art for our weather carry work — worth a read-through.
5. **`polymarket-whale-scanner` + `smart-money-whale-scanner`** are public designs for
   the flow-capture recorder we already run (ours is chain-verified; his are API-only).
6. **`xgboost-raw-candles-polymarket`** is the ML approach he settled on for BTC 5-min:
   raw-candle features → XGBoost, *predicting the round outcome*, and per FAQ #11 his
   stated view: ML should predict regime/when-to-run, not price. Same philosophy as our
   harness-first design.
7. **FAQ #20** (backtest fees at 2–3× exchange fee for slippage) and **RBI incubation**
   ($10 start, check every 12h) match our house rules almost word for word — external
   validation of the stakes ladder.
8. ⚠️ The AI-agents GitHub is **members-only now**; no public repo to audit. Anything
   claiming to be it elsewhere is suspect.
