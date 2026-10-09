"""Research-grade first-pass GBLUP with auditable, leakage-aware evaluation.

Scope: diploid biallelic genotype dosages (0/1/2), one adjusted trait value
per line, in-population genomic prediction; NOT automatic cultivar release.
"""
from __future__ import annotations
from dataclasses import dataclass
import csv
from io import BytesIO
from hashlib import sha256
from itertools import combinations
import math
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, GroupKFold

ID_COLUMNS = ("sample_id", "Sample_ID", "taxa", "Taxa", "genotype", "Genotype", "ID", "id")
NULLS = {"", "NA", "NAN", "N/A", "NONE", "NULL", "--", ".", "-"}
CALLS = {"AA": 0., "AB": 1., "BA": 1., "BB": 2.}
MAX_CSV_BYTES = 15_000_000
MAX_LINES = 5000
MAX_MARKERS = 100_000

@dataclass
class BreedingData:
    ids: list[str]
    markers: list[str]
    genotype: np.ndarray
    phenotypes: np.ndarray
    groups: np.ndarray | None
    trait: str
    qc: dict


def _frame(raw: bytes, label: str) -> pd.DataFrame:
    if not raw or len(raw) > MAX_CSV_BYTES:
        raise ValueError(f"{label}: CSV must be nonempty and <= {MAX_CSV_BYTES} bytes")
    try:
        header = next(csv.reader(raw[:250_000].decode('utf-8-sig').splitlines()))
        if len(header) != len(set(header)) or any(not c.strip() for c in header):
            raise ValueError('Duplicate or blank CSV column identifiers')
        df = pd.read_csv(BytesIO(raw), dtype=str)
    except Exception as e:
        raise ValueError(f"{label}: unable to parse CSV: {e}") from None
    if df.empty or len(df) > MAX_LINES or not df.columns.is_unique:
        raise ValueError(f"{label}: empty, too many rows, or duplicate column names")
    col = next((c for c in ID_COLUMNS if c in df.columns), None)
    if col is None:
        raise ValueError(f"{label}: sample_id identifier column is required")
    if df[col].isna().any():
        raise ValueError(f"{label}: missing sample identifiers")
    names = df[col].astype(str).str.strip()
    if names.eq('').any() or names.duplicated().any():
        raise ValueError(f"{label}: blank or duplicated sample identifiers")
    return df.drop(columns=[col]).set_axis(pd.Index(names, name="sample_id"))


def _dosage(v: object) -> float:
    if pd.isna(v):
        return math.nan
    s = str(v).strip().upper()
    if s in NULLS:
        return math.nan
    if s in CALLS:
        return CALLS[s]
    if s in ("0", "1", "2", "0.0", "1.0", "2.0"):
        return float(s)
    raise ValueError(f"Invalid SNP dosage {str(v)[:24]!r}; expected diploid 0,1,2 or AA,AB,BB")


