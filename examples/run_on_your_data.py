#!/usr/bin/env python
"""
Template: apply the SAME estimators to YOUR OWN cohort.

────────────────────────────────────────────────────────────────────────────
READ THIS FIRST.

This script does NOT simulate. It fits the two survival specifications from the
paper to a real dataset you supply, so you can see, in your own data, how much
the EOR coefficient moves between the "total effect" model (the one a surgical
decision needs) and the "direct effect" model (the mediator-adjusted one that
looks cleaner and is wrong for that decision).

This is an ILLUSTRATION, not a validated analysis. Before you read anything into
the numbers, note the limitations the paper raises:

  • "Eloquent" is not standardized. However you code it, be explicit.
  • Post-operative KPS is a CONVERGENCE POINT (baseline KPS, age, and the new
    deficit all feed it). Conditioning on it can introduce collider bias. The
    two-model contrast below is a teaching contrast, NOT a substitute for a
    proper causal-mediation analysis (use g-methods for that).
  • A single institution's data cannot, on its own, establish any of this.

If you want the total effect of resection, use `fit_total_effect`
(adjusts for PRE-operative KPS). Do not report the direct-effect number as the
answer to "does resecting more help my patients."
────────────────────────────────────────────────────────────────────────────

Your data need these columns (one row per patient):

    eor        float   extent of resection (any monotonic scale; e.g. fraction 0-1)
    eloquent   0/1     tumor in an eloquent location
    kps_pre    float   pre-operative KPS
    kps_post   float   post-operative KPS (e.g. at discharge or 30 days)
    time       float   follow-up time (months)
    event      0/1     1 = death, 0 = censored

Usage:
    python examples/run_on_your_data.py path/to/your_cohort.csv
"""
import sys

import pandas as pd

from eor_sim import fit_total_effect, fit_direct_effect

REQUIRED = ["eor", "eloquent", "kps_pre", "kps_post", "time", "event"]


def main(path: str) -> int:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        print(f"ERROR: your file is missing required columns: {missing}")
        print(f"Required: {REQUIRED}")
        return 1

    n = len(df)
    events = int(df["event"].sum())
    print(f"Loaded {n} patients, {events} events "
          f"({events / n:.0%}), eloquent = {df['eloquent'].mean():.0%}\n")

    if events < 30:
        print("WARNING: fewer than ~30 events. Cox estimates will be unstable; "
              "treat everything below as illustrative only.\n")

    tc, tlo, thi = fit_total_effect(df)
    dc, dlo, dhi = fit_direct_effect(df)

    print("TOTAL effect of EOR   (adjusts for PRE-op KPS)   "
          "<- the quantity a surgical decision needs")
    print(f"    log-HR {tc:+.3f}   95% CI [{tlo:+.3f}, {thi:+.3f}]\n")
    print("DIRECT effect of EOR  (conditions on POST-op KPS) "
          "<- cleaner-looking, WRONG for the decision")
    print(f"    log-HR {dc:+.3f}   95% CI [{dlo:+.3f}, {dhi:+.3f}]\n")

    gap = tc - dc
    print(f"The two specifications differ by {gap:+.3f} in log-HR.")
    print("If they differ substantially, the difference is the mediated "
          "(deficit -> KPS) portion of the surgical effect being adjusted "
          "away. That portion is a real cost of surgery, not a nuisance.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))
