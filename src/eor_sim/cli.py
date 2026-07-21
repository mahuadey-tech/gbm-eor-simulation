"""Command-line interface for eor_sim.

Examples
--------
    eor-sim sweep
    eor-sim sweep --fractions 0,25,50,75,100 --n 1500 --reps 30
    eor-sim sweep --estimator direct
    eor-sim figure --out figure.png
    eor-sim falsify          # the paper's own kill-switch check
"""
from __future__ import annotations

import argparse
import sys

from .model import SimParams, sweep_eloquent_fraction


def _parse_fractions(text: str) -> list[float]:
    vals = [float(v) for v in text.split(",") if v.strip() != ""]
    # accept either 0-1 or 0-100
    if max(vals) > 1.0:
        vals = [v / 100.0 for v in vals]
    return vals


def _print_table(sweep) -> None:
    print(f"{'eloquent %':>11}{'deficit %':>11}{'EOR log-HR':>13}{'95% CI':>22}")
    for _, row in sweep.iterrows():
        ci = f"[{row.ci_low:.2f}, {row.ci_high:.2f}]"
        print(f"{row.eloquent_fraction*100:>10.0f}%"
              f"{row.deficit_rate*100:>10.1f}%"
              f"{row.coef_mean:>13.3f}"
              f"{ci:>22}")


def cmd_sweep(args) -> int:
    params = SimParams()
    sweep = sweep_eloquent_fraction(
        fractions=_parse_fractions(args.fractions),
        n=args.n, reps=args.reps, params=params, estimator=args.estimator,
    )
    print(f"\nTrue direct effect (fixed in every cohort): {params.b_eor_direct}")
    print(f"Estimator: {args.estimator}\n")
    _print_table(sweep)
    if args.estimator == "total":
        span = sweep.coef_mean.iloc[-1] - sweep.coef_mean.iloc[0]
        print(f"\nCoefficient moved by {span:+.3f} across the eloquent range "
              f"while the true effect never changed.")
    return 0


def cmd_figure(args) -> int:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is required for `figure`. "
              "Install with: pip install 'eor-sim[plot]'", file=sys.stderr)
        return 1
    from .plotting import plot_sweep

    params = SimParams()
    sweep = sweep_eloquent_fraction(
        fractions=_parse_fractions(args.fractions),
        n=args.n, reps=args.reps, params=params, estimator="total",
    )
    ax = plot_sweep(sweep, params,
                    title="Same biology, opposite conclusions across cohorts")
    ax.figure.savefig(args.out, dpi=args.dpi, bbox_inches="tight",
                      facecolor="white")
    print(f"Wrote {args.out}")
    return 0


def cmd_falsify(args) -> int:
    """Remove the mechanism (d_eor_x_eloq = 0) and confirm the slope vanishes.

    If the slope does NOT vanish here, the estimator is detecting something that
    was never put in, and nothing downstream can be trusted. This is the check
    the paper insists a user run before touching real data.
    """
    import numpy as np

    on = sweep_eloquent_fraction(estimator="total")
    off = sweep_eloquent_fraction(
        params=SimParams(d_eor_x_eloq=0.0), estimator="total")

    def slope(s):
        return float(np.polyfit(s.eloquent_fraction, s.coef_mean, 1)[0])

    s_on, s_off = slope(on), slope(off)
    print(f"slope WITH mechanism (d_eor_x_eloq=3.0): {s_on:+.3f}")
    print(f"slope WITHOUT mechanism (d_eor_x_eloq=0): {s_off:+.3f}")
    ok = abs(s_off) < 0.15
    print("\nPASS: removing the mechanism flattens the slope."
          if ok else
          "\nFAIL: slope persists without the mechanism -- do not trust results.")
    return 0 if ok else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eor-sim",
        description="Teaching simulation of the extent-of-resection "
                    "double-duty problem in glioblastoma.")
    sub = p.add_subparsers(dest="command", required=True)

    common = dict()
    s = sub.add_parser("sweep", help="print the coefficient across eloquent fractions")
    s.add_argument("--fractions", default="0,25,50,75,100")
    s.add_argument("--n", type=int, default=1500)
    s.add_argument("--reps", type=int, default=30)
    s.add_argument("--estimator", choices=["total", "direct"], default="total")
    s.set_defaults(func=cmd_sweep)

    f = sub.add_parser("figure", help="render the sweep figure to a file")
    f.add_argument("--fractions", default="0,25,50,75,100")
    f.add_argument("--n", type=int, default=1500)
    f.add_argument("--reps", type=int, default=30)
    f.add_argument("--out", default="eor_sweep.png")
    f.add_argument("--dpi", type=int, default=300)
    f.set_defaults(func=cmd_figure)

    k = sub.add_parser("falsify", help="run the mechanism kill-switch check")
    k.set_defaults(func=cmd_falsify)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
