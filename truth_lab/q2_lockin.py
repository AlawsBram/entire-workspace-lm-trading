#!/usr/bin/env python3
"""
q2_lockin.py — Q2: refresh the S1 lock-in edge on FRESH truth_lab days.

Pre-registered (BACKTEST-QUEUE.md Q2): replicate on new days —
  (a) lock accuracy: |gap_bps| >= 4 at late-round => our direction == chain outcome
      (original claim: 100% on the Oct corpus);
  (b) lagging-book win rate: when the lock says D but the CLOB still sells D below
      99.5c, buying D at the ask wins (original claim: 73% on the lagging subset);
  (c) post-fee edge per share: 1 - ask - 0.07*ask*(1-ask);
  (d) capacity: top-of-book size at signal (recorded from 2026-10-15 recorder v2).
PASS: (a) ~100% and (b) ~73% replicated on held-out new days at n>=100 signals.
INTERIM report while n < 100 (label says so; no verdict until then).
"""
import json, os, glob, statistics as st
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "truth_data")

def fee(p): return 0.07 * p * (1 - p)

def load_rounds():
    recs = {}
    for f in sorted(glob.glob(os.path.join(DATA, "timeline-*.jsonl"))):
        for line in open(f):
            try: r = json.loads(line)
            except Exception: continue
            if r.get("type") != "live" or r.get("label") != "5m": continue
            recs.setdefault(r["start"], []).append(r)
    chain = {}
    p = os.path.join(DATA, "divergences.csv")
    if os.path.exists(p):
        import csv
        for row in csv.DictReader(open(p)):
            if row.get("chain_outcome") in ("Up", "Down"):
                chain[int(row["start"])] = row["chain_outcome"]
    rp = os.path.join(DATA, "retro_settled.json")
    if os.path.exists(rp):
        for r in json.load(open(rp)):
            if r.get("chain") in ("Up", "Down"):
                chain[r["start"]] = r["chain"]
    return recs, chain

def main():
    recs, chain = load_rounds()
    OFFS = (60, 45, 30, 20, 10)
    acc = {o: dict(lock=0, ok=0, lag=0, lagwin=0, edges=[], sizes=[]) for o in OFFS}
    endagree = dict(n=0, ok=0)
    for start, rows in sorted(recs.items()):
        ch = chain.get(start)
        if ch not in ("Up", "Down"): continue
        rows.sort(key=lambda r: r["ts"])
        end = start + 300
        cov = (rows[-1]["ts"] - rows[0]["ts"]) / 300 if rows else 0
        last = rows[-1]
        if cov >= 0.9 and last.get("gap_bps") is not None:
            d = "Up" if last["gap_bps"] >= 0 else "Down"
            endagree["n"] += 1; endagree["ok"] += (d == ch)
        for o in OFFS:
            cand = [r for r in rows if r["ts"] <= end - o]
            if not cand: continue
            r = cand[-1]
            g = r.get("gap_bps")
            if g is None or abs(g) < 4: continue
            d = "Up" if g > 0 else "Down"
            a = acc[o]; a["lock"] += 1; a["ok"] += (d == ch)
            bb, ba, bs, asz = r.get("bb"), r.get("ba"), r.get("bs"), r.get("asz")
            ask = ba if d == "Up" else (1 - bb if bb is not None else None)
            size = asz if d == "Up" else bs
            if ask is not None and ask < 0.995:
                a["lag"] += 1; a["lagwin"] += (d == ch)
                a["edges"].append(1 - ask - fee(ask))
                if size: a["sizes"].append(size)
    n_tot = sum(acc[o]["lag"] for o in OFFS)
    interim = "INTERIM (n<100 — NO VERDICT YET)" if n_tot < 100 else "FINAL n"
    L = [f"# Q2 REPORT — lock-in refresh on fresh days ({interim})",
         f"generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
         f"settled rounds with timelines: {sum(1 for s in recs if s in chain)}",
         "", "| t-before-end | lock signals | lock accuracy | lagging-book buys | win rate | mean post-fee edge/sh | median top-of-book size |",
         "|---|---|---|---|---|---|---|"]
    for o in OFFS:
        a = acc[o]
        lp = f"{a['ok']/a['lock']:.1%}" if a["lock"] else "-"
        wr = f"{a['lagwin']/a['lag']:.1%}" if a["lag"] else "-"
        me = f"{st.mean(a['edges']):+.3f}" if a["edges"] else "-"
        ms = f"{st.median(a['sizes']):.0f}" if a["sizes"] else "-"
        L.append(f"| {o}s | {a['lock']} | {lp} | {a['lag']} | {wr} | {me} | {ms} |")
    allag = [e for o in OFFS for e in acc[o]["edges"]]
    allw = sum(acc[o]["lagwin"] for o in OFFS); alln = sum(acc[o]["lag"] for o in OFFS)
    alllock = sum(acc[o]["lock"] for o in OFFS); allokk = sum(acc[o]["ok"] for o in OFFS)
    L += ["", f"pooled: lock accuracy {allokk}/{alllock}"
          + (f" = {allokk/alllock:.1%}" if alllock else "")
          + f" · lagging-book win {allw}/{alln}" + (f" = {allw/alln:.1%}" if alln else "")
          + f" · mean post-fee edge {st.mean(allag):+.3f}/sh" if allag else "",
          f"arbiter-at-end vs chain (coverage>=0.9): {endagree['ok']}/{endagree['n']}",
          "", "Targets (pre-registered): lock accuracy ~100%, lagging win ~73%.",
          "Verdict rule: only at pooled lagging-book n>=100."]
    open(os.path.join(HERE, "Q2-REPORT.md"), "w").write("\n".join(L))
    print("\n".join(L))

if __name__ == "__main__":
    main()
