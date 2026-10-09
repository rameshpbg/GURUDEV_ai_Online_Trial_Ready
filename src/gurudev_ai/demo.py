"""Synthetic demonstration data only, not real crop results."""
from pathlib import Path
import numpy as np
import pandas as pd

def generate(directory, seed=193, samples=72, markers=32):
    dest = Path(directory)
    dest.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    x = rng.binomial(2, 0.35, (samples, markers)).astype(float)
    x[rng.random(x.shape) < .03] = np.nan
    effects = rng.normal(0, 0.4, markers)
    y = np.nan_to_num(x, nan=.7) @ effects + rng.normal(0, 1.7, samples) + 5
    ids = [f"RICE_{i:03d}" for i in range(samples)]
    g = pd.DataFrame(x, columns=[f"SNP_{i:04d}" for i in range(markers)])
    g.insert(0, "sample_id", ids)
    g.to_csv(dest / "demo_genotype.csv", index=False, na_rep="")
    p = pd.DataFrame({"sample_id": ids, "grain_yield": y, "family": [f"FAM_{i%8}" for i in range(samples)]})
    p.to_csv(dest / "demo_phenotype.csv", index=False)
    return dest / "demo_genotype.csv", dest / "demo_phenotype.csv"
