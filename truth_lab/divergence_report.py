#!/usr/bin/env python3
"""
divergence_report.py — analyze truth_data/divergences.csv

Answers, with counts:
  1. How often is the house DISPLAY (past-results `outcome`) wrong vs chain,
     by |gap_bps| bucket?  (the 27.5-35% sub-2bp finding, measured prospectively)
  2. How long after round end does each source become final?
     (gamma display lag, chain ground-truth lag)
  3. How often did OUR arbiter agree with chain — and when it did, how many
     seconds of head start did we have over the house display?
  4. House lifecycle flags (disputed / extended review / missing).

Usage:  python3 divergence_report.py [--csv truth_data/divergences.csv]
"""
import argparse, csv, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def bucket(gap_bps):
    g = abs(gap_bps)
    if g < 1: return "<1bp"
    if g < 2: return "1-2bp"
    if g < 4: return "2-4bp"
    return ">4bp"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(HERE, "truth_data", "divergences.csv"))
    a = ap.parse_args()
    if not os.path.exists(a.csv):
        print(f"no data yet at {a.csv} — run truth_recorder.py first"); return
    rows = [r for r in csv.DictReader(open(a.csv)) if r.get("chain_outcome") in ("Up", "Down")]
    total = len(rows)
    if not total:
        print("no chain-verified verdict rows yet"); return

    print(f"== TRUTH-FEED DIVERGENCE REPORT == ({total} chain-verified rounds)\n")

    # 1. past-results correctness by gap bucket — TWO axes:
    #    pr_gap_bps = house's own (close-open)/open  <- the axis that flips its sign() display
    #    gap_bps    = our window-TWAP vs open         <- the axis that decides settlement
    #    Live finding 2026-10-14 round 2: pr wrong at TWAP gap -9.58bp because the
    #    HOUSE axis was razor (+0.85bp tail rebound). Bucket by the house axis first.
    print("1) House display (past-results `outcome`) vs chain:")
    for axis, key in (("house |close-open| (pr_gap_bps)", "pr_gap_bps"),
                      ("our |TWAP-open|  (gap_bps)", "gap_bps")):
        print(f"   by {axis}:")
        print(f"   {'bucket':<7} {'n':>4} {'pr_wrong':>9} {'pr_wrong%':>9} {'pr_missing':>10}")
        buckets = {}
        for r in rows:
            g = f(r.get(key))
            if g is None: continue
            b = bucket(g)
            d = buckets.setdefault(b, dict(n=0, wrong=0, missing=0))
            d["n"] += 1
            prm = r.get("pr_match")
            if prm == "": d["missing"] += 1
            elif prm.lower() in ("false", "0"): d["wrong"] += 1
        for b in ("<1bp", "1-2bp", "2-4bp", ">4bp"):
            d = buckets.get(b)
            if not d or not d["n"]: continue
            scored = d["n"] - d["missing"]
            pct = (d["wrong"] / scored * 100) if scored else float("nan")
            print(f"   {b:<7} {d['n']:>4} {d['wrong']:>9} {pct:>8.1f}% {d['missing']:>10}")
        print()

    # 2. finality lags
    gl = [f(r.get("gamma_lag_s")) for r in rows]; gl = [x for x in gl if x is not None]
    cl = [f(r.get("chain_lag_s")) for r in rows]; cl = [x for x in cl if x is not None]
    print("\n2) Seconds after round end until source is final:")
    for name, xs in (("gamma display", gl), ("chain truth", cl)):
        if xs:
            print(f"   {name:<14} n={len(xs):>4} median={st.median(xs):>7.1f}s "
                  f"p90={sorted(xs)[int(len(xs)*0.9)-1]:>7.1f}s max={max(xs):>7.1f}s")
        else:
            print(f"   {name:<14} no data")

    # 3. arbiter agreement + head start
    cov_ok = [r for r in rows if (f(r.get("coverage")) or 0) >= 0.95]
    am = [r for r in cov_ok if r.get("arbiter_match") in ("True", "False")]
    agree = sum(1 for r in am if r["arbiter_match"] == "True")
    print(f"\n3) Our arbiter vs chain (coverage>=0.95): {agree}/{len(am)} agree"
          + (f" ({agree/len(am)*100:.1f}%)" if am else ""))
    es = [f(r.get("arbiter_early_s")) for r in am if r["arbiter_match"] == "True"]
    es = [x for x in es if x is not None]
    if es:
        print(f"   when arbiter agreed with chain, head start over gamma display: "
              f"median={st.median(es):.1f}s p90={sorted(es)[max(0,int(len(es)*0.9)-1)]:.1f}s max={max(es):.1f}s (n={len(es)})")

    # 4. house lifecycle
    hv = {}
    for r in rows: hv[r.get("house_verdict") or "?"] = hv.get(r.get("house_verdict") or "?", 0) + 1
    print(f"\n4) House lifecycle (Data API v2): {hv}")

    # extra: gamma display vs chain disagreements (display wrong even at finality)
    gw = sum(1 for r in rows if r.get("gamma_outcome") and r.get("gamma_outcome") != r.get("chain_outcome"))
    print(f"\n   gamma FINAL display disagreed with chain: {gw}/{total}")

    # extra: our open ref vs the house's recorded openPrice (both claim "the open print")
    diffs = []
    for r in rows:
        o, po = f(r.get("o_ref")), f(r.get("pr_open"))
        if o and po: diffs.append((po - o) / o * 1e4)
    if diffs:
        ad = [abs(x) for x in diffs]
        print(f"   open-ref disagreement (house pr_open vs our o_ref), bps: "
              f"median|d|={st.median(ad):.2f} max|d|={max(ad):.2f} (n={len(diffs)})")

if __name__ == "__main__":
    main()
