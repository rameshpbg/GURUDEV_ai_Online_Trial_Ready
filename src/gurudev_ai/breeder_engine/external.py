"""Safe model serialization and true, no-refit independent population evaluation.

No pickle/joblib loading; numpy arrays are loaded with allow_pickle=False.
Test-set phenotypes never influence marker selection, imputation, or the model.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .science import _frame, _dosage, _scores
from .workflow import _require_job, _write, _now, AuditLog


def save_model(folder: Path, data, result) -> None:
    model = result['model']
    kernel = model.kernel_
    np.savez_compressed(folder/'trained_gblup_model.npz',
        retained_marker_names=np.asarray(data.markers)[kernel.keep],
        training_ids=np.asarray([data.ids[i] for i in np.flatnonzero(np.isfinite(data.phenotypes))]),
        allele_frequencies=kernel.p.astype('float64'),
        centered_training_genotypes=kernel.ztrain.astype('float64'),
        ridge_coefficients=model.alpha_.astype('float64'),
        training_trait_mean=np.array(model.mean_),
        denominator=np.array(kernel.denominator),
        penalty=np.array(model.penalty))


def evaluate_external(root: str|Path,job_id: str, genotype_csv: bytes,
                      phenotype_csv: bytes, trait: str) -> dict:
    folder = _require_job(root,job_id)
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    if manifest['status'] not in ('SCIENTIFIC_HOLD','AWAITING_HUMAN_REVIEW','REVIEWED_SHORTLIST'):
        raise ValueError('Campaign must finish successfully before external validation')
    if trait != manifest['trait']:
        raise ValueError('External phenotype trait must match trained model')
    if (folder/'external_validation.json').exists():
        raise ValueError('External dataset has already been evaluated for this job; create another campaign for another experiment')
    if not AuditLog(folder).verify():
        raise ValueError('Campaign audit log failed integrity verification')
    with np.load(folder/'trained_gblup_model.npz',allow_pickle=False) as model:
        needed=list(model['retained_marker_names'].astype(str))
        p=np.array(model['allele_frequencies'],dtype=float)
        ztrain=np.array(model['centered_training_genotypes'],dtype=float)
        alpha=np.array(model['ridge_coefficients'],dtype=float)
        mean=float(model['training_trait_mean'])
        denom=float(model['denominator'])
        training_ids=set(model['training_ids'].astype(str))
    g,phe=_frame(genotype_csv,'External genotypes'),_frame(phenotype_csv,'External phenotypes')
    if len(needed)<2 or any(m not in g.columns for m in needed):
        raise ValueError('External data lack one or more retained SNP IDs; no implicit marker mapping permitted')
    if (set(g.index) & training_ids) or (set(phe.index) & training_ids):
        raise ValueError('External validation cannot reuse a training sample identifier')
    if trait not in phe.columns:
        raise ValueError('Trait not present in external phenotypes')
    available=[sample for sample in phe.index if sample in g.index]
    if len(available)<10:
        raise ValueError('External evaluation requires >=10 independently phenotyped-genotyped samples')
    y=pd.to_numeric(phe.loc[available,trait],errors='coerce').to_numpy(dtype=float)
    if not np.isfinite(y).all() or np.std(y)<=1e-12:
        raise ValueError('External phenotypes must be finite, numeric and variable')
    vals=g.loc[available,needed].apply(lambda s:s.map(_dosage)).to_numpy(dtype=float)
    if (np.isnan(vals).mean(axis=1)>.20).any():
        raise ValueError('External entries exceed 20% missing retained SNPs; investigate missingness first')
    ii,jj=np.where(np.isnan(vals))
    vals[ii,jj]=2*p[jj]
    z=vals-2*p
    pred=mean+(z@ztrain.T/denom)@alpha
    baseline=np.full(len(y),mean)
    sc,bs=_scores(y,pred),_scores(y,baseline)
    passed=bool(sc['rmse']<bs['rmse'] and sc['pearson_r'] is not None and sc['pearson_r']>0)
    evaluation={'n_samples':len(y),'trait':trait,'model':sc,'train_mean_baseline':bs,
        'external_skill_pass':passed,'protocol':'no-refit prospective-independent IDs; exact marker-ID alignment; same allele orientation required',
        'warning':'External independence of site/year/breeding cycle must also be confirmed from experimental metadata.'}
    pd.DataFrame({'sample_id':available,'observed':y,'prediction':pred,
                  'train_mean_baseline':baseline}).to_csv(folder/'external_predictions.csv',index=False)
    _write(folder/'external_validation.json',evaluation)
    AuditLog(folder).append('external_validation_agent','independent_population_evaluation',evaluation)
    manifest['scientific_checks']['prospective_external_validation']=True
    manifest['scientific_checks']['external_skill_pass']=passed
    manifest['external_evaluation']=evaluation
    if not passed:
        manifest['status']='SCIENTIFIC_HOLD'
        manifest['approval']=None
    elif manifest['status']=='SCIENTIFIC_HOLD':
        manifest['status']='AWAITING_HUMAN_REVIEW' if manifest['scientific_checks']['positive_skill'] else 'SCIENTIFIC_HOLD'
    _write(folder/'manifest.json',manifest)
    return evaluation
