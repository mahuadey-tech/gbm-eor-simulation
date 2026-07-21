#!/usr/bin/env python
"""Reproduce the simulation panel from the manuscript (Fig. 1b).

Run:
    python scripts/reproduce_figure.py

This regenerates the sweep table and the figure from a fixed seed, so the
numbers should match the manuscript exactly.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eor_sim import SimParams, sweep_eloquent_fraction
from eor_sim.plotting import plot_sweep

if __name__ == "__main__":
    params = SimParams()

    total = sweep_eloquent_fraction(estimator="total", params=params)
    direct = sweep_eloquent_fraction(estimator="direct", params=params)

    print("TOTAL effect (the conventional published model):")
    print(total.to_string(index=False))
    print("\nDIRECT effect (mediator-adjusted; recovers truth, wrong for a surgeon):")
    print(direct.to_string(index=False))

    ax = plot_sweep(total, params,
                    title="Same biology, opposite conclusions across cohorts")
    ax.figure.savefig("eor_reproduced.png", dpi=300, bbox_inches="tight",
                      facecolor="white")
    print("\nWrote eor_reproduced.png")
