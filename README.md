# GURUDEV.ai v0.3.0 — Evidence-Driven Agentic Breeder

**Serious scientific development build — not a finished world-class product and not validated for breeding deployment.**

GURUDEV.ai combines the existing voice-capable breeder companion with a new scientific breeding engine:

- Input validation for matched diploid biallelic SNP genotypes (`0/1/2`, or `AA/AB/BB`) and adjusted trait values, including unphenotyped candidates.
- **GBLUP** with VanRaden-style genomic relationship kernel, training-only allele-frequency calculation, missing-marker imputation, SNP missingness/MAF QC, kernel regularization tuning and nested random or group cross-validation.
- Evaluation against fold-specific training-mean prediction, **automatic hold of cross proposals** when predictive skill is insufficient, and deliberately labelled exploratory cross shortlist when sufficient internal predictive skill exists.
- A **frozen numerical model** (`.npz`; no pickle) for no-refit independent-population evaluation. Overlap with training sample IDs is rejected; external performance compared with the fixed training-mean baseline.
- Reproducible audit folder with input hashes, model hyperparameters, fold assignments, out-of-fold and candidate predictions, conditional cross shortlist, 350-DPI PNG/vector PDF graphics and human review gate.
- An **optional cloud AI research coordinator** using the OpenAI Agents SDK. Its tools are allowlisted: inspect data, run one scientifically gated campaign and review evidence; it has no shell or breeding decision approval access. Requires an API key and independent end-to-end credentialed testing.
- Existing local breeder companion: voice dictation/output (browser dependent), field book, tasks, trial structural QC, exploratory phenotypic parent index, baseline GP Auto-Lab.

## What GURUDEV.ai is NOT yet

This is **not** automatically superior to existing scientific software, not a validated multi-crop production service, not a native HapMap/VCF analysis pipeline, and not an auto-learning LLM. No authentication, encrypted at-rest project storage, production job queue, CI/CD deployment, real-time laboratory actuation, unrestricted self-patching, prospective multi-environment validation, or independent IRRI/ICAR benchmark has been implemented. Do not expose the included API to the public internet.

Legacy GURUDEV Diversity, GWAS, E-Design and other R packages are **not integrated** because their authoritative source code has not been supplied to this build.

## Installation

1. Download and extract ZIP. Requires **Python 3.10+**, an internet connection once for dependencies, and Windows/macOS/Linux.
2. Windows: double-click `START_GURUDEV_WINDOWS.bat`; browser local URL is **http://127.0.0.1:8502**.
3. Or terminal:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
python -m gurudev_ai.companion.server
```

Voice input is push-to-talk in supported browser environments. It may require device permissions and browser processing of audio. Normal typing remains available.

## Scientifically auditable breeding campaign — offline, no API key

```bash
python -m gurudev_ai campaign \
  --genotype examples/demo_genotype.csv \
  --phenotype examples/demo_phenotype.csv \
  --trait grain_yield --group family \
  --direction max --output campaign_runs
```

Run results are written under `campaign_runs/<32-character-id>/` with `manifest.json`, `events.jsonl`, `scientific_report.md`, `candidate_predictions.csv`, `out_of_fold_predictions.csv`, `trained_gblup_model.npz`, `cross_shortlist.json` and figures. **Included example data are synthetic and only establish functionality.**

Random individual CV can overestimate generalization in related germplasm; grouped CV by family/location/year is advised when scientifically appropriate. External evaluation is a separate, stronger gate. Real-world performance and genotypic accuracy remain unproven until independently benchmarked.

## Freeze and independently validate the trained model

```bash
python -m gurudev_ai external-validate \
  --id <RUN_ID> --output campaign_runs \
  --genotype external_genotypes.csv \
  --phenotype external_phenotypes.csv \
  --trait grain_yield
