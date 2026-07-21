"""Sanity tests. The most important one encodes the paper's own kill-switch:
with the mechanism removed, the coefficient must stop moving."""
import numpy as np

from eor_sim import (
    SimParams, simulate_cohort, fit_total_effect,
    fit_direct_effect, sweep_eloquent_fraction,
)


def _slope(sweep):
    return float(np.polyfit(sweep.eloquent_fraction, sweep.coef_mean, 1)[0])


def test_simulate_shapes():
    df = simulate_cohort(200, 0.5, rng=1)
    assert len(df) == 200
    assert set(["eor", "eloquent", "kps_pre", "kps_post",
                "time", "event"]).issubset(df.columns)
    assert df["event"].isin([0, 1]).all()


def test_direct_effect_recovers_truth():
    # Conditioning on post-op KPS should recover the specified direct effect,
    # ON AVERAGE. A single cohort wanders with sampling noise, so average the
    # estimate across several seeds and check the mean.
    p = SimParams()
    coefs = [fit_direct_effect(simulate_cohort(4000, 0.5, p, rng=s))[0]
             for s in range(8)]
    mean = sum(coefs) / len(coefs)
    assert abs(mean - p.b_eor_direct) < 0.12, (mean, coefs)


def test_total_effect_attenuates_with_eloquence():
    # The conventional model's coefficient must move toward zero as the
    # eloquent fraction rises, even though the truth is fixed.
    sweep = sweep_eloquent_fraction(estimator="total", reps=15)
    assert sweep.coef_mean.iloc[-1] > sweep.coef_mean.iloc[0]   # less negative
    assert _slope(sweep) > 0.10


def test_mechanism_kill_switch():
    # THE falsification check: remove the interaction, the slope must vanish.
    off = sweep_eloquent_fraction(
        params=SimParams(d_eor_x_eloq=0.0), estimator="total", reps=15)
    assert abs(_slope(off)) < 0.15, _slope(off)
