"""eor_sim -- a teaching simulation of the extent-of-resection "double-duty" problem.

This package accompanies a manuscript on model structure in glioblastoma
prediction. It is an illustration of a statistical mechanism, not a validated
clinical model. See README.md.
"""
from .model import (
    SimParams,
    simulate_cohort,
    fit_total_effect,
    fit_direct_effect,
    sweep_eloquent_fraction,
)

__version__ = "1.0.0"

__all__ = [
    "SimParams",
    "simulate_cohort",
    "fit_total_effect",
    "fit_direct_effect",
    "sweep_eloquent_fraction",
    "__version__",
]
