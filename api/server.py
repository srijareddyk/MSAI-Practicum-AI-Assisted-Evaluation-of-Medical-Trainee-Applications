"""FastAPI server for the residency application screening UI."""

from __future__ import annotations

import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.pipeline import project_root, run_pipeline
from llm_score.llm_client import DEFAULT_MODEL

ROOT = project_root()
UPLOAD_ROOT = ROOT / "api_data" / "jobs"
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(
    title="Northwestern Ophthalmology Application Screening",
    description="AI-assisted evaluation of medical trainee applications",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (local practicum use)
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_job(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = _now()


def _check_ollama(model: str) -> dict[str, Any]:
    try:
        import ollama

        models = ollama.list()
        names: list[str] = []
        for m in models.get("models", []):
            name = m.get("model") or m.get("name") or ""
            if name:
                names.append(name)
        available = any(model in n or n.startswith(f"{model}:") or n == model for n in names)
        return {"ok": True, "available": available, "models": names, "requested": model}
    except Exception as exc:  # noqa: BLE001 — surface status to UI
        return {"ok": False, "available": False, "error": str(exc), "requested": model}


@app.get("/api/health")
def health() -> dict[str, Any]:
    template = ROOT / "rubric" / "template.xlsx"
    ollama_status = _check_ollama(DEFAULT_MODEL)
    return {
        "status": "ok",
        "template_present": template.is_file(),
        "default_model": DEFAULT_MODEL,
        "ollama": ollama_status,
    }


def _run_job(
    job_id: str,
    pdf_paths: list[Path],
    job_dir: Path,
    model: str,
    mode: str,
) -> None:
    skip_llm = mode == "step1"
    skip_agents = mode == "briefing"

    def on_progress(stage: str, extra: dict[str, Any]) -> None:
        _update_job(job_id, stage=stage, progress=extra)

    try:
        result = run_pipeline(
            pdf_paths,
            output_dir=job_dir / "output",
            model=model,
            skip_llm=skip_llm,
            skip_agents=skip_agents,
            on_progress=on_progress,
        )
        _update_job(
            job_id,
            status="completed",
            stage="complete",
            applicants=result.applicants,
            excel_name=result.excel_path.name,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        _update_job(job_id, status="failed", stage="error", error=str(exc))


@app.post("/api/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    mode: str = Form("full"),
    model: str = Form(DEFAULT_MODEL),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(400, "Upload at least one PDF")
    if mode not in {"full", "briefing", "step1"}:
        raise HTTPException(400, "mode must be full, briefing, or step1")

    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"Only PDF files are accepted ({f.filename})")

    job_id = uuid.uuid4().hex[:12]
    job_dir = UPLOAD_ROOT / job_id
    uploads_dir = job_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths: list[Path] = []
    saved_names: list[str] = []
    for upload in files:
        name = Path(upload.filename or "application.pdf").name
        dest = uploads_dir / name
        # Avoid collisions
        if dest.exists():
            dest = uploads_dir / f"{dest.stem}_{uuid.uuid4().hex[:6]}{dest.suffix}"
        content = await upload.read()
        dest.write_bytes(content)
        pdf_paths.append(dest)
        saved_names.append(dest.name)

    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "stage": "queued",
            "progress": {},
            "mode": mode,
            "model": model,
            "files": saved_names,
            "applicants": [],
            "excel_name": None,
            "error": None,
            "created_at": _now(),
            "updated_at": _now(),
            "job_dir": str(job_dir),
        }

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, pdf_paths, job_dir, model, mode),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "running", "files": saved_names}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        # Don't expose filesystem paths to the client
        return {
            "id": job["id"],
            "status": job["status"],
            "stage": job["stage"],
            "progress": job["progress"],
            "mode": job["mode"],
            "model": job["model"],
            "files": job["files"],
            "applicants": job["applicants"],
            "excel_name": job["excel_name"],
            "error": job["error"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        }


@app.get("/api/jobs/{job_id}/excel")
def download_excel(job_id: str) -> FileResponse:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if job["status"] != "completed":
            raise HTTPException(400, "Job not completed")
        job_dir = Path(job["job_dir"])
        excel_name = job["excel_name"] or "screening_scores.xlsx"
    path = job_dir / "output" / excel_name
    if not path.is_file():
        raise HTTPException(404, "Excel file not found")
    return FileResponse(
        path,
        filename=excel_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/jobs/{job_id}/markdown/{filename}")
def download_markdown(job_id: str, filename: str) -> FileResponse:
    safe = Path(filename).name
    if not safe.endswith(".md") or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        job_dir = Path(job["job_dir"])
    path = job_dir / "output" / "briefings" / safe
    if not path.is_file():
        raise HTTPException(404, "Markdown file not found")
    return FileResponse(path, filename=safe, media_type="text/markdown")


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, str]:
    with _lock:
        job = _jobs.pop(job_id, None)
    if not job:
        raise HTTPException(404, "Job not found")
    job_dir = Path(job["job_dir"])
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    return {"status": "deleted"}


# Serve built frontend in production
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