```

The independent dataset needs **different sample IDs** and the **same retained SNP IDs, orientation, diploid dosage convention and trait units**. The code does not retrain, re-select SNPs or change allele frequencies. This does not independently establish that an external site/year is truly prospective: metadata must be reviewed by the scientist.

## Human review

Crossing is NEVER performed automatically. To acknowledge review of a shortlist (not authorize field operations), use:

```bash
python -m gurudev_ai approve-campaign --id <RUN_ID> \
  --output campaign_runs --reviewer "Breeder Reviewer" \
  --justification "Reviewed with field and pedigree information; validation limitations understood"
```

This approval applies only to **review of exploratory cross candidates**, never cultivar release, laboratory protocols or field actuation.

## Optional AI tool-using breeder coordinator

```bash
python -m pip install -e '.[agentic]'
# Set OPENAI_API_KEY privately in the process environment; do not put secrets in source code or chat.
python -m gurudev_ai agent-run \
  'Inspect these genomic data, evaluate yield predictability, and explain if a cross shortlist is defensible' \
  --genotype examples/demo_genotype.csv \
  --phenotype examples/demo_phenotype.csv \
  --trait grain_yield --group family \
  --output campaign_runs
```

In this mode, the cloud service receives the natural-language goal and **structured QC/evaluation summaries**, not the raw genotype CSV, via the declared tools. Calls may incur charges. The tool loop has not yet been live API-tested, because no authorized API key was available. Tracing is disabled by default in this integration to avoid exporting sensitive research context.

## Scientific output interpretation

- `predicted_oof` / `out_of_fold_predictions.csv`: unbiased-within-chosen-CV-scheme holdout predictions, not external prospective evidence.
- `candidate_predictions.csv`: **in-sample fitted** model predictions for phenotyped entries, model-based predictions for unphenotyped entries. These are different evidence classes.
- `cross_shortlist.json`: additive midparent-index proxies, genomic relationship and marker-level estimated F1 heterozygosity. **Not** predicted F1 field performance, recombination variance or heterosis.
- `SCIENTIFIC_HOLD`: failed basic model-skill gate or subsequently failed external check; no crosses should be promoted.
- `AWAITING_HUMAN_REVIEW`: internal gate passed; hypothetical shortlist requires scientific evaluation.
- `REVIEWED_SHORTLIST`: explicit local review acknowledgement; not field crossing authority.

## Tests

```bash
python -m pip install -e '.[dev]'
pytest -q
node --check src/gurudev_ai/companion/static/app.js   # if Node is available
```

All 34 included tests were run on the development environment for this version (separate real-sample validation not performed). Tests cover source compatibility, input rejection, CV grouping and leakage avoidance, positive/negative skill gates, frozen-model validation without refitting, tamper detection of audit records, API endpoints and local workflows.

## Scientific/engineering priorities

1. Obtain and freeze **authoritative real rice panel + trial datasets** with experimental layouts, SNP IDs, population structure, locations, seasons and phenotype reliability. Perform external blind benchmarking against rrBLUP/BGLR/GBLUP/R models.
2. Capture MIAPPE-compliant metadata and support BrAPI 2.1 data connections, genomic VCF/HapMap and multi-environment trial analysis.
3. Add software-level authorization, encrypted storage, immutable signed logs, user roles, multiple projects and a durable job queue with retries/cancellation.
4. Connect legacy GURUDEV scientific R packages with independent numerical reference tests and automated regression checks.
5. Extend the breeder coordinator to documented multi-trait selection objectives, expected progeny value uncertainty, mating design/OCS, G×E, phenomics, multi-omics and real field data collection.
6. Validate voice on target devices and languages. Build support for low-connectivity Android deployment with privacy safeguards.

See `docs/SCIENTIFIC_ACCEPTANCE_v0_3.md` and `SECURITY.md` for acceptance criteria and risks.

**© Scientific development project. Product name GURUDEV.ai used provisionally; intellectual property, branding and domain verification pending.**
