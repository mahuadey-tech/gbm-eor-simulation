#!/usr/bin/env python
"""Write a small synthetic cohort CSV so examples/run_on_your_data.py works
out of the box. This is fake data for a smoke-test only."""
from eor_sim import simulate_cohort

if __name__ == "__main__":
    df = simulate_cohort(400, p_eloquent=0.4, rng=0)
    df = df[["eor", "eloquent", "kps_pre", "kps_post", "time", "event"]]
    df.to_csv("examples/sample_cohort.csv", index=False)
    print("Wrote examples/sample_cohort.csv (synthetic, for testing only)")
