# PAIR-MM INVESTIGATION — pre-registered stages (2026-10-15)

## 0. The mechanism in one paragraph
Two-sided maker on the redundant pair: rest bids on Up AND Down that sum to ~0.97;
a completed pair redeems $1.00 at resolution → ~3¢ per pair. Economics =
pairs/day × pair-spread − naked-leg adverse selection. gabigol (24 h, 2026-09-28,
as profiled): 7,422 maker fills, ~3,700 pairs, 97% completion, +$2,088 pairs,
−$423 naked legs (over-held side won 32%), +$144 rebate, max capital tied $381.

## 1. Their own latency table, decomposed (why "find latency fixes" is question #2)

| comparison | gap | what it actually measures |
|---|---|---|
| gabigol live +$978 vs replay-at-0s +$199 | **+$779** | TECHNIQUE not in the replay: queue persistence, resting at touch / 1 tick better, cancel anticipation |
| replay 0s +$199 vs 0.2s −$47 | −$246 | reaction latency 0→200 ms |
| replay 0.2s −$47 vs 1.0s −$181 | −$134 | reaction latency 200→1000 ms |

Their numbers say the technique gap is **3.2× the entire latency gap**. "He cancels
before the price runs through him" is anticipation/queue behaviour, not reaction
milliseconds. Searching for a faster server first = optimizing the smaller term while
the bigger term is still unspecified. Second: the replay's fill/queue model is the same
family that invented fills on frozen books in the #11 zip (E3/E5). Until the sim
reproduces gabigol's ACTUAL 7,422 fills from his book states, the ladder is an
unvalidated model's opinion.

## 2. Base rates (written before any stage runs)
One wallet, one good day = survivorship candidate; we lost this family live twice;
his return-per-dollar fell 7× at 100× scale (their own note) = competition/decay.
Prior that this becomes live-positive after infra work: **15–25%**. Stage costs are
~zero until S4, so the investigation is still +EV as measurement.

## 3. Stages (each has a kill condition; ZERO capital until S4)

**S0 — existence (RUNNING NOW, probe_pair_spread.py, 1 Hz both books, live 5m rounds).**
Measures: how often bidUp+bidDown ≤ 0.98 / ≤ 0.97, at what top-of-book depth; quote
churn (cancel/replace race intensity); whether askUp+askDown < 1.00 ever prints.
KILL: ≤0.98 prints on <5% of seconds OR depth <20 shares when it prints → the pair
spread no longer exists at tradeable size → STOP, no infra story.

**S1 — replay audit (needs gabigol fills + replay code + its fill model from twapvm).**
Sim must reproduce the WINNER's fills (count ±10%, completion ±3 pts) from his book
states, else the fill model is fiction → rebuild or STOP. Then: technique-vs-latency
decomposition; then placement-policy variants at FIXED 0.2 s and 1.0 s (rest-at-touch /
1-tick-better / 2-tick; cancel thresholds; no-requote-after-fill). If a policy turns
positive at 1.0 s → infra unnecessary. KILL: no policy positive at ≤1.0 s AND S2 can't
reach the required budget.

**S2 — latency budget on current infra (no new spend).** Instrument components: book
update age via the venue's own CLOB websocket book channel (push, not 1 Hz REST poll —
architecture, not arms race); order/cancel RTT distributions; reaction p95. If p95
≤0.2 s is reachable on the current VPS with websockets, colocation never enters.

**S3 — region probe (passive, cheap).** TLS-handshake RTT to clob.polymarket.com from
candidate regions; choose best. Only if S1 says sub-0.2 s is binding AND S2 misses it.
Colocation cost vs expected edge decided on paper before any spend.

**S4 — live queue test (first capital: $500 tier, welded gate applies).**
≥200 rounds, pre-registered: pair completion ≥95% @20 shares; naked-leg win ≥35%;
post-cost EV/round > 0 (CI lower > 0); worst day ≤2% of capital; gate_pass.json lock.
KILL: any criterion fails → archive the family.

**S5 — scale only after S4 passes:** add ETH/SOL rounds (~780 markets/day); rebate
counted as kicker only after it is measured on our own fills.

## 4. House-rule tension — OWNER DECISION REQUIRED before S2 order-path work
RUNBOOK §9 says "Latency sniping = banned." The gabigol family is two-sided MAKING
(house payroll — he collected rebates), but its edge decays with reaction ms, which is
arms-race-adjacent. Proposed amendment: *banned = taker-side racing to pick off stale
quotes; permitted = maker-side queue competition iff the measured reaction budget
(S2/S3) sustains the sim edge and the S4 gate passes; no strategy claims maker-family
status on unmeasured infrastructure.* Owner approves or rejects in writing.

## 5. Reconciliation flags on the pasted numbers (verify at S1 from source data)
- 2,088 − 423 + 144 = 1,809 ≠ 1,694 → −115 unexplained (fees? rounding? missing line).
- "3,600 pairs" vs 7,422 fills ⇒ 3,711 pairs — consistent.
- 4.4%/day is on THROUGHPUT; on tied capital ($381) it is ~444%/day — a turnover
  machine whose sustainability question is competition, not capital.
- "zero as a taker" must be verified against his trade-history side field.

## 6. Needed from owner / VPS AI to start S1
(a) gabigol fill export (ts, side, price, size, order ids) + profiling script;
(b) the replay code + its fill/queue model + the 265-round book dataset;
(c) logs of our two live losses in this family (what completion % did we actually get).
