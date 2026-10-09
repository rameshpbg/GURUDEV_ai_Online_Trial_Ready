"""Allowlisted task planner and opt-in advisory language-model routing."""
import json
import os
from .registry import ALLOWED


def deterministic_plan(request: str) -> dict:
    lowered = request.lower()
    if any(w in lowered for w in ("genomic prediction", "predict breeding value", "predict phenotype", "genomic selection", " gp ")):
        target = "gp"
    elif any(w in lowered for w in ("quality control", "qc", "clean genotype", "validate data", "sample alignment")):
        target = "qc"
    else:
        target = "unsupported"
    return {"request": request, "route": target, "steps": ["import", "validate", "analyse", "verify", "report"] if target in ALLOWED else ["review_for_new_module"],
            "mode": "deterministic", "approval_required": target == "unsupported"}


def llm_advisory_plan(request: str, model: str | None = None) -> dict:
    """Requires explicit API use. LLM can suggest *only* an allowed module."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not present. LLM planner is disabled; use deterministic planning.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install optional LLM dependency: pip install -e '.[llm]'") from exc
    prompt = (
        "You are a conservative scientific workflow router for GURUDEV.ai. "
        "Given a request, return only a JSON object with route ('qc', 'gp', or 'unsupported') and rationale. "
        "qc means CSV data checking and alignment; gp means starter numeric-marker genomic prediction. "
        "Everything else, including GWAS and laboratory biotechnology, is unsupported. "
        "Do not claim analysis has run or that a module exists. Request: " + request
    )
    resp = OpenAI().responses.create(model=model or os.getenv("GURUDEV_AI_MODEL", "gpt-5-mini"), input=prompt)
    try:
        parsed = json.loads(resp.output_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Model output is not valid JSON; no task will execute") from exc
    if not isinstance(parsed, dict) or parsed.get("route") not in ALLOWED | {"unsupported"}:
        raise ValueError("Model suggested an unapproved route; no task will execute")
    return {"request": request, "route": parsed["route"], "rationale": str(parsed.get("rationale", ""))[:500],
            "steps": ["import", "validate", "analyse", "verify", "report"] if parsed["route"] in ALLOWED else ["review_for_new_module"],
            "mode": "llm_advisory", "approval_required": parsed["route"] == "unsupported"}
