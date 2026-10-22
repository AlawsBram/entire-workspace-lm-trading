# Can You Beat Polymarket? — The Reproducible Study (Code + Methodology)

Source (linked from every page of the series):
https://shop.marvoproduction-apps.de/l/hrlfls (Gumroad, $19, 28.5 KB)
Captured 2026-10-07, verbatim.

⚠️ CODE & METHODOLOGY, NOT A DATASET. No Polymarket data included; a
one-command script rebuilds datasets fresh from Polymarket's FREE public
APIs (Python 3.11+, internet, no keys/account). Deliberate: reproduce from
source instead of trusting someone's CSV.

The bundle reproduces the ten-strategy efficiency study (AI swarm, classic
betting edges, calendar arb, negRisk Dutch book, smart-money copytrading).

**What you get**
- Analysis library — bootstrap CIs, favorite-longshot, calibration, momentum,
  base rates
- `collect_data.py` — rebuild datasets from public APIs in one command
- `reproduce.py` — market-structure analysis
- `negrisk_depth.py` — negRisk Dutch-book order-book-depth test
- `smartmoney.py` — on-chain smart-money walk-forward persistence test
- `GUIDE.md` + `METHODOLOGY.md` — every experiment, sample size, CI

**3 commands:** `pip install -r requirements.txt` →
`python code/scripts/collect_data.py` → `python reproduce.py`

**Result in one line:** ten approaches, one conclusion — efficiently priced;
no effect survived bootstrap 95% CI above zero AND the ~2% round-trip cost.

NOTE (our annotation): we do NOT need to buy this — our own stack already
rebuilds equivalent data from the same public APIs (maker_lab history
backfill + chain relabel + recorder) and adds on-chain ground truth the
bundle doesn't have. Saved here for completeness / cross-method comparison;
his bootstrap/Bonferroni discipline mirrors our own gate philosophy.
