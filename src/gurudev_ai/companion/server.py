"""Local-first companion API. Run only on localhost unless authenticated reverse proxy is configured."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Literal
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import store
from .agent import respond
from .breeding import rank_parents, trial_quality, parse_parent_csv, MAX_UPLOAD_BYTES

STATIC = Path(__file__).resolve().parent / "static"


class ChatMessage(BaseModel):
    text: str = Field(min_length=1,max_length=4000)
    project: str = Field(default="Rice",min_length=1,max_length=100)
    use_ai: bool = False


class Task(BaseModel):
    project: str = Field(default="Rice",min_length=1,max_length=100)
    title: str = Field(min_length=1,max_length=300)
    due_date: date | None = None


class Observation(BaseModel):
    project: str = Field(default="Rice",min_length=1,max_length=100)
    genotype: str = Field(min_length=1,max_length=120)
    trait: str = Field(min_length=1,max_length=120)
    value: str = Field(min_length=1,max_length=120)
    environment: str = Field(default="",max_length=120)
    notes: str = Field(default="",max_length=1000)


class Preferences(BaseModel):
    traits: list[dict]


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="GURUDEV.ai | Breeder Companion", version="0.3.0", docs_url="/api/docs", redoc_url=None)

    @contextmanager
    def database():
        conn = store.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.get("/")
    def home():
        return FileResponse(STATIC / "index.html", media_type="text/html")

    @app.get("/static/{asset_name}")
    def asset(asset_name: str):
        if asset_name not in {"app.js", "styles.css"}:
            raise HTTPException(404, "Asset not found")
        return FileResponse(STATIC / asset_name)

    @app.get("/api/status")
    def status(project: str = "Rice"):
        with database() as conn:
            tasks = store.list_tasks(conn, project)
            obs = store.list_observations(conn, project)
        return {"product":"GURUDEV.ai", "version":"0.3.0", "project":project,
                "open_tasks":sum(t["status"] == "open" for t in tasks),
                "observations":len(obs), "cloud_ai_configured":bool(os.getenv("OPENAI_API_KEY")),
                "modules": {"breeder_companion":"implemented", "field_book":"implemented",
                            "trial_qc":"implemented", "parent_explorer":"exploratory",
                            "gp_cli":"available separately", "gwas":"not integrated",
                            "r_diversity":"not integrated", "e_design":"not integrated",
                            "autonomous_code_repair":"not implemented", "evidence_breeding_campaign":"implemented, scientific validation pending"}}

    @app.post("/api/chat")
    def chat(data:ChatMessage):
        try:
            with database() as conn:
                return respond(data.text, data.project, conn, use_ai=data.use_ai)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/tasks")
    def tasks(project: str="Rice"):
        with database() as conn:
            return store.list_tasks(conn, project)

    @app.post("/api/tasks", status_code=201)
    def task_add(data:Task):
        with database() as conn:
            return store.add_task(conn, data.project, data.title.strip(), data.due_date.isoformat() if data.due_date else None)

    @app.post("/api/tasks/{task_id}/done")
    def task_done(task_id: str, project: str="Rice"):
        with database() as conn:
            if not store.set_done(conn,project,task_id):
                raise HTTPException(404,"Task not found in this project")
        return {"status":"done", "id":task_id}

    @app.get("/api/observations")
    def observations(project: str="Rice"):
        with database() as conn:
            return store.list_observations(conn,project)

    @app.post("/api/observations",status_code=201)
    def observation_add(data:Observation):
        with database() as conn:
            return store.add_observation(conn,data.project,data.genotype.strip(),data.trait.strip(),data.value.strip(),data.environment.strip(),data.notes.strip())

    @app.post("/api/parents/schema")
    async def parent_schema(file:UploadFile=File(...)):
        raw = await file.read(MAX_UPLOAD_BYTES+1)
        try:
            df,numeric = parse_parent_csv(raw)
            return {"traits":numeric,"parents":len(df),"columns":list(df.columns)}
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.post("/api/parents/rank")
    async def parent_rank(file:UploadFile=File(...), preferences: str=Form(...)):
        import json
        try:
            opts=json.loads(preferences)
            if not isinstance(opts,dict):raise ValueError("Preferences must be an object")
            return rank_parents(await file.read(MAX_UPLOAD_BYTES+1),opts.get("traits",[]))
        except (ValueError,TypeError) as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.post("/api/trial/qc")
    async def trial_qc(file:UploadFile=File(...)):
        try:
            return trial_quality(await file.read(MAX_UPLOAD_BYTES+1))
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.post("/api/gp/run")
    async def genomic_prediction_run(genotype:UploadFile=File(...), phenotype:UploadFile=File(...),
                                     trait:str=Form(...), group_column:str=Form("")):
        """Run the existing leakage-controlled GP baseline on small, user-provided CSVs.
        Every execution has an immutable manifest and creates a persistent local job record.
        """
        import tempfile
        from .validation import verified_gp_run
        if not trait or len(trait)>120 or len(group_column)>120:
            raise HTTPException(422,"Choose a valid trait and optional group column")
        raw_g = await genotype.read(MAX_UPLOAD_BYTES+1)
        raw_p = await phenotype.read(MAX_UPLOAD_BYTES+1)
        if len(raw_g)>MAX_UPLOAD_BYTES or len(raw_p)>MAX_UPLOAD_BYTES:
            raise HTTPException(422,"Each GP input CSV must be 5 MB or less")
        if not raw_g or not raw_p:
            raise HTTPException(422,"Genotype and phenotype files cannot be empty")
        output_root=Path(os.getenv("GURUDEV_RUNS", "./gurudev_runs")).resolve()
        with tempfile.TemporaryDirectory(prefix="gurudev_gp_") as temp:
            g=Path(temp)/"genotype.csv"
            p=Path(temp)/"phenotype.csv"
            g.write_bytes(raw_g)
            p.write_bytes(raw_p)
            try:
                result=verified_gp_run(str(g),str(p),trait.strip(),output_root,
                                       group_column=group_column.strip() or None)
                return result
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from exc
            except Exception as exc:
                # Reject unsafe server tracebacks in API responses.
                raise HTTPException(500,"GP computation failed; inspect the local job manifest and audit log") from exc

    @app.get("/api/gp/jobs")
    def gp_jobs():
        from gurudev_ai.jobs import recent_jobs
        output_root=Path(os.getenv("GURUDEV_RUNS", "./gurudev_runs")).resolve()
        result=recent_jobs(output_root,limit=20)
        return [{"id":x[0],"created":x[1],"status":x[2],"module":x[3],"trait":x[4]} for x in result]

    @app.get("/api/gp/jobs/{job_id}/report")
    def gp_report(job_id:str):
        import re
        output_root=Path(os.getenv("GURUDEV_RUNS", "./gurudev_runs")).resolve()
        if not re.fullmatch(r"[0-9a-f]{12}",job_id):
            raise HTTPException(404,"Job not found")
        p=output_root/job_id/"report.md"
        if not p.is_file():
            raise HTTPException(404,"Report not found")
        return FileResponse(p,media_type="text/markdown",filename=f"gurudev_gp_{job_id}.md")

    @app.post("/api/breeding/campaign")
    async def breeding_campaign(genotype:UploadFile=File(...), phenotype:UploadFile=File(...),
        trait:str=Form(...), group_column:str=Form(""), direction:str=Form("max")):
        from gurudev_ai.breeder_engine.workflow import run_campaign
        from gurudev_ai.breeder_engine.science import MAX_CSV_BYTES
        if len(trait)>120 or direction not in ("max","min") or len(group_column)>120:
            raise HTTPException(422,"Invalid parameter")
        genodata=await genotype.read(MAX_CSV_BYTES+1)
        phenodata=await phenotype.read(MAX_CSV_BYTES+1)
        if len(genodata)>MAX_CSV_BYTES or len(phenodata)>MAX_CSV_BYTES:
            raise HTTPException(413,"CSV upload exceeds campaign limit")
        try:
            # Local single-user synchronous execution only. Production needs queue + auth.
            record=run_campaign(genodata,phenodata,trait,
                os.getenv("GURUDEV_CAMPAIGNS","./gurudev_campaigns"),
                group=group_column.strip() or None, direction=direction)
            return {"job_id":record["job_id"],"status":record["status"],
                "qc":record["qc"],"evaluation":record["evaluation"],
                "scientific_checks":record["scientific_checks"],
                "report_url":f"/api/breeding/campaign/{record['job_id']}/report"}
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500,"Campaign failed; inspect the run's local audit log") from exc

    @app.post("/api/breeding/campaign/{job_id}/external-validate")
    async def breeding_external_validation(job_id:str, genotype:UploadFile=File(...),
                                           phenotype:UploadFile=File(...),trait:str=Form(...)):
        from gurudev_ai.breeder_engine.external import evaluate_external
        from gurudev_ai.breeder_engine.science import MAX_CSV_BYTES
        g=await genotype.read(MAX_CSV_BYTES+1)
        p=await phenotype.read(MAX_CSV_BYTES+1)
        if len(g)>MAX_CSV_BYTES or len(p)>MAX_CSV_BYTES:
            raise HTTPException(413,"External CSV file too large")
        try:
            result=evaluate_external(os.getenv("GURUDEV_CAMPAIGNS","./gurudev_campaigns"),
                                     job_id,g,p,trait)
            return result
        except FileNotFoundError:
            raise HTTPException(404,"Campaign not found")
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.get("/api/breeding/campaign/{job_id}")
    def breeding_campaign_status(job_id:str):
        from gurudev_ai.breeder_engine.workflow import get_campaign
        try:
            return get_campaign(os.getenv("GURUDEV_CAMPAIGNS","./gurudev_campaigns"),job_id)
        except (ValueError,FileNotFoundError):
            raise HTTPException(404,"Campaign not found")

    @app.get("/api/breeding/campaign/{job_id}/report")
    def breeding_campaign_report(job_id:str):
        from gurudev_ai.breeder_engine.workflow import _require_job
        try:
            folder=_require_job(os.getenv("GURUDEV_CAMPAIGNS","./gurudev_campaigns"),job_id)
        except (ValueError,FileNotFoundError):
            raise HTTPException(404,"Campaign not found")
        report=folder/"scientific_report.md"
        if not report.is_file():
            raise HTTPException(404,"Report unavailable")
        return FileResponse(report,media_type="text/markdown",filename=f"GURUDEV_campaign_{job_id}.md")

    return app


app = create_app()


def main():
    import uvicorn
    # Intentionally local-only by default: no authentication is provided in the prototype.
    uvicorn.run("gurudev_ai.companion.server:app",host="127.0.0.1",port=int(os.getenv("GURUDEV_PORT","8502")),reload=False)

if __name__ == "__main__":
    main()
