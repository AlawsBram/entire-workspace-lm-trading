#!/usr/bin/env python3
"""
passed_test.py — replay any strategy's PnL series through PROP FIRM evaluation
rules and count passes / deaths / stalls. Inspired by Moon Dev's prop-firm
stream (transcript archived in `Prop Firm Bots/`).

THE RULES (transcript-verified, configurable):
  * You pay a fee ($245) for a $50,000 SIMULATION account.
  * Pass  = equity reaches +9%  (54,500). No time limit.
  * Death = daily loss hits 3% of the day's starting equity (UTC days)
            OR equity hits the static max-drawdown floor (initial * 0.97 —
            the floor does NOT trail up when you profit).
  * Fail an attempt -> buy another one (fee again). Pass -> funded sim,
    80/20 split (80% to you), balance RESETS to 50k.

HOW WE SCORE OUR STRATEGIES:
  A strategy's per-round PnL (earned on its own tiny capital D, e.g. $10)
  becomes a per-round RETURN r = pnl / D. That return is applied to the prop
  equity:  E *= (1 + r * scale).  scale = what fraction of the prop account
  you'd deploy with the same relative sizing (default 1.0 = same % risk).
  This is honest: it asks "would the SHAPE of this PnL stream survive the
  floors?", not "would our $10 make $4,500".

INPUTS (adapters):
  --maker-csv  maker_lab/sim_rounds.csv        (round_start, pnl_usd)
  --s1-csv     s1_harness/backtest_s1_signals.csv (reconstructs $10/signal PnL
               with official fee 0.07*p*(1-p), per s1_harness backtest method)
  --csv F --ts-col C1 --pnl-col C2 --capital D  (generic)

OUTPUT: table of attempts + summary (pass rate, P(>=1 pass in N attempts),
costs), JSON dump. Restarts a fresh attempt after every pass/death, in
chronological order; end-of-data = stall.
"""
import argparse, csv, json, os, sys
from datetime import datetime, timezone

# ---- prop firm rule defaults (transcript values) ----
ACCOUNT      = 50_000.0
FEE          = 245.0
TARGET_PCT   = 9.0     # pass at +9%
DAILY_FLOOR  = 3.0     # die: daily loss >= 3% of day-start equity
MAX_DD_FLOOR = 3.0     # die: equity <= initial * (1 - 3%) — STATIC, no trail
SPLIT_TO_US  = 0.80

def day_of(ts): return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()

def auto_scale(ts_pnl, capital, worst_round_cap_pct=1.0):
    """Pick scale so the worst single-round |return| moves the prop account at
    most worst_round_cap_pct%. This is the honest prop-firm question: sized to
    fit the floors, does the stream reach the target before variance kills it?"""
    rets = [abs(pnl / capital) for _, pnl in ts_pnl if capital]
    if not rets: return 1.0
    worst = max(rets)
    if worst == 0: return 1.0
    return min(1.0, (worst_round_cap_pct / 100.0) / worst)

def replay(ts_pnl, capital, scale=1.0, account=ACCOUNT, target=TARGET_PCT,
           daily=DAILY_FLOOR, maxdd=MAX_DD_FLOOR):
    """Run the attempt loop over a chronological (ts, pnl) series."""
    attempts, cur = [], None
    def fresh(idx):
        return dict(start_idx=idx, equity=account, day=None, day_start=account,
                    peak=account, worst_daily=0.0, worst_dd=0.0, rounds=0)
    cur = fresh(0)
    for i, (ts, pnl) in enumerate(ts_pnl):
        if cur is None: cur = fresh(i)
        d = day_of(ts)
        if cur["day"] != d:
            cur["day"], cur["day_start"] = d, cur["equity"]
        r = pnl / capital if capital else 0.0
        cur["equity"] *= (1.0 + r * scale)
        cur["rounds"] += 1
        day_loss = (cur["day_start"] - cur["equity"]) / cur["day_start"] * 100
        dd = (account - cur["equity"]) / account * 100   # vs STATIC initial
        cur["worst_daily"] = max(cur["worst_daily"], day_loss)
        cur["worst_dd"] = max(cur["worst_dd"], dd)
        if cur["equity"] >= account * (1 + target / 100):
            cur["result"] = "PASS"; attempts.append(cur); cur = None
        elif dd >= maxdd or day_loss >= daily:
            cur["result"] = "DEATH"
            cur["cause"] = "daily-floor" if day_loss >= daily else "max-dd-floor"
            attempts.append(cur); cur = None
    if cur is not None and cur["rounds"] > 0:
        cur["result"] = "STALL"; attempts.append(cur)
    return attempts

def summarize(name, attempts, fee=FEE, n_buy=5):
    n = len(attempts)
    p_ = sum(1 for a in attempts if a["result"] == "PASS")
    d_ = sum(1 for a in attempts if a["result"] == "DEATH")
    s_ = sum(1 for a in attempts if a["result"] == "STALL")
    decided = p_ + d_
    rate = (p_ / decided * 100) if decided else None
    p_at_least_one = (1 - (1 - p_ / decided) ** n_buy) * 100 if (rate is not None and decided) else None
    return dict(strategy=name, attempts=n, passes=p_, deaths=d_, stalls=s_,
                pass_rate_pct=round(rate, 1) if rate is not None else None,
                cost_per_attempt_usd=fee,
                cost_n_buy_usd=round(fee * n_buy, 2),
                p_at_least_one_pass_in_n=round(p_at_least_one, 1) if p_at_least_one is not None else None,
                worst_daily_loss_pct=round(max((a["worst_daily"] for a in attempts), default=0), 2),
                worst_drawdown_pct=round(max((a["worst_dd"] for a in attempts), default=0), 2),
                rounds_total=sum(a["rounds"] for a in attempts))

