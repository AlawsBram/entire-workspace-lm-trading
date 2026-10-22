# OPEN-BOOK MAKER — the "be first at the open" limit-order strategy

Date: 2026-09-27 · Status: DESIGNED, awaiting opening-flow data + pilot approval
Docs basis: `Entire Predictions Tab Polymarket/` (Prices & Orderbook, Fees,
Maker Rebates, Order Lifecycle, Market Making) + our own measured data.

## 1. The idea (as stated)
When a round/market opens, be the FIRST to place limit orders. Early takers
cross the spread and get filled against us. Whatever doesn't fill, we cancel.

## 2. Why the mechanics support it (documented facts)
- **All orders are limit orders**; `post-only` guarantees maker status —
  a post-only order that would cross is rejected, so we can NEVER accidentally
  pay a taker fee.
- **Makers are never charged fees.** Takers pay `C × feeRate × p × (1-p)` —
  crypto rounds: feeRate 0.07 → 1.75¢/share at 50¢; weather: 0.05.
- **Maker Rebates**: filled maker liquidity earns 20% of the taker fee it
  generated (crypto) / 25% (weather), paid daily in pUSD. Getting filled is
  doubly paid: the spread + the rebate.
- **GTD (Good-Till-Date)** order type auto-cancels at a set time → the
  "cancel what didn't fill" step can be built INTO the order (no race).
- **Complementarity**: bidding NO at 0.46 ≡ asking YES at 0.54 — the book
  treats both sides natively.
- **Price discovery at open**: the first YES-bid + NO-bid that sum to ≥ $1
  mint a pair. Early on, the book is literally being built by whoever posts
  first — queue position at open is the whole game.

## 3. The core trade: "Opening Straddle Maker"
Post **post-only GTD bids on BOTH outcomes** slightly inside fair, e.g. at
round open (fair = 0.50 exactly, by construction of updown rounds):

```
YES bid @ 0.46 × N shares
NO  bid @ 0.46 × N shares      (GTD expiry = open + 20 seconds)
```

Three outcomes, all bounded:
| fills | position | result |
|---|---|---|
| BOTH sides | 1 YES + 1 NO for $0.92 | **$1.00 guaranteed at settlement: +8¢/pair (8.7% in 15 min) + rebates, zero direction risk** |
| ONE side | e.g. YES @ 0.46 | bought a ~50/50 at 46¢: +4¢ edge vs fair; manage per §4 |
| NONE | nothing | cost $0 — cancel everything, wait for next round |

## 4. Managing the one-sided fill (the only real risk)
The taker who lifted your bid may have momentum info (BTC moved in the first
seconds). Rules, all automatable:
1. **Skew with the BRTI proxy** (live in us_round_recorder): if BTC is already
   ≥ X bps above round-open at quote time, drop the YES bid / raise the NO bid
   proportionally — never quote a side the oracle says is overpriced.
2. **Pull-on-move**: any proxy move > 3 bps inside the quoting window →
   cancel all resting (GTD is the backstop, this is the active defense).
3. **Pair-completion**: after a one-sided fill, immediately quote the opposite
   side at fill_price + 2–3¢; if it fills, you've locked the straddle late.
4. **Hard exit**: T−60s to close, if still one-sided: sell into the book if
   bid ≥ entry, else hold (a 46¢ coin-flip is still +EV vs settlement).
5. Max N shares per side per round sized to the $10/$20 daily limits.

## 5. What we measured that de-risks this
- **Resting orders DO get sold into**: 1,426 fills observed in a partial
  session; median gap between fills 0.2s in active rounds. The tape is
  continuous — whoever rests at best price gets lifted.
- **Depth at 40–60¢**: ~17,000 shares/side at top level (~$8.5k) — ample for
  $10–100 sizing; our fills won't move anything.
- **Books go one-sided late** (bestAsk null near settlement) — hence the
  T−60s hard-exit rule; never depend on an exit path in the final minute.
- Fee math at 46¢: our post-only fills cost us 0; each taker filling us pays
  ~1.7¢/share of which ~0.34¢/share returns to us as rebate (crypto tier).

## 6. What we still must measure (recorder now capturing it)
The recorder pre-subscribes to NEXT rounds (patched 2026-09-27), so from the
next open we capture:
- t(first quote) − t(round start): how early the maker race actually starts
- depth growth curve in the first 60s
- size of the opening taker burst and who gets filled at what level
- whether the house MM pre-empts the open (if so, we quote ONE tick inside
  their opening level instead of racing to 0.46)
This data decides the quote level (0.46 vs 0.48) and the GTD window (20s vs 60s).

## 7. Execution venues (both fit the same logic)
- **.com CLOB (5m/15m rounds)**: py-clob-client, EIP-712 signed orders,
  documented Place/Cancel APIs — fastest path to a $10 pilot (burner wallet,
  user-held keys per standing rules).
- **US venue (15m/1h rounds)**: needs an account + KYC first; same strategy,
  and the US fee docs match this structure. Weather buckets (25% rebate tier)
  are the same play on a slower clock — quote around the frontier bucket after
  each NWS update instead of at a round open.

## 8. Backtest before live
Extend `maker_lab/maker_sim.py` with an OPEN-BURST module: replay archived
opening seconds (once recorded), simulate our two-sided GTD quotes at
varying levels/windows, output: both-fill rate, one-side rate, PnL incl.
rebates, worst drawdown. Gate: positive expectancy across ≥100 simulated
opens before any live order. Then $10 pilot, one round at a time, full log.

## 9. Honest expectation
This is a real maker strategy with bounded downside and a genuine structural
edge (rebates + zero maker fees + queue priority at open). It is NOT a
money-printer: realistic capture at $10–100 size is cents-to-a-few-dollars
per day, compounding slowly. It's the correct vehicle for the step-ladder —
survivable by design, and every fill teaches the model.
