# GURUDEV.ai v0.4.1 — Scientific Engine and Breeder Research Agent

**Research development release. Not production-certified, and not a complete plant breeding or biotechnology analysis suite.**

GURUDEV.ai is a crop-independent, modular scientific software effort. Its purpose is to grow into an agentic research environment that unifies experimental design, quantitative genetics, genetic diversity, mapping, genomic prediction, breeding simulations, field phenomics, molecular biotechnology, multi-omics, and AI/ML/DL. **Only the explicitly implemented methods below are executable in this release.**

## Working functions (local technical tests)

| Area | Currently executable | Explicit limits |
|---|---|---|
| File import | CSV, TSV/TXT, XLSX, diploid biallelic HapMap, restricted VCF GT/.vcf.gz; sample/marker checks, import preview, normalization | Not `.xls`, multi-ALT/polyploid VCF, PLINK BGEN/PGEN, FASTQ/BAM, arbitrary biological schema inference |
| Diploid genetic diversity | PCA, Ho/He, PIC, Weir–Cockerham theta with locus-bootstrap interval and high-resolution PCA/FST figures | Not full FIT/FIS, AMOVA, multi-allelic or polyploid inference; source R Diversity remains unintegrated |
| Trial ANOVA | Strictly balanced single-trait CRD, RCBD and multi-environment RCBD including G×E, method-of-moments entry mean H², experimental CV, unadjusted LSD and residual Shapiro/Levene screens | Does not perform REML, missing-plot imputation, BLUE/BLUP, alpha-lattice, split plot or spatial correction |
| Association mapping | PC-adjusted GLM; null REML kinship LMM (EMMAX-like approximation), SNP call-rate/MAF filters, BH-FDR/Bonferroni, publication-resolution association-index/QQ figures, audit folders | No LOCO, allele orientation harmonization, fine mapping, validated FarmCPU/BLINK/mrMLM or genome annotation |
| Genomic prediction | Ridge/ElasticNet nested CV; GBLUP with nested/group CV and frozen independent population evaluation | Real crop/family/year external validation incomplete; no Bayesian, deep learning or multi-trait engine yet |
| Crossing | Exploratory midparent and marker relationship metrics, review gates on predictive skill | Not predicted recombination outcomes or validated genetic gain; no automatic crossing approval |
| Research agent | Natural language intent routing, data checks, allowlisted execution of ANOVA/GWAS/GBLUP/population diversity, automatic artefact logging and stop-for-review | Deterministic goal router; not a permanently running autonomous LLM or unrestricted automatic debugger |
| Breeder companion | Field notes, tasks, voice interaction in supported browsers, basic conversational workflows | Offline fallback is limited; voice speech recognition depends on browser/vendor |
| Knowledge library | 21 curated, provenance-linked learning resources and search | Not a comprehensive verified literature search index; links/content need periodic review |

**Method readiness matters.** The Scientific Analysis Studio shows implemented/technical-test versus planned methods. An item in the catalogue is not a claim that its statistical engine has been implemented.

## Start without an LLM subscription

### Local execution

- Windows: extract the ZIP and double-click `START_GURUDEV_WINDOWS.bat` (Python 3.10+ required).
- Linux/macOS: `sh START_GURUDEV_LINUX_MAC.sh`.
- Browser URL: `http://127.0.0.1:8502`.

Alternatively:

```bash
python -m pip install -e '.[dev]'
python -m gurudev_ai.companion.server
```

The source package also contains `cloud_server.py` and `render.yaml` for authenticated temporary Render hosting, **not** an institutional secure SaaS environment.

### Test the release

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

Input templates are in `examples/`. For an immediately runnable balanced ANOVA, use `demo_field_trial_complete.csv`; `demo_field_trial.csv` intentionally has a missing yield for the QC/error demonstration. For genetic diversity, upload `demo_genotype.csv` together with `demo_population_metadata.csv`. All sample datasets are **synthetic** and must not be represented as real field results.

## Operating the new Research Studio

