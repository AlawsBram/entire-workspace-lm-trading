#!/usr/bin/env python3
"""Q1 W1 backtest: ensemble-style prob model (calibrated deterministic forecasts) vs
crowd bucket prices. Fit bias/sigma on first 60% of days per (city,lead); ALL reported
trade metrics on the 40% holdout. Pre-registered: BACKTEST-QUEUE.md Q1."""
import sys, os, json, statistics as st, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

def bin_interval(b):
    # VENUE RULE (verified 2026-10-21 via gamma rules text + hk weather bot repo):
    # buckets are RANGES with FLOOR cut-off (31.9 counts as 31) -> [b, b+1).
    kind, v = b[0], b[1]
    if kind == "le": return (-99.0, v + 1.0)
    if kind == "ge": return (v, 99.0)
    if kind == "between": return (v[0], v[1] + 1.0)
    return (v, v + 1.0)

def mid_of_win(ev):
    for bk in ev["buckets"]:
        if bk["won"]:
            lo, hi = bin_interval(bk["bin"])
            return (lo + hi) / 2 if abs(lo) < 50 and abs(hi) < 50 else (hi - 1.5 if lo < -50 else lo + 1.5)
    return None

def price_at(tok, ts):
    try: h = load(f"px_{tok[:16]}.json")
    except Exception: return None, None
    pts = [p for p in h if p["t"] <= ts]
    if not pts: return None, None
    last = pts[-1]
    age_h = (ts - last["t"]) / 3600
    return last["p"], age_h

def main():
    cities = load("cities_kept.json")
    rows = []          # (city, lead, day, bucket..., prob, price, ask, won, holdout)
    for city in cities:
        wx = load(f"wx_{city}.json"); evs = load(f"events_{city}.json")
        days = sorted({e["end"][:10] for e in evs})
        nfit = max(1, int(len(days) * SPLIT))
        fit_days, hold_days = set(days[:nfit]), set(days[nfit:])
        ev_by_day = {e["end"][:10]: e for e in evs}
        for lead in ("L0", "L1", "L2", "L3"):
            def fcu(d):
                fc = wx.get(lead, {}).get(d); mw = mid_of_win(ev_by_day[d])
                if fc is None or mw is None: return None
                u = ev_by_day[d]["buckets"][0]["bin"][2]
                fc = fc if u == "C" else fc * 9 / 5 + 32
                return fc - mw
            res = [x for x in (fcu(d) for d in days) if x is not None]
            if len(res) < 8: continue
            fr = res[:max(1, int(len(res) * SPLIT))]
            bias = st.mean(fr); sigma = max(st.pstdev(fr) if len(fr) > 2 else 1.0, 0.6)
            for ev in evs:
                d = ev["end"][:10]
                fc = wx.get(lead, {}).get(d)
                if fc is None: continue
                u = ev["buckets"][0]["bin"][2]
                fc = fc if u == "C" else fc * 9 / 5 + 32
                mu = fc - bias
                for bk in ev["buckets"]:
                    lo, hi = bin_interval(bk["bin"])
                    prob = norm_cdf((hi - mu) / sigma) - norm_cdf((lo - mu) / sigma)
                    if prob < MIN_PROB: continue
                    ts = None
                    tz = CITIES[city][2]
                    dd = dt.date.fromisoformat(d)
                    if lead == "L0": day, hour = dd, 9
                    else: day, hour = dd - dt.timedelta(days=int(lead[1])), 18
                    ts = int(dt.datetime(day.year, day.month, day.day, hour).timestamp()) - tz * 3600
                    px, age = price_at(bk["token"], ts)
                    rows.append(dict(city=city, lead=lead, day=d, lo=lo, hi=hi,
                                     prob=prob, px=px, age_h=age, won=bk["won"],
                                     holdout=d in hold_days))
    save("model_rows.json", rows)
    fresh = [r for r in rows if r["px"] is not None and r["age_h"] <= MAX_PRICE_AGE_H]
    stale = len(rows) - len(fresh)
    print(f"model rows {len(rows)}; with fresh market price {len(fresh)}; stale-skipped {stale}")

    trades = {th: [] for th in THETAS}
    for r in fresh:
        if not r["holdout"]: continue
        ask = min(r["px"] + SLIPPAGE, 0.95)
        for th in THETAS:
            if r["prob"] - ask > th:
                trades[th].append(dict(**{k: r[k] for k in ("city","lead","day","prob","won")},
                                       ask=ask, pnl=(1/ask - 1) if r["won"] else -1.0))
    ho = [r for r in fresh if r["holdout"]]
    lines = ["# Q1 REPORT — W1 weather bucket backtest (holdout only)",
             f"window {WINDOW_START} → 2026-10-14 · cities {len(cities)} · "
             f"model rows {len(rows)} · priced-fresh {len(fresh)} (stale-skipped {stale})",
             f"fit/holdout split {SPLIT:.0%} of days per city·lead · slippage +{SLIPPAGE}",
             ""]
    lines.append("| θ | n buys | hit rate | EV per $1 | total PnL @$1 | mean prob | mean ask |")
    lines.append("|---|---|---|---|---|---|---|")
    verdict = "KILL"
    for th in THETAS:
        t = trades[th]
        if not t: lines.append(f"| {th} | 0 | - | - | - | - | - |"); continue
        ev = sum(x["pnl"] for x in t) / len(t)
        hr = sum(1 for x in t if x["won"]) / len(t)
        lines.append(f"| {th} | {len(t)} | {hr:.1%} | {ev:+.2f} | {sum(x['pnl'] for x in t):+.1f} | "
                     f"{st.mean(x['prob'] for x in t):.2f} | {st.mean(x['ask'] for x in t):.2f} |")
        if len(t) >= 100 and ev >= 0.20: verdict = "PASS-TO-NEXT-STAGE"
        elif len(t) >= 30 and ev > 0: verdict = verdict if verdict == "PASS-TO-NEXT-STAGE" else "PROMISING-BELOW-n"
    lines += ["", "## calibration (holdout, all priced rows, no trade filter)",
              "| prob/price bin | our n | our hit | crowd n | crowd hit |", "|---|---|---|---|---|"]
    for lo_b in range(0, 90, 10):
        a = [r for r in ho if lo_b/100 <= r["prob"] < (lo_b+10)/100]
        c = [r for r in ho if r["px"] is not None and lo_b/100 <= r["px"] < (lo_b+10)/100]
        lines.append(f"| {lo_b}-{lo_b+10}% | {len(a)} | {st.mean([r['won'] for r in a]) if a else float('nan'):.2f} | "
                     f"{len(c)} | {st.mean([r['won'] for r in c]) if c else float('nan'):.2f} |")
    brier_us = st.mean([(r["prob"] - r["won"]) ** 2 for r in ho]) if ho else float("nan")
    brier_crowd = st.mean([(r["px"] - r["won"]) ** 2 for r in ho if r["px"] is not None]) if ho else float("nan")
    lines += ["", f"Brier — our model {brier_us:.4f} vs crowd price {brier_crowd:.4f} (holdout)",
              "", f"## VERDICT vs pre-registered criteria: **{verdict}**",
              "(PASS needs n≥100 AND EV/$≥+0.20 on holdout; KILL if EV≤0)"]
    open(os.path.join(HERE, "REPORT.md"), "w").write("\n".join(lines))
    json.dump(trades, open(os.path.join(HERE, "trades_holdout.json"), "w"), default=str)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