def prepare_data(geno_csv: bytes, pheno_csv: bytes, trait: str, group: str | None = None) -> BreedingData:
    g, p = _frame(geno_csv, "Genotypes"), _frame(pheno_csv, "Phenotypes")
    if trait not in p.columns or trait == group:
        raise ValueError(f"Trait {trait!r} is missing or conflicts with the validation group")
    if group and group not in p.columns:
        raise ValueError(f"Group column {group!r} is absent")
    if len(g.columns) > MAX_MARKERS or len(g.columns) < 2 or len(g) * len(g.columns) > 5_000_000:
        raise ValueError("This execution profile requires 2–100000 markers and at most 5 million genotype cells")
    markers = list(g.columns)
    if any(not str(x).strip() for x in markers):
        raise ValueError("Blank marker identifiers are not accepted")
    # Genotype input may contain unphenotyped breeding candidates.
    X = g.apply(lambda column: column.map(_dosage)).to_numpy(dtype=float)
    if np.isinf(X).any():
        raise ValueError("Inf genotype dosage is not supported")
    trait_values = p[trait].astype('string').str.strip()
    explicit_missing = trait_values.isna() | trait_values.str.upper().isin(NULLS)
    y_raw = pd.to_numeric(p[trait], errors="coerce")
    unexpected = (~explicit_missing.fillna(True)) & y_raw.isna()
    if unexpected.any():
        raise ValueError(f"Trait {trait!r} contains {int(unexpected.sum())} nonnumeric values; repair them explicitly")
    if np.isinf(y_raw.to_numpy(dtype=float)).any():
        raise ValueError("Infinite phenotypes are not supported")
    y = np.array([float(y_raw.at[s]) if s in p.index else np.nan for s in g.index])
    measured = np.isfinite(y)
    if measured.sum() < 24:
        raise ValueError("Need at least 24 phenotyped genotyped entries for initial nested validation")
    if np.std(y[measured]) <= 1e-12:
        raise ValueError("Phenotype trait has no measurable variation")
    groups = None
    if group:
        # Every phenotyped training entry needs a nonmissing group label.
        gs = [p.at[s, group] if s in p.index else None for s in g.index]
        groups = np.array([str(a).strip() if a is not None and not pd.isna(a) else '' for a in gs])
        if (groups[measured] == '').any() or len(set(groups[measured])) < 4:
            raise ValueError("Grouped validation requires >=4 populated independent groups")
    if not np.isfinite(np.nanmean(X, axis=0)).any():
        raise ValueError("No usable SNPs")
    missing_fraction = np.isnan(X).mean(axis=1)
    high_missing = [str(g.index[i]) for i in np.where(missing_fraction > 0.20)[0]]
    return BreedingData(
        ids=list(g.index), markers=markers, genotype=X, phenotypes=y, groups=groups,
        trait=trait, qc={
            "n_genotyped": int(len(g)), "n_phenotyped": int(measured.sum()),
            "n_unphenotyped_candidates": int((~measured).sum()), "n_markers_raw": int(X.shape[1]),
            "overall_missing_genotype_fraction": float(np.isnan(X).mean()),
            "high_missing_entries_above_20pct": high_missing,
            "unmatched_phenotype_ids": sorted(set(p.index) - set(g.index))[:30],
            "phenotype_type": "per-genotype single value; supply adjusted means or BLUEs when trials are replicated",
            "validation_design": "grouped" if group else "random; relatedness between folds may inflate accuracy",
            "ploidy": "diploid_biallelic_only",
            "group_column": group,
        },
    )


