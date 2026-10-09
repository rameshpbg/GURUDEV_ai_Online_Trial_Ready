"""Capability registry. 'planned' capabilities cannot be executed."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    status: str
    details: str

CAPABILITIES = [
    Capability("qc", "Genotype–phenotype QC", "implemented", "CSV import, sample alignment and explicit validation"),
    Capability("gp", "Genomic prediction (starter)", "implemented", "Nested CV, Ridge/ElasticNet training and reports"),
    Capability("breeding_campaign", "Evidence-gated genomic breeding campaign", "implemented", "GBLUP nested CV, sample QC, gated cross shortlist, frozen external validation and audit"),
    Capability("diversity", "GURUDEV Diversity", "adapter_pending", "Connect and validate authoritative R source package"),
    Capability("e_design", "GURUDEV E-Design", "adapter_pending", "Connect and validate experimental-design backend"),
    Capability("gwas", "GURUDEV GWAS", "adapter_pending", "Native R backend and independent statistical checks required"),
    Capability("qtl", "Linkage/QTL mapping", "planned", "Map construction, QTL methods and validation"),
    Capability("simulation", "Breeding simulation", "planned", "Cross prediction, progeny simulation and MAGIC founders"),
    Capability("phenomics", "Digital phenomics", "planned", "UAV, field and seed imaging"),
    Capability("omics", "Multi-omics & biotechnology", "planned", "RNA-seq, proteomics, metabolomics and experimental workflows"),
]
ALLOWED = {c.key for c in CAPABILITIES if c.status == "implemented"}

def capability_list():
    return [c.__dict__ for c in CAPABILITIES]
