"""
Core generative model and estimators for the extent-of-resection (EOR)
"double-duty" demonstration.

The point of this module is deliberately narrow. It builds synthetic patient
cohorts in which the TRUE causal structure is known because we specify it, then
fits the kind of survival model that is almost always fit in the published
literature, and shows that the estimated EOR coefficient changes with cohort
case-mix even though no biological parameter has changed.

It is a teaching / illustration tool. It is NOT a validated prognostic model,
and nothing in it should be used to make a decision about a real patient. See
README.md, section "What this is and is not."

Reference: [author/manuscript citation — see CITATION.cff]
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from lifelines import CoxPHFitter
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "lifelines is required. Install with:  pip install lifelines"
    ) from exc


# ---------------------------------------------------------------------------
# Parameters of the generative model.
#
# Every value here is an ASSUMPTION we impose on the synthetic world, not an
# estimate from data. They are fixed across every simulated cohort; the ONLY
# thing we vary between cohorts is the eloquent fraction. That is the whole
# design: if the estimated EOR effect moves anyway, it moved because of
# case-mix, not biology.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SimParams:
    b_eor_direct: float = -1.30     # true direct effect of EOR on log-hazard (protective)
    b_kps: float = -0.030           # log-hazard per KPS point (higher KPS -> lower hazard)
    deficit_kps_drop: float = 25.0  # KPS points lost to a new permanent deficit

    # extent-of-resection -> deficit, on the logit scale
    d_intercept: float = -3.2
    d_eor: float = 1.4              # resecting more raises deficit risk ...
    d_eloq: float = 0.9            # ... eloquent tumors start higher ...
    d_eor_x_eloq: float = 3.0      # ... and the penalty is far steeper there  <-- the mechanism

    baseline_hazard: float = 0.055  # per month
    eor_mean: float = 0.85          # mean fraction resected in a non-eloquent tumor
    eor_eloq_shift: float = -0.12   # surgeons resect less in eloquent tumors (this CONFOUNDS)
    eor_sd: float = 0.10
    kps_pre_mean: float = 80.0
    kps_pre_sd: float = 10.0
    censor_low: float = 6.0         # administrative censoring window (months)
    censor_high: float = 60.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Simulate one cohort
# ---------------------------------------------------------------------------
def simulate_cohort(
    n: int,
    p_eloquent: float,
    params: SimParams | None = None,
    rng: np.random.Generator | int | None = None,
) -> pd.DataFrame:
    """Generate a synthetic cohort of ``n`` patients.

    Parameters
    ----------
    n : int
        Number of patients.
    p_eloquent : float
        Fraction of tumors in an eloquent location (0-1).
    params : SimParams, optional
        Generative parameters. Defaults to the values used in the paper.
    rng : Generator | int | None
        A numpy Generator, an int seed, or None.

    Returns
    -------
    pandas.DataFrame with columns:
        eloquent, eor, deficit, kps_pre, kps_post, time, event
    """
    p = params or SimParams()
    if not isinstance(rng, np.random.Generator):
        rng = np.random.default_rng(rng)

    eloquent = rng.binomial(1, p_eloquent, n)

    # Surgeons resect less aggressively in eloquent tumors. This makes eloquence
    # a confounder of the EOR->survival relationship, exactly as in reality.
    eor = np.clip(
        rng.normal(p.eor_mean + p.eor_eloq_shift * eloquent, p.eor_sd),
        0.30, 1.0,
    )

    kps_pre = np.clip(rng.normal(p.kps_pre_mean, p.kps_pre_sd, n), 40, 100)

    logit_d = (
        p.d_intercept
        + p.d_eor * eor
        + p.d_eloq * eloquent
        + p.d_eor_x_eloq * eor * eloquent
    )
    p_def = 1.0 / (1.0 + np.exp(-logit_d))
    deficit = rng.binomial(1, p_def)

    kps_post = np.clip(kps_pre - p.deficit_kps_drop * deficit, 10, 100)

    log_h = p.b_eor_direct * eor + p.b_kps * (kps_post - 80)
    months = rng.exponential(1.0 / (p.baseline_hazard * np.exp(log_h)))

    censor = rng.uniform(p.censor_low, p.censor_high, n)
    time = np.minimum(months, censor)
    event = (months <= censor).astype(int)

    return pd.DataFrame(
        dict(
            eloquent=eloquent, eor=eor, deficit=deficit,
            kps_pre=kps_pre, kps_post=kps_post, time=time, event=event,
        )
    )


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------
def _cox_eor(df: pd.DataFrame, covariates: list[str]) -> tuple[float, float, float]:
    """Fit Cox on the given covariates, return (coef, lower95, upper95) for eor."""
    model = CoxPHFitter()
    model.fit(df[covariates + ["time", "event"]], "time", "event")
    coef = float(model.params_["eor"])
    ci = model.confidence_intervals_.loc["eor"].values
    return coef, float(ci[0]), float(ci[1])


def fit_total_effect(df: pd.DataFrame) -> tuple[float, float, float]:
    """Estimate the TOTAL effect of EOR (the quantity a surgeon needs).

    Adjusts for PRE-operative KPS and eloquence. Does NOT condition on the
    mediator (post-operative KPS), so the deficit path is left intact.
    """
    covs = ["eor", "kps_pre"]
    if df["eloquent"].nunique() > 1:
        covs.append("eloquent")
    return _cox_eor(df, covs)


def fit_direct_effect(df: pd.DataFrame) -> tuple[float, float, float]:
    """Estimate the DIRECT effect of EOR by conditioning on POST-operative KPS.

    This recovers the true direct effect and is stable across cohorts -- and it
    is the WRONG model for a surgical decision, because it holds constant a
    variable (post-op function) that is itself a consequence of the resection.
    Provided so users can see the difference, not because it should be used.
    """
    covs = ["eor", "kps_post"]
    if df["eloquent"].nunique() > 1:
        covs.append("eloquent")
    return _cox_eor(df, covs)


# ---------------------------------------------------------------------------
# Sweep across eloquent fraction
# ---------------------------------------------------------------------------
def sweep_eloquent_fraction(
    fractions: Iterable[float] = (0.0, 0.25, 0.50, 0.75, 1.0),
    n: int = 1500,
    reps: int = 30,
    params: SimParams | None = None,
    estimator: str = "total",
    base_seed: int = 1000,
) -> pd.DataFrame:
    """Repeat the simulation across a grid of eloquent fractions.

    Parameters
    ----------
    estimator : {"total", "direct"}
        Which specification to fit. "total" is the conventional published model.

    Returns
    -------
    DataFrame with columns: eloquent_fraction, coef_mean, ci_low, ci_high,
    deficit_rate  (percentiles are across ``reps`` replicates).
    """
    fit = fit_total_effect if estimator == "total" else fit_direct_effect
    rows = []
    for pf in fractions:
        coefs = []
        for r in range(reps):
            df = simulate_cohort(n, pf, params, rng=base_seed + r)
            coefs.append(fit(df)[0])
        coefs = np.asarray(coefs)
        # a larger cohort just for a stable deficit-rate readout
        big = simulate_cohort(max(n * 4, 4000), pf, params, rng=77)
        rows.append(
            dict(
                eloquent_fraction=pf,
                coef_mean=float(np.mean(coefs)),
                ci_low=float(np.percentile(coefs, 2.5)),
                ci_high=float(np.percentile(coefs, 97.5)),
                deficit_rate=float(big["deficit"].mean()),
            )
        )
    return pd.DataFrame(rows)


__all__ = [
    "SimParams",
    "simulate_cohort",
    "fit_total_effect",
    "fit_direct_effect",
    "sweep_eloquent_fraction",
]
