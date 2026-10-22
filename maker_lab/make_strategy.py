#!/usr/bin/env python3
"""
make_strategy.py — quoting strategy v1 + fill model + accounting (pure, testable)

STRATEGY (two-sided fair-value market making on BTC up/down rounds):
  fair = S1-verified model probability that the round settles Up.
  Quote both sides around fair with a target half-spread; join the book when
  fair is outside our quotes; skew is automatic because quotes are fair-anchored.
  Hard rules:
    - only quote when fair in [FAIR_LO, FAIR_HI]  (inventory control: at extreme
      fair you're picking up a falling knife)
    - stop quoting in the last NO_QUOTE_SECS of the round (settlement gamma:
      a print in the final seconds decides everything; makers get run over)
    - keep resting spread <= MAX_SPREAD (rewards-program eligibility: 3.5c)
    - size = QUOTE_SIZE (rewards min_size = 200 shares on sampled markets)
    - stop quoting the side that pushes net inventory past MAX_NET_SHARES

FILL MODEL (deliberately conservative — no queue-position data available):
  a resting bid is assumed lifted when the next observed best-bid trades down
  through our price; each crossing fills with probability QUEUE_FILL_PROB (0.5).
  Symmetric for asks. Same model in live mode and replay mode.

REBATES/REWARDS: intentionally NOT counted in PnL. Zero maker fee is applied
(the venue's published maker fee for these markets), the 20% taker-fee rebate
and liquidity rewards are reported separately as upside.

Everything is denominated in USDC. BUY = we bought Up shares (rested bid lifted);
SELL = we sold Up shares (rested ask lifted; short Up = long Down in a binary).
"""

# ---- config (all tunable, all logged) ---------------------------------------
HALF_SPREAD   = 0.015      # 1.5c target each side of fair
MIN_SPREAD    = 0.010      # never rest tighter than 1c total capture target
MAX_SPREAD    = 0.035      # rewards-program ceiling (sampled markets)
FAIR_LO       = 0.08
FAIR_HI       = 0.92
NO_QUOTE_SECS = {"5m": 20, "15m": 30}
QUOTE_SIZE    = 200.0
MAX_NET_SHARES = 400.0
QUEUE_FILL_PROB = 0.5
MAKER_FEE     = 0.0        # venue charges makers zero on these markets

class Book:
    def __init__(self, bids, asks):
        self.bids = bids or []   # [(price, size)] sorted desc
        self.asks = asks or []   # [(price, size)] sorted asc
    @property
    def bb(self): return self.bids[0][0] if self.bids else None
    @property
    def ba(self): return self.asks[0][0] if self.asks else None

def decide_quotes(fair_p, t_rem, label, net_shares):
    """returns (bid, ask) resting prices or None. Pure function of state."""
    if fair_p is None or not (FAIR_LO <= fair_p <= FAIR_HI):
        return None
    if t_rem is not None and t_rem < NO_QUOTE_SECS.get(label, 30):
        return None
    bid = fair_p - HALF_SPREAD
    ask = fair_p + HALF_SPREAD
    if ask - bid < MIN_SPREAD:
        mid = (bid + ask) / 2
        bid, ask = mid - MIN_SPREAD / 2, mid + MIN_SPREAD / 2
    if ask - bid > MAX_SPREAD:
        bid, ask = fair_p - MAX_SPREAD / 2, fair_p + MAX_SPREAD / 2
    bid = round(max(0.001, min(bid, 0.999)), 3)
    ask = round(max(bid + 0.001, min(ask, 0.999)), 3)
    # inventory guard: stop feeding the side that grows exposure
    if net_shares >= MAX_NET_SHARES:  return (None, ask)
    if net_shares <= -MAX_NET_SHARES: return (bid, None)
    return (bid, ask)

def detect_fills(prev_book, new_book, quote, rng):
    """given last book, new book and our resting quote -> list of fills
       [(side, price, size)] with side in {'BUY','SELL'} (of Up shares)."""
    fills = []
    if quote is None or prev_book is None or new_book is None: return fills
    qb, qa = quote
    # our resting bid lifted: sellers pushed best bid down through qb
    pb, nb = prev_book.bb, new_book.bb
    if qb is not None and pb is not None and nb is not None and nb < qb <= max(pb, qb):
        if rng.random() < QUEUE_FILL_PROB:
            fills.append(("BUY", qb, QUOTE_SIZE))
    # our resting ask lifted: buyers pushed best ask up through qa
    pa, na = prev_book.ba, new_book.ba
    if qa is not None and pa is not None and na is not None and na > qa >= min(pa, qa):
        if rng.random() < QUEUE_FILL_PROB:
            fills.append(("SELL", qa, QUOTE_SIZE))
    return fills

class RoundAccount:
    """per-round fill ledger + settlement valuation"""
    def __init__(self):
        self.fills = []          # (t, side, price, size, fair_at_t)
        self.n_quotes = 0
    @property
    def net_shares(self):
        return sum(s if side == "BUY" else -s for _, side, _, s, _ in self.fills)
    def add(self, t, side, price, size, fair):
        self.fills.append((t, side, price, size, fair))
    def settle(self, settled_up):
        """realized PnL in USDC at resolution. maker fee = 0."""
        payoff = 1.0 if settled_up else 0.0
        pnl = 0.0
        for _, side, price, size, _ in self.fills:
            if side == "BUY":
                pnl += (payoff - price) * size
            else:
                pnl += (price - payoff) * size
        return pnl - MAKER_FEE * sum(s for _, _, _, s, _ in self.fills)
    def adverse_selection(self, settled_up):
        """mean realized edge per filled share: >0 means our fair-value anchor
           was RIGHT about where the round ended (we weren't picked off)."""
        if not self.fills: return None
        payoff = 1.0 if settled_up else 0.0
        es = []
        for _, side, price, size, _ in self.fills:
            edge = (payoff - price) if side == "BUY" else (price - payoff)
            es.append(edge)
        return sum(es) / len(es)
