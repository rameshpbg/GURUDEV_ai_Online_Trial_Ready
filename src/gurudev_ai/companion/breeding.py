"""Exploratory selection index and trait complementarity: not genomic breeding values."""
from __future__ import annotations
from io import BytesIO
from itertools import combinations
import json
import numpy as np
import pandas as pd

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_LINES = 5000
MAX_PAIRS = 150000


def parse_parent_csv(content: bytes) -> tuple[pd.DataFrame, list[str]]:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The upload exceeds 5 MB; submit an appropriately sized table.")
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise ValueError(f"Cannot read CSV: {exc}") from None
    if df.empty or len(df) > MAX_LINES:
        raise ValueError("Parent table must contain 1–5000 records.")
    possible = ("sample_id", "genotype", "Genotype", "parent_id", "Parent", "ID")
    ident = next((x for x in possible if x in df.columns), None)
    if ident is None:
        raise ValueError("Parent table requires a sample_id, genotype, parent_id or ID column.")
    df = df.rename(columns={ident: "sample_id"})
    if df.sample_id.isna().any() or df.sample_id.astype(str).str.strip().eq("").any():
        raise ValueError("Parent identifiers cannot be blank.")
    df["sample_id"] = df.sample_id.astype(str).str.strip()
    if df.sample_id.duplicated().any():
        raise ValueError("Each row must represent one parent. Aggregate replicates using an appropriate statistical model first.")
    numerical = []
    for col in df.columns:
        if col == "sample_id":
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() >= max(2, int(len(df) * 0.75)) and converted.nunique() >= 2:
            df[col] = converted.astype(float)
            numerical.append(col)
    if len(numerical) == 0:
        raise ValueError("At least one informative numeric trait is required.")
    return df, numerical


def rank_parents(content: bytes, specifications: list[dict], top: int = 15) -> dict:
    df, numeric_cols = parse_parent_csv(content)
    if not isinstance(specifications, list) or not specifications or len(specifications) > 12:
        raise ValueError("Provide 1–12 trait preferences.")
    seen = set()
    accepted = []
    for spec in specifications:
        trait = str(spec.get("trait", ""))
        if trait not in numeric_cols or trait in seen:
            raise ValueError(f"Trait '{trait}' is missing, repeated or not numeric.")
        seen.add(trait)
        direction = str(spec.get("direction", "max"))
        if direction not in ("max", "min"):
            raise ValueError("Trait direction must be max or min.")
        weight = float(spec.get("weight", 1))
        if not np.isfinite(weight) or weight <= 0 or weight > 100:
            raise ValueError("Trait weights must be positive and no more than 100.")
        accepted.append({"trait": trait, "direction": direction, "weight": weight})
    weights = np.array([s["weight"] for s in accepted])
    weights = weights / weights.sum()
    complete = df.dropna(subset=[x["trait"] for x in accepted]).copy()
    excluded = int(len(df) - len(complete))
    if len(complete) < 3:
        raise ValueError("At least three parents with complete selected trait observations are required.")
    Z = []
    for spec in accepted:
        x = complete[spec["trait"]].to_numpy(dtype=float)
        sd = np.std(x, ddof=0)
        z = (x - np.mean(x)) / sd if sd > 1e-12 else np.zeros(len(x))
        if spec["direction"] == "min":
            z = -z
        Z.append(z)
    matrix = np.array(Z).T
    scores = matrix @ weights
    items = []
    for idx, r in complete.reset_index(drop=True).iterrows():
        items.append({"sample_id": str(r["sample_id"]), "score": round(float(scores[idx]), 5),
                      "traits": {s["trait"]: round(float(r[s["trait"]]), 4) for s in accepted}})
    items.sort(key=lambda x: x["score"], reverse=True)
    # For manageable computation, consider the strongest-ranked 100 parents only.
    best = items[:min(100, len(items))]
    z_lookup = {str(complete.iloc[i]["sample_id"]): matrix[i] for i in range(len(complete))}
    crosses = []
    for p, q in combinations(best, 2):
        zp, zq = z_lookup[p["sample_id"]], z_lookup[q["sample_id"]]
        pair_score = (p["score"] + q["score"]) / 2 + float(np.dot(np.abs(zp - zq), weights) * 0.10)
        crosses.append({"parent_1": p["sample_id"], "parent_2": q["sample_id"],
                        "exploratory_score": round(pair_score, 5),
                        "complementarity": round(float(np.dot(np.abs(zp - zq), weights)), 5)})
    crosses.sort(key=lambda x: x["exploratory_score"], reverse=True)
    return {"parents": items[:max(1,min(top,50))], "crosses": crosses[:10],
            "n_parents": len(complete), "excluded_for_missing_selected_traits": excluded,
            "selected_traits": accepted,
            "warning": "Exploratory phenotypic ranking only. Scores are standardized trait indices, NOT genetic merit, heterosis, predicted progeny performance, diversity, causal effects, or field recommendations. Account for G×E, heritability, relatedness, stability, maturity, and intended breeding objective before choosing crosses."}


def trial_quality(content: bytes) -> dict:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Maximum CSV size is 5 MB.")
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise ValueError(f"Cannot read CSV: {exc}") from None
    if df.empty or len(df) > 50000:
        raise ValueError("Trial CSV must contain 1–50,000 observations.")
    idcol = next((k for k in ("sample_id","Genotype","genotype","entry","Entry","ID") if k in df.columns), None)
    if idcol is None:
        raise ValueError("Add a sample_id, genotype or entry identifier column.")
    alerts = []
    if df[idcol].isna().any() or df[idcol].astype(str).str.strip().eq("").any():
        alerts.append("Missing genotype/entry identifiers detected.")
    replicate = next((k for k in ("rep", "Rep", "replicate", "Replication") if k in df.columns), None)
    if replicate is None:
        alerts.append("No replication column identified; design validation and error estimation may be limited.")
    elif df[replicate].nunique() < 2:
        alerts.append("Only one replicate label detected; do not assume replication-based ANOVA is possible.")
    env = next((k for k in ("environment", "Environment", "location", "Location", "year", "Year") if k in df.columns), None)
    plotcol = next((k for k in ("plot_id", "Plot", "plot") if k in df.columns), None)
    duplicate_plots = 0
    if plotcol:
        subset = ([env] if env else []) + [plotcol]
        duplicate_plots = int(df.duplicated(subset=subset).sum())
        if duplicate_plots:
            alerts.append(f"{duplicate_plots} repeated plot identifiers within the available environment key; inspect original field book.")
    trait_missing = {}
    for c in df.columns:
        if c not in {idcol, replicate, env, plotcol}:
            numeric = pd.to_numeric(df[c], errors="coerce")
            if numeric.notna().sum() >= 2:
                trait_missing[c] = round(float(numeric.isna().mean()), 4)
    if not trait_missing:
        alerts.append("No analyzable numeric traits detected.")
    if any(v > 0.2 for v in trait_missing.values()):
        alerts.append("Some numeric traits have more than 20% missing observations; investigate missingness mechanisms.")
    return {"n_rows":len(df), "n_columns":len(df.columns), "entries":int(df[idcol].nunique(dropna=True)),
            "replicate_column":replicate, "environment_column":env,
            "duplicate_plots":duplicate_plots, "trait_missing_fraction":trait_missing,
            "alerts":alerts, "validation_note":"Structural QC only. This is not ANOVA, BLUP, GWAS, or confirmation of design validity."}