1. Open **Data Import Lab** to inspect formats, sample IDs, marker orientation and transformations before analysis.
2. Open **Genetic Diversity Lab** to provide diploid SNP genotypes and explicitly declared population groups for PCA, Ho/He, PIC and WC84 theta.
3. Open **Scientific Analysis Studio**. Choose **Scientific Task Agent** to enter a research assignment, identify required data, and then explicitly execute a single supported tool. Unsupported/multimodule requests stop and request clarification.
4. For replicated trials, choose **CRD/RCBD ANOVA**, upload a row-per-plot table with `sample_id`, `rep`, trait and optional `environment`. Unbalanced trials are rejected.
5. For GWAS, upload **sample-by-SNP diploid 0/1/2** genotypes (or a declared HapMap/VCF), a one-row-per-individual **experiment-adjusted** phenotype table, choose a trait, PCs, model and QC limits. Results include raw p-values, BH q-values, Bonferroni p-values, estimated effects, high-resolution PNG/PDF figures and a report. Scientific release is blocked.
6. Open **Knowledge Library** for key formulas/interpretation cautions and primary references.

**Avoid confidential breeding data in the Render Free trial.** Uploaded material, observations and results are processed on that server, whose disk and SQLite database are temporary. Free CPU/RAM and upload limits cannot accommodate large 44K SNP chips or production workloads reliably. Separate storage, job queue and research computing must be engineered before production.

## Source code layout

```
src/gurudev_ai/io/importer.py                 # explicit genotype/table formats
src/gurudev_ai/research_core/quantitative.py   # balanced CRD/RCBD
src/gurudev_ai/research_core/diversity.py      # diploid diversity, PCA and WC84 theta
src/gurudev_ai/research_core/diversity_pipeline.py # QA, artifacts, figures
src/gurudev_ai/research_core/gwas.py           # PC GLM / approximate kinship LMM
src/gurudev_ai/research_core/gwas_pipeline.py  # artifact, hash, report, audit
src/gurudev_ai/research_core/gwas_figures.py   # 350-DPI plots and vector PDF
src/gurudev_ai/research_core/agent.py          # goal-to-allowlisted-tool router
src/gurudev_ai/research_core/knowledge.py      # curated knowledge
src/gurudev_ai/research_core/catalog.py        # scientific capability maturity
src/gurudev_ai/companion/server.py             # app / APIs
cloud_server.py                                # temporary HTTP Basic authentication
```

## Continuous integration

The repository includes `.github/workflows/quality.yml`: it runs Python 3.11 and 3.12 tests, checks browser JavaScript syntax, and compiles Python sources on each pull request and push to `main`. **The workflow has not been run on GitHub because repository write access was unavailable in this session.** CI passage must not be mistaken for agronomic validation.

## Validation and provenance

- Synthetic null-marker association p-value calibration test; causal-marker positive control.
- Independent `scipy.stats.linregress` and `statsmodels.GLS` marker coefficient/p-value comparisons.
- RCBD ANOVA independently checked against `statsmodels` OLS Type-II ANOVA.
- Import regression tests include malformed, multiallelic and ploidy-incompatible VCF rejection, duplicate IDs, invalid genotype dosages, split-trial balance, missingness, and hosted API uploads.
- Browser navigation and JS syntax checked; **browser interaction tests use mocked responses, not a real Render launch or microphone**.
- Every GWAS run stores data hashes, parameters, complete marker statistics, 350-DPI/vector figures, and a scientific-review gate.

No independent real-crop validation, across-population field trial, prospective breeding-gain study, commercial security audit or benchmark against full GAPIT/ASReml workflows has been performed. Never claim otherwise.

**Guidance:** `docs/GURUDEV_AI_MASTER_SPEC_v1.md`, `docs/SCIENTIFIC_ACCEPTANCE_v0_3.md`, `docs/IMPORT_CONTRACT.md`, `SECURITY.md`, `README_CLOUD.md`, and `STATUS.md`.
