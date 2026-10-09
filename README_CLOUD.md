# GURUDEV.ai — Temporary Online Trial Deployment

This is the real GURUDEV.ai v0.3 scientific codebase and browser voice-companion UI, adapted for password-protected **temporary** cloud hosting. It is *not* a completed research-grade SaaS. No dummy model has been substituted. The numerical science remains the v0.3 engine.

## Deploy without installing Python on your computer

1. Sign in to **https://github.com** and create a **private repository** such as `gurudev-ai-trial`.
2. Extract this ZIP to a folder, then upload **the contents of that folder** to the repository using **Add file → Upload files**. Keep the `src/gurudev_ai/...` hierarchy and `render.yaml` at the repository root. Do NOT upload only the ZIP file.
3. Sign in at **https://dashboard.render.com**, connect GitHub if prompted, and choose **New → Blueprint** (new names/UI may vary). Select the private GURUDEV.ai repository and review its `render.yaml`.
4. Set `GURUDEV_ONLINE_USER` and `GURUDEV_ONLINE_PASSWORD` in Render's secure environment-variable form. The password must contain at least 12 characters. NEVER commit passwords or API keys to GitHub or send them in chat.
5. Deploy. Render provides your actual `*.onrender.com` URL. Open it on a phone or laptop via HTTPS and enter the username/password when asked.
6. Test voice using the microphone button in a supported browser; voice recognition remains browser-dependent. Always allow microphone permission if you choose to use voice.

## Limitations that matter

- Render free services **sleep after 15 minutes without requests**, and their files/database can be discarded when sleeping/restarting. Therefore use trial data only. Tasks and observations may be lost. Click **Export temporary field-book backup** while records are available. This export does NOT automatically restore your data.
- All genotype/phenotype CSVs and notes are sent to the cloud host. Do not upload proprietary germplasm records, unpublished results, identifiable participant data, confidential plant breeding records, or secret keys in this trial.
- Only single-user Basic authentication; not a multi-user access-control system. No encrypted-at-rest data repository, persistent storage or research-institution security approval.
- No working cloud AI without separately provisioned credentials. The offline science and limited companion replies still operate.
- If the cloud server exceeds CPU/RAM/time limits, numerical analyses can fail. Use small non-sensitive data to verify functionality.
- GURUDEV Diversity/GWAS/E-Design R packages are not yet integrated. This remains a development release, NOT a fully autonomous agent.
- For long-term protected operation, upgrade to persistent managed storage, real identity and permissions, background job processing and end-to-end security verification.

**No live URL exists until the repository is uploaded and a hosting deployment succeeds.**
