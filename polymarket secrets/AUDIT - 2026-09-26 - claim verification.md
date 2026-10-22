# DYUTAM ARTICLE — FULL CLAIM AUDIT (cross-reference vs Polymarket docs + live data)

**Audit date:** 2026-09-26 · **Article published:** ~2026-03-15 (6.5 months old)
**Auditor stance:** every falsifiable claim checked against (1) our mirrored Polymarket docs, (2) the CURRENT live docs (`docs.polymarket.com/llms-full.txt`, fetched today), (3) live market data measured today. Verdicts:
- **AGREE** — docs/live data confirm
- **STALE** — true at publication, changed since (official changelog date given)
- **DEAD** — the product/feature no longer exists
- **DISAGREE** — contradicted by docs/data even for its own time
- **NEWS-TIME** — external news claim, cited source exists; not re-litigated here
- **UNVERIFIABLE** — no public data source available

---

## A. FEE STRUCTURE (the part our money touches)

| # | Article claim (Mar 15) | Evidence today | Verdict |
|---|---|---|---|
| A1 | Max taker fee 1.56% at 50¢ | Live `feeSchedule` on 5m/15m: `feeType=crypto_fees_v2, rate=0.07` → 0.07×0.5×0.5 = **1.75%** at 50¢. Docs table: Crypto taker fee rate 0.07. Changed by **Fee Structure V2, Mar 30 2026** (15 days after publication). Our `trader.py` uses 0.07 — correct today. | **STALE** (article) / our code correct |
| A2 | Fee curve shape `fee ∝ p(1−p)`, max at 50¢ | Docs formula `fee = C × feeRate × p × (1−p)` unchanged | **AGREE** |
| A3 | Fee table: $0.50→1.56%, $0.30→0.9%, $0.10→0.13% | Today at rate 0.07: 0.50→**1.75%**, 0.30→**1.47%**, 0.10→**0.63%**. Round-trip ~3.5% not 3.12% | **STALE** |
| A4 | Makers pay zero | Docs table: Crypto maker fee rate 0 (all categories except top-tier perps) | **AGREE** |
| A5 | "100% of taker fees redistributed as daily USDC rebates to makers" | Current Maker Rebates page: "**A percentage** of these fees are redistributed… Crypto → **20%**, fee-curve weighted", paid in **pUSD**, not USDC | **STALE** (both % and currency) |
| A6 | Hourly crypto markets are fee-free (the onramp) | Official changelog **Mar 1 2026**: fees extend to all NEW crypto markets incl. 1H/4H/daily/weekly from Mar 6 — already partly stale AT publication. Today: hourly Up/Down markets **no longer exist at all** (slug probes `btc-updown-1h/60m/hourly-{start}` all empty; only hourly candle-count markets remain) | **STALE → DEAD** |
| A7 | Docs warn against hardcoding fees | Current docs expose per-market `feeSchedule` and say rates changed multiple times | **AGREE** |
| A8 | Speed bump (500ms) removed mid-Feb 2026, no announcement | Live: `seconds_delay=0` on 5m and 15m; official changelog has NO removal entry (silence confirmed); current docs now describe a separate 250ms taker delay (`itode`) for "selected" markets — NOT active on BTC 5m/15m today (`itode` key absent). Watcher now tracks both fields. | **AGREE** (+ new info) |

## B. VOLUME / MARKET STRUCTURE (measured live, all 288+96 BTC rounds of the last 24h)

| # | Article claim | Measured today | Verdict |
|---|---|---|---|
| B1 | 288 five-minute windows/day, 24/7 | 288/288 rounds resolved in last 24h; 96/96 15m | **AGREE** |
| B2 | $60M daily volume in 5-min crypto markets (Dune, March) | Summed lifetime volume of every round: BTC 5m **$11.82M** + BTC 15m $2.65M; other assets 5m: ETH $0.98M, SOL $0.35M, XRP $0.26M, DOGE/BNB/HYPE ≈ $0.12M → **≈ $13.5M/day in 5m, ~$16M incl. 15m**. ≈ 4.4× below the claim | **STALE** (volume collapsed further after the Feb removal) |
| B3 | BTC = 67% of crypto prediction volume | BTC 5m share today ≈ 11.8/13.5 ≈ **87%** (smaller assets drained faster) | **STALE** |
| B4 | 15-min weekly $260M→$143M after removal | Today's 15m ≈ $2.65M/day ≈ **$18.5M/week** — an order of magnitude below even the post-removal figure | **STALE** (direction right, magnitude moved on) |
| B5 | ~600 max taker transactions/window under the 500ms bump | Arithmetic: 300s ÷ 0.5s = 600 ✓; mechanism now absent | **AGREE (historical)** |
| B6 | Assets: BTC, ETH, SOL, XRP 5m markets | Live: also **HYPE, DOGE, BNB** 5m rounds exist now | **AGREE + expanded** |
| B7 | "Polymarket reportedly exploring 1-minute windows" | No 1m Up/Down markets exist today (slug probes empty) | **NOT MATERIALIZED** (rumor stands unconfirmed) |
| B8 | Resolution via Chainlink oracle on Polygon; tamper-resistant but not instantaneous | Our S1 arbiter validates settlement vs Chainlink 60s-TWAP daily (70/70 historically); docs confirm | **AGREE** |
| B9 | Displayed price "can be delayed by a few seconds" | Current docs: 250ms taker delay on selected markets + general oracle latency; our harness measures feed lag live | **AGREE (in spirit; exact disclosure wording moved)** |
| B10 | Fee extraction $400–600K/day, $150–200M/yr | At today's volume: ~$13.5M × ~1% avg ≈ **$135K/day** | **STALE** (formula right, input changed) |

