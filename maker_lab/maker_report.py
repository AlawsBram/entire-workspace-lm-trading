#!/usr/bin/env python3
"""
maker_report.py — gate report for the maker simulator (same discipline as S1)

Reads sim_rounds.csv + sim_fills.jsonl, prints the PASS/FAIL verdict:
  G1  >= 50 settled simulated rounds
  G2  >= 20 fills
  G3  mean realized edge per filled share > 0 (not getting picked off)
  G4  model certification >= 90% (fair at fill agreed with the round outcome)
Rebates/rewards are reported as an explicit upside estimate and are NEVER
counted toward the gate.
"""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_P = os.path.join(HERE, "sim_rounds.csv")
FILLS_P = os.path.join(HERE, "sim_fills.jsonl")
STATS_P = os.path.join(HERE, "maker_stats.json")

def load():
    rows = []
    if os.path.exists(CSV_P):
        with open(CSV_P) as f: rows = list(csv.DictReader(f))
    fills = []
    if os.path.exists(FILLS_P):
        with open(FILLS_P) as f:
            for line in f:
                try: fills.append(json.loads(line))
                except Exception: pass
    return rows, fills

def fee_taker(p): return 0.07 * p * (1 - p)

def main():
    rows, fills = load()
    n_rounds = len(rows)
    n_fills = len(fills)
    pnl = sum(float(r["pnl_usd"]) for r in rows if r["pnl_usd"] not in ("", None))
    edges = [float(r["adv_sel_edge"]) for r in rows if r["adv_sel_edge"] not in ("", None)]
    mean_edge = sum(edges) / len(edges) if edges else None
    cert_n = sum(int(r["model_cert_n"] or 0) for r in rows)
    cert_h = sum(int(r["model_cert_hit"] or 0) for r in rows)
    cert = cert_h / cert_n if cert_n else None
    n_quotes = sum(int(r["n_quotes"] or 0) for r in rows)
    # rebate upside: 20% of the taker fee paid by the aggressors on OUR fills,
    # assuming we were the only maker (upper bound; real share is pro-rata)
    rebate_up = 0.20 * sum(fee_taker(f["price"]) * f["size"] for f in fills)

    g1 = n_rounds >= 50
    g2 = n_fills >= 20
    g3 = (mean_edge is not None and mean_edge > 0)
    g4 = (cert is not None and cert >= 0.90)
    passed = g1 and g2 and g3 and g4

    L = []
    L.append("MAKER FAMILY (S3+S6+S10) — SIMULATOR GATE REPORT")
    L.append("=" * 54)
    L.append(f"settled rounds:      {n_rounds}")
    L.append(f"fills:               {n_fills}   quote-seconds: {n_quotes}")
    L.append(f"paper PnL:           {pnl:+.2f} USDC  (maker fee = 0; rebates NOT included)")
    L.append(f"mean edge per fill:  {mean_edge if mean_edge is None else format(mean_edge, '+.4f')}  (>0 = fair anchor survived adverse selection)")
    L.append(f"model certification: {cert_h}/{cert_n}" + (f" = {cert:.1%}" if cert is not None else ""))
    L.append(f"rebate upside est.:  +{rebate_up:.2f} USDC upper bound (20% of taker fees on our fills)")
    L.append("")
    L.append("GATES")
    L.append(f"  [{'PASS' if g1 else 'FAIL'}] G1 >= 50 settled rounds        (n={n_rounds})")
    L.append(f"  [{'PASS' if g2 else 'FAIL'}] G2 >= 20 fills                 (n={n_fills})")
    L.append(f"  [{'PASS' if g3 else 'FAIL'}] G3 mean realized edge > 0      ({mean_edge if mean_edge is None else format(mean_edge, '+.4f')})")
    L.append(f"  [{'PASS' if g4 else 'FAIL'}] G4 model certification >= 90%  ({cert if cert is None else format(cert, '.1%')})")
    L.append("")
    if passed:
        L.append("VERDICT: PASS — eligible to draft a live maker mode at MINIMAL size,")
        L.append("with regime-watch running and KILL switch armed. Rebates/rewards then")
        L.append("become real upside on top of the proven spread capture.")
    elif n_rounds < 50 or n_fills < 20:
        L.append("VERDICT: INSUFFICIENT EVIDENCE — keep the simulator accumulating.")
        L.append(f"  needs: {max(0, 50 - n_rounds)} more settled rounds, {max(0, 20 - n_fills)} more fills.")
    else:
        L.append("VERDICT: FAIL — do NOT take the maker family live.")
        if not g3: L.append("  adverse selection is eating the spread: widen HALF_SPREAD or tighten FAIR band.")
        if not g4: L.append("  model disagreeing with outcomes: check feed health / sigma calibration.")
    print("\n".join(L))

if __name__ == "__main__":
    main()