# ---- adapters ---------------------------------------------------------------
def load_maker(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                pnl = float(r.get("pnl_usd") or 0)
            except ValueError:
                continue
            if not r.get("pnl_usd"):  # unsettled rows carry no pnl
                continue
            rows.append((int(float(r["round_start"])), pnl))
    rows.sort()
    return rows, None  # capital supplied on CLI

def load_s1(path, bet=10.0):
    """Reconstruct per-signal PnL: $bet buys shares at synthetic_price; win pays $1/share.
    Official fee 0.07*p*(1-p)*shares (s1_harness method)."""
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                ts = int(float(r["round_start"])); p = float(r["synthetic_price"])
                win = str(r.get("win", "")).strip().lower() == "true"
            except (KeyError, ValueError):
                continue
            if p <= 0 or p >= 1: continue
            shares = bet / p
            fee = 0.07 * p * (1 - p) * shares
            pnl = (shares - bet - fee) if win else (-bet - fee)
            rows.append((ts, pnl))
    rows.sort()
    return rows, bet

def load_generic(path, ts_col, pnl_col):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try: rows.append((int(float(r[ts_col])), float(r[pnl_col])))
            except (KeyError, ValueError, TypeError): continue
    rows.sort()
    return rows, None

# ---- main --------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Prop-firm rule checker")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--maker-csv")
    src.add_argument("--s1-csv")
    src.add_argument("--csv")
    ap.add_argument("--name", default=None)
    ap.add_argument("--ts-col", default="round_start")
    ap.add_argument("--pnl-col", default="pnl_usd")
    ap.add_argument("--capital", type=float, default=None,
                    help="capital the PnL was earned on (default: 200/side for maker = QUOTE_SIZE*2*0.5)")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--auto-scale", action="store_true",
                    help="size the strategy so its worst round moves the account <= --worst-round-cap")
    ap.add_argument("--worst-round-cap", type=float, default=1.0)
    ap.add_argument("--show", type=int, default=12, help="max attempts to print in detail")
    ap.add_argument("--account", type=float, default=ACCOUNT)
    ap.add_argument("--fee", type=float, default=FEE)
    ap.add_argument("--target", type=float, default=TARGET_PCT)
    ap.add_argument("--daily-floor", type=float, default=DAILY_FLOOR)
    ap.add_argument("--maxdd-floor", type=float, default=MAX_DD_FLOOR)
    ap.add_argument("--n-buy", type=int, default=5, help="attempts to model for P(>=1 pass)")
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()

    if a.maker_csv:
        rows, cap = load_maker(a.maker_csv)
        name = a.name or f"OPEN-BOOK-MAKER ({os.path.basename(a.maker_csv)})"
        capital = a.capital if a.capital else 200.0   # 2 sides * 20 shares * ~$0.50
    elif a.s1_csv:
        rows, cap = load_s1(a.s1_csv)
        name = a.name or f"S1 taker signals ({os.path.basename(a.s1_csv)})"
        capital = a.capital if a.capital else cap
    else:
        rows, cap = load_generic(a.csv, a.ts_col, a.pnl_col)
        name = a.name or os.path.basename(a.csv)
        capital = a.capital or cap
        if not capital:
            sys.exit("--capital required for generic CSV")

    if not rows:
        print(f"{name}: NO SETTLED PnL ROWS — nothing to score yet.")
        return
    if a.auto_scale:
        a.scale = auto_scale(rows, capital, a.worst_round_cap)
    span_h = (rows[-1][0] - rows[0][0]) / 3600
    print(f"== {name} ==")
    print(f"rows={len(rows)} span={span_h:.1f}h capital=${capital:.2f} "
          f"scale={a.scale:.4f} rules: acct ${a.account:,.0f} target +{a.target}% "
          f"daily -{a.daily_floor}% maxDD -{a.maxdd_floor}% (static) fee ${a.fee}")
    attempts = replay(rows, capital, a.scale, a.account, a.target,
                      a.daily_floor, a.maxdd_floor)
    for i, at in enumerate(attempts[:a.show], 1):
        print(f"  attempt {i}: {at['result']:<5} rounds={at['rounds']:<4} "
              f"end_equity=${at['equity']:,.0f} worst_daily={at['worst_daily']:.2f}% "
              f"worst_dd={at['worst_dd']:.2f}%" + (f" cause={at.get('cause','')}" if at.get('cause') else ""))
    if len(attempts) > a.show:
        print(f"  ... {len(attempts) - a.show} more attempts (see --json-out)")
    s = summarize(name, attempts, a.fee, a.n_buy)
    print("  summary:", json.dumps({k: v for k, v in s.items() if k != 'strategy'}, indent=None))
    if s["stalls"] and not (s["passes"] or s["deaths"]):
        print("  VERDICT: INSUFFICIENT DATA — the stream never reached a pass or a floor.")
        print("           Re-run once more rounds are captured (target >=200).")
    if a.json_out:
        json.dump(dict(summary=s, attempts=attempts), open(a.json_out, "w"), indent=2)
        print(f"  wrote {a.json_out}")

if __name__ == "__main__":
    main()
