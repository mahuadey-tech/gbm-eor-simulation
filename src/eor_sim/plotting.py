"""Plotting helpers for the EOR sweep. Kept separate so the core model has no
hard dependency on matplotlib."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .model import SimParams


def plot_sweep(sweep: pd.DataFrame, params: SimParams | None = None, ax=None,
               title: str | None = None):
    """Plot estimated EOR coefficient vs eloquent fraction, with the true
    direct effect drawn as a reference line.

    Returns the matplotlib Axes.
    """
    import matplotlib.pyplot as plt

    p = params or SimParams()
    if ax is None:
        _, ax = plt.subplots(figsize=(5.2, 3.6))

    x = sweep["eloquent_fraction"].to_numpy() * 100
    y = sweep["coef_mean"].to_numpy()
    lo = sweep["ci_low"].to_numpy()
    hi = sweep["ci_high"].to_numpy()

    ax.axhline(0, color="#c2c9d4", lw=0.8, ls=":")
    ax.axhline(p.b_eor_direct, color="#1a1a2e", lw=1.1, ls="--")
    ax.text(3, p.b_eor_direct + 0.08,
            f"true direct effect ({p.b_eor_direct:.2f}), identical in every cohort",
            fontsize=8, va="bottom")
    ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt="o-", color="#1a1a2e",
                ms=5, lw=1.5, capsize=3.5, mfc="white", mew=1.4, zorder=5)
    ax.set_xlabel("Eloquent fraction of the cohort (%)")
    ax.set_ylabel("Estimated EOR coefficient (log-HR)")
    ax.set_xticks(x)
    ax.set_ylim(min(-2.0, lo.min() - 0.15), max(0.5, hi.max() + 0.15))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if title:
        ax.set_title(title, fontsize=10, fontweight="bold")
    return ax
