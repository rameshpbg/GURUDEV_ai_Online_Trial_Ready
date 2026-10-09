# GURUDEV.ai v0.3 security model

## Current trust boundary

- Only run on localhost or a trusted isolated machine. There is no login, tenancy or network-service hardening. Do not deploy behind a public endpoint.
- Local SQLite stores companion tasks and voice-derived text in plaintext. Genomic campaign artifacts are saved unencrypted to local directories. The user must control filesystem permissions and backups.
- API has upload-size and genotype-matrix limits but *not* a production rate limiter, separate compute worker, request timeout or resource cgroups. Large analyses may block the server.
- SHA256 of input bytes is included in the run manifest. The JSONL audit hash chain detects ordinary edits, but not deletion/replacement by a machine administrator; external signatures are required for immutable provenance.
- Numerical models use `.npz` loaded with `allow_pickle=False`; never unpickle outside models from untrusted sources.
- Voice input uses browser/OS speech recognition with device/provider-dependent privacy; device vendor may process utterances remotely.
- Optional cloud AI sends research goal and structured QC/performance summary to the chosen model provider. No default cloud transmission of raw genotype tables through the agent tool pipeline. Do not use confidential data until contractual and privacy review is complete.
- Agent tools are explicit allowlisted functions, no arbitrary shell/code access or physical/laboratory action. The LLM does not approve scientific claims, crossing, release or field deployment.

## Production prerequisites

1. Identity provider, RBAC (breeder, analyst, statistician, admin, reviewer), workspace-level access and audit of approvals.
2. Upload scanning, per-project storage quotas, execution limits, dependency pinning, SBOM and vulnerability response.
3. Signed immutable scientific artifacts and model provenance with content-addressed dataset versions.
4. Sandboxed R/Python execution using isolated workers, job timeouts and controlled tool capabilities; no unrestricted agent self-patching.
5. Encrypted at-rest data, secure key management, retention/deletion policies and institutional data governance.
6. Human approval workflow for breeding actions and any biotechnology laboratory operations.
7. AI-agent evals including prompt-injection resistance, tool-policy compliance, unsupported-claim detection and trace privacy.
