"""Auditable local jobs and bounded, non-destructive failure diagnostics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import uuid
from . import __version__
from .data import load_dataset
from .gp import train_nested
from .registry import ALLOWED


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def init_db(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = root / "gurudev_jobs.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created TEXT, status TEXT, module TEXT, trait TEXT, directory TEXT, error TEXT)")
    return db


def log_event(directory, label, message):
    with open(Path(directory) / "events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": stamp(), "stage": label, "message": message}, default=str) + "\n")


def diagnose(exc: Exception) -> str:
    text = str(exc).lower()
    if "no matching sample" in text:
        return "Inspect ID spellings and mapping in both CSV files. No fuzzy merging is performed."
    if "duplicat" in text:
        return "Resolve repeated sample identifiers against source records; automatic deduplication is unsafe."
    if "genotype value" in text:
        return "Recode biallelic SNP genotypes to 0/1/2 or AA/AB/BB; do not guess allele polarity."
    if "group" in text:
        return "Review independent family/environment group labels and required number of groups."
    if "sample identifier" in text:
        return "Rename the ID column to sample_id or one of the recognized aliases."
    return "Inspect events.jsonl and traceback in your development environment. No unverified automatic code patch was applied."


def execute(module: str, genotype, phenotype, trait, output_root="runs", group_column=None, seed=42):
    if module not in ALLOWED:
        raise ValueError(f"Module '{module}' is not executable in v{__version__}; approved modules: {sorted(ALLOWED)}")
    root = Path(output_root).resolve()
    db = init_db(root)
    jid = uuid.uuid4().hex[:12]
    folder = root / jid
    folder.mkdir(parents=True, exist_ok=False)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)", (jid, stamp(), "running", module, trait, str(folder), None))
    manifest = {"job_id": jid, "version": __version__, "module": module, "trait": trait, "group_column": group_column,
                "seed": seed, "created_utc": stamp(), "files": {}, "status": "running", "validation": {}}
    try:
        log_event(folder, "plan", f"Executing allowlisted '{module}' workflow")
        for label, value in (("genotype", genotype), ("phenotype", phenotype)):
            manifest["files"][label] = {"name": Path(value).name, "sha256": sha256(value)}
        ds = load_dataset(genotype, phenotype, trait, group_column)
        manifest["qc"] = ds.qc
        log_event(folder, "validate", f"Aligned {len(ds.ids)} samples and {ds.X.shape[1]} markers")
        (folder / "qc.json").write_text(json.dumps(ds.qc, indent=2), encoding="utf-8")
        if module == "gp":
            import joblib
            result = train_nested(ds, seed=seed)
            result.predictions.to_csv(folder / "out_of_fold_predictions.csv", index=False)
            joblib.dump(result.final_model, folder / "trained_model.joblib")
            manifest["metrics"] = result.metrics
            manifest["training"] = result.parameters
            manifest["fold_details"] = result.fold_details
            manifest["validation"] = {"nested_cv": True, "all_samples_predicted_once": True,
                                     "preprocessing_within_training_folds": True,
                                     "external_validation": False,
                                     "scope_note": "Related individuals: random CV estimates within-population prediction, not transfer to new families/environments."}
            log_event(folder, "analyse", f"Nested CV complete: RMSE={result.metrics['RMSE']}")
        else:
            manifest["validation"] = {"sample_id_alignment": True, "marker_format_check": True, "statistical_model_fitted": False}
            log_event(folder, "analyse", "QC-only job complete; no genomic prediction performed")
        manifest["status"] = "completed"
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE jobs SET status=? WHERE id=?", ("completed", jid))
        lines = ["# GURUDEV.ai job report", f"Job: `{jid}`", f"Module: `{module}`", f"Trait: `{trait}`", "", "## QC", "",
                 f"Aligned samples: {ds.qc['matched_samples']}", f"Markers used: {ds.qc['markers_used']}", f"Missing genotype fraction: {ds.qc['genotype_missing_fraction']}"]
        if module == "gp":
            lines += ["", "## Nested cross-validation metrics", ""]
            lines += [f"- {k}: {v}" for k, v in manifest["metrics"].items()]
            lines += ["", "## Scientific interpretation", "", "Outer-fold predictions are out-of-fold. Inner-fold tuning selects hyperparameters and estimator. Preprocessing is fit inside each training fold. These are not independent multi-environment or external validation results."]
        lines += ["", "## Reproducibility", "", f"Random seed: {seed}", "Inputs are SHA-256 recorded in manifest.json.", "The trained .joblib file is a Python pickle format; load only files you trust."]
        (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        log_event(folder, "verify", "Run completed and report written")
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        manifest["diagnostic_suggestion"] = diagnose(exc)
        log_event(folder, "failure", str(exc))
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE jobs SET status=?, error=? WHERE id=?", ("failed", str(exc)[:1000], jid))
        raise
    finally:
        manifest["finished_utc"] = stamp()
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return folder, manifest


def recent_jobs(output_root="runs", limit=20):
    db = init_db(output_root)
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT id, created, status, module, trait, directory, error FROM jobs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
