"""Command line client."""
import argparse
import json
from .registry import capability_list
from .planner import deterministic_plan, llm_advisory_plan
from .demo import generate
from .jobs import execute, recent_jobs


def main():
    parser = argparse.ArgumentParser(prog="gurudev", description="GURUDEV.ai scientific workflow foundation")
    p = parser.add_subparsers(dest="command", required=True)
    p.add_parser("modules", help="See modules and their verified status")
    demo = p.add_parser("demo", help="Generate synthetic data and execute the starter GP pipeline")
    demo.add_argument("--output", default="gurudev_demo")
    plan = p.add_parser("plan", help="Plan a request using a strict capability allowlist")
    plan.add_argument("request")
    plan.add_argument("--llm", action="store_true", help="Use opt-in API planner (charges may apply)")
    run = p.add_parser("run", help="Run an approved QC or GP job")
    run.add_argument("--module", choices=["qc", "gp"], required=True)
    run.add_argument("--genotype", required=True)
    run.add_argument("--phenotype", required=True)
    run.add_argument("--trait", required=True)
    run.add_argument("--group", default=None)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--output", default="runs")
    status = p.add_parser("status", help="Show jobs saved in the local SQLite tracker")
    status.add_argument("--output", default="runs")
    campaign = p.add_parser("campaign", help="Run evidence-gated genomic breeding campaign (GBLUP, QC, cross triage)")
    campaign.add_argument("--genotype", required=True)
    campaign.add_argument("--phenotype", required=True)
    campaign.add_argument("--trait", required=True)
    campaign.add_argument("--group", default=None)
    campaign.add_argument("--direction", choices=["max", "min"], default="max")
    campaign.add_argument("--output", default="gurudev_campaigns")
    campaign.add_argument("--seed", type=int, default=42)
    agent = p.add_parser("agent-run", help="Optional LLM-driven, tool-limited breeding research coordinator")
    agent.add_argument("goal")
    agent.add_argument("--genotype", required=True)
    agent.add_argument("--phenotype", required=True)
    agent.add_argument("--trait", required=True)
    agent.add_argument("--group", default=None)
    agent.add_argument("--direction", choices=["max", "min"], default="max")
    agent.add_argument("--output", default="gurudev_campaigns")
    validate = p.add_parser("external-validate", help="Evaluate frozen GBLUP on independent data without refitting")
    validate.add_argument("--id", required=True)
    validate.add_argument("--genotype", required=True)
    validate.add_argument("--phenotype", required=True)
    validate.add_argument("--trait", required=True)
    validate.add_argument("--output", default="gurudev_campaigns")
    review = p.add_parser("approve-campaign", help="Human approval of research shortlist, not breeding deployment")
    review.add_argument("--id", required=True)
    review.add_argument("--output", default="gurudev_campaigns")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--justification", required=True)
    args = parser.parse_args()
    if args.command == "modules":
        print(json.dumps(capability_list(), indent=2))
    elif args.command == "plan":
        print(json.dumps((llm_advisory_plan(args.request) if args.llm else deterministic_plan(args.request)), indent=2))
    elif args.command == "demo":
        geno, pheno = generate(args.output)
        directory, record = execute("gp", geno, pheno, "grain_yield", output_root=str(args.output) + "/runs", seed=42)
        print("Synthetic demo completed:", directory)
        print("Out-of-fold evaluation:", record["metrics"])
    elif args.command == "run":
        directory, record = execute(args.module, args.genotype, args.phenotype, args.trait,
                                    output_root=args.output, group_column=args.group, seed=args.seed)
        print("Job:", directory)
        print(json.dumps({"status": record["status"], "metrics": record.get("metrics"), "qc": record["qc"]}, indent=2))
    elif args.command == "campaign":
        from .breeder_engine.workflow import run_campaign
        record=run_campaign(open(args.genotype,"rb").read(),open(args.phenotype,"rb").read(),
            args.trait, args.output,group=args.group,direction=args.direction,seed=args.seed)
        print(json.dumps({"job_id":record["job_id"], "status":record["status"],
            "scientific_checks":record["scientific_checks"],"evaluation":record["evaluation"],
            "folder":str(args.output)+"/"+record["job_id"]},indent=2))
    elif args.command == "agent-run":
        from .breeder_engine.agentic import run_agentic_campaign
        r=run_agentic_campaign(args.goal,open(args.genotype,"rb").read(),
            open(args.phenotype,"rb").read(),args.trait,args.output,
            group=args.group,direction=args.direction)
        print(json.dumps(r,indent=2))
    elif args.command == "external-validate":
        from .breeder_engine.external import evaluate_external
        ev=evaluate_external(args.output,args.id,open(args.genotype,"rb").read(),
                             open(args.phenotype,"rb").read(),args.trait)
        print(json.dumps(ev,indent=2))
    elif args.command == "approve-campaign":
        from .breeder_engine.workflow import approve_campaign
        record=approve_campaign(args.output,args.id,args.reviewer,args.justification)
        print(json.dumps({"job_id":record["job_id"],"status":record["status"],
                          "approval":record["approval"]},indent=2))
    elif args.command == "status":
        for row in recent_jobs(args.output):
            print(" | ".join(str(x) for x in row))

if __name__ == "__main__":
    main()
