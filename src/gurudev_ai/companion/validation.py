"""Deterministic post-execution validation; no self-modifying code or unsupported science."""
from __future__ import annotations
from pathlib import Path
import json
import math
import re
import pandas as pd
from gurudev_ai.jobs import execute, diagnose, log_event


def verified_gp_run(geno_path, pheno_path, trait, output_root, group_column=None):
    corrections = []
    # Bounded auto-fix: unique differences in column spelling/spacing/case only.
    # Scientific fields, missing observations or genotype codes are never guessed.
    header = list(pd.read_csv(pheno_path,nrows=0).columns)
    def canonical(value):
        return re.sub(r"[^a-z0-9]", "", value.casefold())
    def reconcile(value,kind):
        if value is None or value in header:
            return value
        matches=[h for h in header if canonical(h)==canonical(value)]
        if len(matches)==1:
            corrections.append({"type":"column_name_normalization", "field":kind,
                                "requested":value,"resolved":matches[0],
                                "rule":"unique case/spacing/punctuation match"})
            return matches[0]
        return value
    trait=reconcile(trait,"trait")
    group_column=reconcile(group_column,"group")
    try:
        folder, manifest=execute("gp", geno_path, pheno_path, trait,
                                 output_root=output_root, group_column=group_column)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Input/analysis error: {exc}. Suggested next step: {diagnose(exc)}") from exc
    if corrections:
        log_event(folder,"bounded_auto_repair",json.dumps(corrections))
        manifest["bounded_auto_repairs"] = corrections
        (Path(folder)/"manifest.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")
    # Validate evidence from the job, not simply a 'completed' string.
    if manifest.get("status") != "completed" or not manifest.get("validation",{}).get("nested_cv"):
        raise ValueError("GP result did not pass workflow status and nested CV checks")
    pred_path=Path(folder)/"out_of_fold_predictions.csv"
    report_path=Path(folder)/"report.md"
    if not pred_path.is_file() or not report_path.is_file():
        raise ValueError("Required GP output files are missing")
    predictions=pd.read_csv(pred_path)
    aligned=manifest["qc"]["matched_samples"]
    if len(predictions)!=aligned:
        raise ValueError("Out-of-fold row count differs from aligned input sample count")
    metrics=manifest.get("metrics",{})
    for metric in ("RMSE","MAE","R2"):
        if metric not in metrics or not math.isfinite(float(metrics[metric])):
            raise ValueError(f"GP metric {metric} is missing or non-finite")
    return {"job_id":manifest["job_id"],"status":"completed", "trait":trait,
            "metrics":metrics,"qc":manifest["qc"],"verification":{
                "nested_cv":True,"preprocessing_inside_folds":True,
                "matched_prediction_rows":True,"report_and_manifest_exist":True,
                "external_validation":False},
            "report_url":f"/api/gp/jobs/{manifest['job_id']}/report",
            "bounded_auto_repairs":corrections,
            "note":"Starter Ridge/ElasticNet nested-CV baseline. Not GBLUP, genomic EBVs, or out-of-population field validation."}
