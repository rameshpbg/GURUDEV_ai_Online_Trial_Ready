"""Conservative QC and alignment. All genotype matrix SNPs are rows of samples."""
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import numpy as np

IDENTIFIERS = ("sample_id", "Sample_ID", "Taxa", "taxa", "Genotype", "genotype", "ID", "id")
MISSING = {"", "NA", "NAN", "NONE", "NULL", "--", ".", "-"}
MAP = {"AA": 0.0, "AB": 1.0, "BA": 1.0, "BB": 2.0, "0": 0.0, "1": 1.0, "2": 2.0}

@dataclass
class Dataset:
    X: pd.DataFrame
    y: pd.Series
    ids: list[str]
    groups: pd.Series | None
    qc: dict


def _idcol(df: pd.DataFrame) -> str:
    found = [c for c in IDENTIFIERS if c in df.columns]
    if not found:
        raise ValueError("Sample identifier column not found; use sample_id, Taxa, Genotype or ID.")
    return found[0]


def _clean_ids(df: pd.DataFrame, label: str):
    field = _idcol(df)
    raw = df[field]
    if raw.isna().any():
        raise ValueError(f"{label} contains missing sample identifiers")
    clean = raw.astype(str).str.strip()
    if (clean == "").any() or clean.duplicated().any():
        raise ValueError(f"{label} contains blank or duplicated sample identifiers")
    cleaned = int((clean != raw.astype(str)).sum())
    result = df.drop(columns=[field]).copy()
    result.index = pd.Index(clean, name="sample_id")
    return result, cleaned


def _allele_value(v):
    if pd.isna(v):
        return np.nan
    key = str(v).strip().upper()
    if key in MISSING:
        return np.nan
    if key in MAP:
        return MAP[key]
    try:
        number = float(key)
    except ValueError:
        raise ValueError(f"Unexpected genotype value '{str(v)[:30]}': use 0/1/2 or AA/AB/BB (or blank for missing)") from None
    if number not in (0.0, 1.0, 2.0):
        raise ValueError(f"Unsupported genotype value {number}; expected 0, 1 or 2")
    return number


def load_dataset(genotype: str | Path, phenotype: str | Path, trait: str, group_column: str | None = None, min_samples: int = 16) -> Dataset:
    geno = pd.read_csv(genotype, dtype=str)
    pheno = pd.read_csv(phenotype, dtype=str)
    g, gtrim = _clean_ids(geno, "Genotype file")
    p, ptrim = _clean_ids(pheno, "Phenotype file")
    if trait not in p.columns:
        raise ValueError(f"Trait '{trait}' is not in phenotype columns: {list(p.columns)}")
    if group_column and group_column not in p.columns:
        raise ValueError(f"Group '{group_column}' is not in phenotype columns")
    matched = p.index.intersection(g.index, sort=False)
    if len(matched) == 0:
        raise ValueError("No matching sample IDs across the genotype and phenotype files. Review spelling and sample_id alignment.")
    y = pd.to_numeric(p.loc[matched, trait], errors="coerce")
    valid = y.notna() & np.isfinite(y)
    matched = matched[valid.to_numpy()]
    if len(matched) < min_samples:
        raise ValueError(f"Only {len(matched)} overlapping samples with numeric phenotypes; need at least {min_samples} for this demonstration pipeline")
    if len(g.columns) < 2:
        raise ValueError("At least two markers are required")
    X = g.loc[matched].apply(lambda col: col.map(_allele_value))
    X = X.astype(float)
    completely_missing = X.columns[X.isna().all()].tolist()
    if completely_missing:
        X = X.drop(columns=completely_missing)
    if X.shape[1] < 2:
        raise ValueError("Fewer than two usable markers remain")
    if not np.isfinite(y.loc[matched].astype(float).to_numpy()).all():
        raise ValueError("Phenotype contains infinite or invalid values")
    groups = None
    if group_column:
        groups = p.loc[matched, group_column].copy()
        if groups.isna().any() or groups.astype(str).str.strip().eq("").any():
            raise ValueError("Group column contains missing entries; grouped CV cannot proceed")
        groups = groups.astype(str).str.strip()
        if groups.nunique() < 4:
            raise ValueError("Grouped nested CV requires at least four independent group labels")
    if float(y.loc[matched].astype(float).std()) == 0:
        raise ValueError("Trait has zero variation; genomic prediction performance is not estimable")
    qc = {
        "genotype_samples": len(g), "phenotype_samples": len(p),
        "matched_samples": len(matched), "markers_used": X.shape[1],
        "excluded_all_missing_markers": completely_missing,
        "genotype_missing_fraction": round(float(X.isna().mean().mean()), 6),
        "trimmed_genotype_ids": gtrim, "trimmed_phenotype_ids": ptrim,
        "cv_strategy": "grouped" if group_column else "random_individual",
        "group_column": group_column, "sample_overlap_fraction_genotype": round(len(matched) / len(g), 4),
        "sample_overlap_fraction_phenotype": round(len(matched) / len(p), 4),
    }
    return Dataset(X=X, y=y.loc[matched].astype(float), ids=matched.tolist(), groups=groups, qc=qc)
