# VENUE TRUST MODEL — adversarial-venue threat analysis

_Last updated 2026-10-07. Append-only; do not delete entries — supersede them
with dated replacements instead. Cross-refs: HANDOFF-PROMPT.md §1 (data trust
model), MASTER-RUNBOOK.md §9 (house rules), regime_watch/README.md._

This file answers ONE question for future sessions: **"What if the venue is
hostile?"** The conclusion is designed to be reached once and inherited: we
never need to settle the conspiracy question, because the stack is built so
venue hostility cannot cost us more than the stakes ladder.

---

## 1. The three claims (user-raised 2026-10-07) and their evidence status

### Claim A — "They regime-change outsiders who find profitable edges"
**Status: TRUE — documented behavior, not a theory.**
- marv's `Polymarket+Kalshi Secrets` series opens with this thesis; the
  gabigool-style episode (visible winner → venue response) is the canonical
  example. Needs no malice beyond margin protection.
- **Mitigations already built:** regime_watch sentinel + changelog mirrors,
  edge-decay assumption baked into all sim gates, KILL switch,
  measure-don't-attack scope (we never give them a reason to target us).
- Rule: treat every validated edge as perishable. Any pattern that starts
  working is assumed to be regime-able until proven otherwise.

### Claim B — "Winners are planted by the venue to lure the crowd"
**Status: strong form UNSUPPORTED (and structurally expensive); weak form
PLAUSIBLE and assumed.**
- Strong form (venue wallets placed to win against real users): expensive to
  run because EVERYTHING is on-chain — every wallet, trade, and funding path
  is forensically auditable; a venue-funded winning wallet would be visible,
  and Polymarket's entire marketing is on-chain trustlessness. Getting caught
  deletes the product, especially while a dozen+ states sue the space
  (see `Polymarket+Kalshi Secrets/YouTube transcript - More Perfect Union -
  scam expose.md`). They also don't need it: the real 0.04% winners already
  market the platform for free, and retail loss data (Citizens Bank: traders
  lost more than at sportsbooks in months 1–3) supplies the lure.
- Weak forms — ASSUME TRUE, design around:
  - wash-traded volume for optics (inflates quoted depth),
  - insider humans (venue-adjacent people, not wallets) trading non-public
    knowledge — the transcript documents this class (GTA VI dates, oil ahead
    of announcements; Robin Hanson: insiders are "great" for accuracy),
  - UMA resolution influence in contested markets.

### Claim C — "We can't know, because we're not the casino"
**Status: TRUE — permanent information asymmetry.**
- We never see internal order flow, affiliate relationships, or rule-making
  deliberations. Unfalsifiable theories cannot guide action; bounded exposure
  can.
- **The stack's answer:** our PnL is verified on-chain against OUR OWN fills
  (`maker_lab/chain_verify.py`), never against venue dashboards or
  leaderboards; edges are mechanical/whale-identity-agnostic (opening skew,
  oracle lag, maker rebates — a shill's flow is just noise to quote against);
  max exposure is the $10→$50–100 stakes ladder with a $20/day stop; KILL
  switch + regime alerts mean the moment the venue turns, we're flat.
- If all three claims were 100% true simultaneously, worst-case damage to us
  is capped by the ladder. That is the point of the design.

---

## 2. Occam correction (kept for honesty)

"They regime-change to HIDE their secret" has a simpler observed explanation
in every documented case: **stop fee/profit leakage.** Motive doesn't change
our defense — the posture is identical either way. Do not spend cycles
litigating the conspiracy question; spend them measuring.

## 3. Operational implications (adopted)

1. **Quoted book depth is untrusted.** If some volume is wash flow, liquidity
   measurements overstate real depth. Verify via OBSERVED fills, not quoted
   depth. Applies to OPEN-BOOK-MAKER slippage assumptions and all ui_lab
   liquidity probes.
2. **Strategy #9 (copytrading) is dead with extra confidence.** If top
   wallets might be planted, copying them ranges from worthless to adversarial
   bait. Marv's persistence 0.035 already buried it; this nails the coffin.
3. **Our edges are whale-agnostic.** Microstructure/mechanical edges work
   against any flow. No strategy in the stack may depend on the identity or
   honesty of any counterparty.
4. **Optional future module (not built):** on-chain audit of top-winner
   wallets — win-rate distribution, clustering on thin-info markets
   (insider signature) vs high-frequency rounds (latency/skill signature),
   taker-fee patterns. Passive, read-only, in scope if ever requested.

## 4. Standing principles derived from this analysis

- Trust measured data over docs; trust chain over venue; trust our own fills
  over everything.
- Never hold an exposure that a hostile venue could expand beyond the ladder.
- Regime change is expected weather, not an emergency — protocol is in
  MASTER-RUNBOOK §7 (stay dry, re-validate, then resume).
- The venue is a rule-making marketplace that rakes; it is not assumed to be
  a directional player, and our plan must survive both possibilities.
