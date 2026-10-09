# GURUDEV.ai v0.4.1 — Engineering Status (10 October 2026)

## Tested locally in current container

- **82 / 82 Python tests passed** (`pytest -q`; synthetic or numerical-reference tests only).
- JavaScript static syntax parsed successfully (`node --check`).
- UI research navigation, agent form/planning and knowledge navigation checked in headless Chromium using mocked API responses. This is a **browser render smoke test**, not real Render hosting or physical microphone testing.
- Browser API operations checked independently via FastAPI `TestClient` for Anova, GWAS and agent routing.
- Independent `scipy` univariate regression and `statsmodels` GLS coefficient/p-value numerical comparisons pass.
- Independent `statsmodels` RCBD fixed-effect ANOVA reference test passes. Residual Shapiro/Levene descriptive checks are reported with explicit warnings.
- Synthetic null-marker type-I error sanity check passes. No real-population calibration or prospective science claims.
- Reproducible GWAS job archives include 350-DPI PNG + vector PDF figures, QC, audit, SHA256 hashes and scientific-review state.
- Cloud HTTP Basic auth tests confirm protection of the knowledge API and fail-closed missing credentials.

## Implemented in source but not live on the user's Render site yet

- New Scientific Analysis Studio with actual balanced single/multi-environment RCBD and CRD ANOVA runner.
- New genome-wide marker association engine: population-PC GLM and approximate null-REML kinship LMM, QC, significance/FDR and reports.
- Scientific Task Agent: bounded natural-language tool routing, require datasets, controlled execute, review stops and audit.
- New diploid genetic-diversity analytics with PCA, Ho/He/PIC and Weir–Cockerham theta, locus-bootstrap warnings, figure/archive API. The full existing Diversity R package is NOT integrated.
- New Data Import Lab adapters: CSV, TSV/TXT, XLSX, diploid HapMap and restricted diploid VCF/VCF.gz, with reject-on-ambiguity policy.
- Curated searchable Knowledge Library, currently 21 source-linked resource entries.
- Existing GBLUP campaign, GP baseline, voice companion, field book and task management retained.

## Scientific scope not proven

- No user-provided real rice multi-environment SNP/phenotype datasets were uploaded in this build.
- No prospective field validation, independent multi-institution benchmark, complete GAPIT/mrMLM validation or R-package integration.
- No native full PLINK VCF INFO/FORMAT QC, polyploid and multi-allelic integration, unbalanced REML BLUE/BLUP or functional omics analysis.
- No reliable uninterrupted agent execution, self-modifying/retraining LLM, institutional multi-user security, encrypted durable storage, job queue, compute scaling or completed public beta.
- Render Free 512-MB RAM and temporary disk are **not suitable for production 44K SNP × hundreds of genotypes**, confidential datasets or lengthy job execution.

## Deployment blocker

Current GitHub integration **can read** `rameshpbg/GURUDEV_ai_Online_Trial_Ready` but creating a feature branch returned **403 `Resource not accessible by integration`**. No source files were uploaded or committed to the repository, and no new Render deployment was performed. Avoid claiming the website contains v0.4 until the repository is updated through an authorized write workflow and the hosted version is verified.

## Next production milestones

1. Obtain GitHub branch/pull-request write permission and deploy a separate authenticated staging service; verify cloud-ready endpoints and rollback.
2. Obtain authoritative, permitted, de-identified rice genotypes and multi-location field trials for blind R-reference benchmarking, with verified genome assembly/allele coding.
3. Production data layer: object storage, databases, backups, access control, job queue, compute workers, schema/ontology/MIAPPE/BrAPI.
4. Native E-Design, GURUDEV Diversity, GAPIT/mrMLM and quantitative genetic/mixed-model engines against independent numeric oracles.
5. Controlled multi-agent runtime with traceable tools, human approvals, continuous integration and secure auto-debug/redeploy gates.

**Release classification: offline technical research preview; not a global-production-ready autonomous breeder.**

## Synthetic example usability regression checks

- Balanced complete 24-plot synthetic RCBD dataset is bundled and runs both by API and directly; the original dataset containing one blank yield remains a documented import/QC rejection example.
- Full genotype and population metadata demo pair is run through the diversity HTTP endpoint, recording an unapproved report and high-resolution figures.
- Four automated example regression tests added; **82 passing technical tests**.

## CI workflow added

A least-privilege GitHub Actions quality workflow is included (Python 3.11, Python 3.12, JS syntax, compileall). It has **not yet executed in GitHub** because the integration cannot push to the repository.