class GenomicKernel:
    """Training-only SNP QC, imputation, VanRaden-style genomic relationship."""
    def __init__(self, max_missing: float = 0.2, min_maf: float = 0.01):
        self.max_missing, self.min_maf = max_missing, min_maf

    def fit(self, train: np.ndarray) -> 'GenomicKernel':
        self.missing = np.isnan(train).mean(axis=0)
        with np.errstate(invalid="ignore"):
            self.freq = np.nanmean(train, axis=0) / 2
        self.keep = ((self.missing <= self.max_missing) &
                     (np.minimum(self.freq, 1-self.freq) >= self.min_maf) &
                     np.isfinite(self.freq))
        if self.keep.sum() < 2:
            raise ValueError("Under training-only QC, fewer than two informative SNPs remain")
        self.p = self.freq[self.keep]
        self.denominator = 2 * float(np.sum(self.p * (1 - self.p)))
        if self.denominator <= 0:
            raise ValueError("Genomic relationship denominator is zero")
        self.ztrain = self.transform(train)
        return self

    def transform(self, matrix: np.ndarray) -> np.ndarray:
        vals = matrix[:, self.keep].astype(float, copy=True)
        fill = 2 * self.p
        i, j = np.where(np.isnan(vals))
        vals[i, j] = fill[j]
        return vals - fill

    def kernel(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return (self.transform(a) @ self.transform(b).T) / self.denominator


class GBLUP:
    def __init__(self, penalty: float = 1.):
        if penalty <= 0:
            raise ValueError("Regularization must be positive")
        self.penalty = float(penalty)

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'GBLUP':
        self.kernel_ = GenomicKernel().fit(X)
        K = self.kernel_.kernel(X, X)
        self.mean_ = float(y.mean())
        # Cholesky is stable for positive semidefinite K + lambda I.
        self.alpha_ = np.linalg.solve(K + self.penalty*np.eye(len(y)), y-self.mean_)
        self.X_train_ = X.copy()
        self.n_markers_ = int(self.kernel_.keep.sum())
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.mean_ + self.kernel_.kernel(X, self.X_train_) @ self.alpha_


def _folds(n: int, groups: np.ndarray | None, seed: int, limit: int):
    if groups is None:
        count = min(limit, n)
        return list(KFold(count, shuffle=True, random_state=seed).split(np.arange(n)))
    n_groups = len(np.unique(groups))
    return list(GroupKFold(min(limit, n_groups)).split(np.arange(n), groups=groups))


def _scores(actual: np.ndarray, pred: np.ndarray) -> dict:
    err = actual - pred
    r = float(np.corrcoef(actual, pred)[0, 1]) if np.std(pred) > 1e-12 else None
    return {"rmse": float(np.sqrt(np.mean(err**2))), "mae": float(np.mean(abs(err))),
            "r2": float(1-np.sum(err**2)/np.sum((actual-actual.mean())**2)),
            "pearson_r": r if r is None or np.isfinite(r) else None}


def fit_and_evaluate(data: BreedingData, seed: int = 42) -> dict:
    measured = np.flatnonzero(np.isfinite(data.phenotypes))
    X, y = data.genotype[measured], data.phenotypes[measured]
    groups = data.groups[measured] if data.groups is not None else None
    folds = _folds(len(y), groups, seed, 5)
    oof, base, assigned = np.full(len(y), np.nan), np.full(len(y), np.nan), np.zeros(len(y), int)
    fold_log = []
    penalties = (0.1, 1., 10., 100.)
    for index, (tr, te) in enumerate(folds, 1):
        inner = _folds(len(tr), groups[tr] if groups is not None else None, seed+index, 3)
        candidate_rmse = []
        for penalty in penalties:
            errors = []
            for itr, ite in inner:
                m = GBLUP(penalty).fit(X[tr[itr]], y[tr[itr]])
                errors.extend((y[tr[ite]]-m.predict(X[tr[ite]]))**2)
            candidate_rmse.append(math.sqrt(float(np.mean(errors))))
        alpha = penalties[int(np.argmin(candidate_rmse))]
        mdl = GBLUP(alpha).fit(X[tr], y[tr])
        oof[te] = mdl.predict(X[te])
        base[te] = y[tr].mean()
        assigned[te] += 1
        fold_log.append({"fold": index, "train_n": int(len(tr)), "test_n": int(len(te)),
                         "penalty": alpha, "inner_cv_rmse": float(min(candidate_rmse)),
                         "test_rmse": float(np.sqrt(np.mean((oof[te]-y[te])**2))),
                         "markers_retained_training_only": mdl.n_markers_,
                         "train_groups": list(map(str, np.unique(groups[tr]))) if groups is not None else None,
                         "test_groups": list(map(str, np.unique(groups[te]))) if groups is not None else None})
    if np.any(assigned != 1) or not np.isfinite(oof).all():
        raise RuntimeError("Out-of-fold coverage invariant violated")
    mscore, bscore = _scores(y, oof), _scores(y, base)
    # For model deployment, tune inside FULL training data with a separate inner CV.
    splits = _folds(len(y), groups, seed+777, 3)
    full_errors = []
    for penalty in penalties:
        err = []
        for tr, te in splits:
            model = GBLUP(penalty).fit(X[tr], y[tr])
            err.extend((y[te]-model.predict(X[te]))**2)
        full_errors.append(math.sqrt(float(np.mean(err))))
    selected_penalty = penalties[int(np.argmin(full_errors))]
    final = GBLUP(selected_penalty).fit(X, y)
    estimated = final.predict(data.genotype)
    # Stop promotion if not outperforming fold-specific train-mean baseline.
    positive_skill = bool(mscore['rmse'] < bscore['rmse'] and
                          mscore['pearson_r'] is not None and mscore['pearson_r'] > 0)
    held = {data.ids[pos]: float(oof[i]) for i, pos in enumerate(measured)}
    rows = []
    excluded = set(data.qc['high_missing_entries_above_20pct'])
    for i, name in enumerate(data.ids):
        rows.append({"sample_id": name, "observed": None if not np.isfinite(data.phenotypes[i]) else float(data.phenotypes[i]),
                     "prediction": float(estimated[i]),
                     "oof_prediction": held.get(name),
                     "prediction_type": "fitted_training_sample" if name in held else "unphenotyped_candidate",
                     "genotype_qc_pass": name not in excluded})
    return {"model": final, "out_of_fold": pd.DataFrame({"sample_id": [data.ids[i] for i in measured],
                   "observed": y, "predicted": oof, "fold_mean_baseline": base}),
            "candidate_table": pd.DataFrame(rows), "model_metrics": mscore,
            "baseline_metrics": bscore, "positive_skill_gate": positive_skill,
            "folds": fold_log, "selected_penalty": selected_penalty,
            "markers_used_final": final.n_markers_, "validation_type": "group_CV" if groups is not None else "random_individual_CV",
            "warning": "Cross-validation is internal, not prospective trial validation; predictions of training entries are fitted values and not independent EBVs. No causal interpretation."}


def cross_shortlist(data: BreedingData, evaluation: dict, direction: str = "max",
                    diversity_weight: float = .15, max_kinship: float = .30, top: int = 20) -> list[dict]:
    """Exploratory additive midparent+distance tradeoff, NOT predicted F1/yield."""
    if direction not in ('max','min'):
        raise ValueError('Direction must be max or min')
    if not (0 <= diversity_weight <= 1) or not (-1 <= max_kinship <= 2):
        raise ValueError('Invalid selection preference')
    # Never release cross recommendations when the model fails basic skill gate.
    if not evaluation['positive_skill_gate']:
        return []
    rows = evaluation['candidate_table']
    idx = [i for i, name in enumerate(data.ids) if rows.iloc[i]['genotype_qc_pass']]
    if len(idx) < 2:
        return []
    fitted = evaluation['model']
    pred = np.array([float(rows.iloc[i]['prediction']) for i in idx])
    sign = 1 if direction == 'max' else -1
    pick = np.argsort(sign*pred)[-min(40,len(idx)):]
    selected = [idx[k] for k in pick]
    raw = data.genotype[selected]
    K = fitted.kernel_.kernel(raw, raw)
    sd = max(float(np.std(data.phenotypes[np.isfinite(data.phenotypes)])), 1e-10)
    crosses = []
    for a,b in combinations(range(len(selected)),2):
        k = float(K[a,b])
        if k > max_kinship:
            continue
        i,j = selected[a],selected[b]
        x,y = data.genotype[i],data.genotype[j]
        valid = np.isfinite(x)&np.isfinite(y)&fitted.kernel_.keep
        if valid.sum()<2:
            continue
        # Under independent gamete segregation, estimated F1 heterozygosity at markers.
        pa, pb = x[valid]/2, y[valid]/2
        hetero = float(np.mean(pa*(1-pb)+(1-pa)*pb))
        midpoint = float((rows.iloc[i]['prediction']+rows.iloc[j]['prediction'])/2)
        diversity = max(0., 1.-k)/2
        score = sign*(midpoint - float(np.mean(data.phenotypes[np.isfinite(data.phenotypes)])))/sd + diversity_weight*diversity
        crosses.append({"parent_1":data.ids[i], "parent_2":data.ids[j],
                        "index_score":round(score,6), "additive_midparent_proxy":round(midpoint,6),
                        "genomic_relationship":round(k,6), "marker_expected_f1_heterozygosity":round(hetero,6),
                        "markers_for_heterozygosity":int(valid.sum()),
                        "decision_status":"RESEARCH_CANDIDATE_NOT_APPROVED"})
    return sorted(crosses,key=lambda q:q['index_score'],reverse=True)[:max(1,min(100,top))]