## C. REGULATORY / EXTERNAL CLAIMS (news-time; cited sources verified to exist)

| # | Claim | Verdict |
|---|---|---|
| C1 | ESMA banned binary options EU-wide July 2018; 74–89% retail lost; €1.6k–29k avg losses | **NEWS-TIME / AGREE-WITH-CITATION** (ESMA Decision 2018/795 — real, matches public record) |
| C2 | UK FCA permanent ban 2019 | **AGREE-WITH-CITATION** (public record) |
| C3 | CFTC staff advisory Mar 12 2026 (sports-focused, ignored the crypto gap) | **AGREE-WITH-CITATION** (cftc.gov release 9193-26) |
| C4 | Palantir/TWG AI sports-integrity partnership Mar 10 2026 | **AGREE-WITH-CITATION** (BusinessWire) |
| C5 | Massachusetts v. KalshiEX; Netherlands ban late 2025; France enforcement | **NEWS-TIME** (consistent with our earlier research) |
| C6 | 0DTE = 59% SPX volume 2025; skew 4.47 / kurtosis 33.58 straddle backtest | **AGREE-WITH-CITATION** (Cboe) |
| C7 | Valuations: PM $9B (Oct 25, ICE $2B), Kalshi $11B (Dec 25), QCEX $112M, both chasing $20B | **NEWS-TIME, likely STALE as "current"** — six months of fundraising news since; treat as history |
| C8 | $18.3B combined monthly vol Feb 2026; $1.3B open interest; 36% US voters tried prediction markets | **NEWS-TIME** (The Block / Paradigm-Echelon) |
| C9 | Pending bills: Moore/Carbajal, Schiff DEATH BETS, Merkley/Klobuchar | **UNVERIFIED-HERE** — bill status as of Sept 2026 not checked; irrelevant to our trading stack |
| C10 | Iran-conflict insider trading: $529M wagered, $1.2M suspicious profit, 6 accounts | **NEWS-TIME** |
| C11 | Nasdaq binary-options SEC filing | **NEWS-TIME** |
| C12 | Data providers double-count prediction-market volume (Protos) | **NEWS-TIME** — note: makes B2's $60M even less trustworthy for March itself |

## D. WHERE ARTICLE AND DOCS FLATLY DISAGREE TODAY
1. **Rebate share:** article 100% vs docs 20% (crypto). → our maker-sim's 20% assumption is the correct one.
2. **Peak taker fee:** 1.56% vs 1.75%. → our 0.07 constant correct.
3. **Hourly fee-free onramp:** article advice vs product deleted. → advice is dead.
4. **Rebate currency:** USDC vs pUSD. → collateral naming migrated; watch funding flow.

## E. WHAT CHANGED Mar 15 → Sep 26 (official changelog dates)
- **Mar 17 2026** — March Madness liquidity rewards (2 days after the article).
- **Mar 30 2026** — **Fee Structure V2**: new categories + updated rates (crypto 0.07 → 1.75% peak).
- **Post-Mar** — collateral/rebates paid in **pUSD**; per-market rebate calculation (Feb 11) stands at 20% for crypto.
- **Post-Mar** — new 5m assets (HYPE, DOGE, BNB).
- **Post-Mar** — hourly Up/Down rounds **discontinued**.
- **Still absent:** 1-minute markets; speed bump (`seconds_delay=0`); no `itode` on BTC rounds today.

## F. IMPACT ON OUR STACK (actions taken / to take)
1. `trader.py` fee constant (0.07) — **correct**, keep. The article's 1.56% must NOT be used anywhere.
2. `maker_lab` rebate model (20%) — **correct**, keep. Rebate upside estimate already conservative.
3. Article's consumer advice "use fee-free hourly markets" — **DEAD**; removed from any future playbook references.
4. Volume sizing: plan against **~$13–16M/day** total, not $60M. Our $10 orders remain invisible either way; but liquidity-depth expectations for the maker family must use today's book, not March's.
5. `regime_watch.py` — **updated today** to also track `itode` (the 250ms taker-delay flag) so a silent re-introduction of any execution delay alerts us.
6. The article remains **directionally correct and structurally excellent** — its core theses (fee machine, maker alignment, rule-change risk, "you are the inefficiency") all still hold and are independently confirmed by our live measurements. It fails only on the *numbers that the venue itself changed afterward* — which is exactly the regime-change risk our whole stack is built around.

**Bottom line:** treat the Dyutam piece as a correct *model* with stale *parameters*. The model we use; the parameters we measure ourselves, daily.
