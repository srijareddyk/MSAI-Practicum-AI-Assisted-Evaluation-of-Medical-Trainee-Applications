"""FastAPI server for the residency application screening UI."""

from __future__ import annotations

import json
import os
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

from llm_score.llm_client import DEFAULT_MODEL, LLM_PROVIDER
from llm_score.usage import estimate_usd_for, pricing_catalog

# Import the scoring pipeline only when a job starts. Loading openpyxl/pypdf at
# import time can hang for minutes if the project lives on iCloud Desktop.
ROOT = Path(__file__).resolve().parent.parent
UPLOAD_ROOT = ROOT / "api_data" / "jobs"
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(
    title="Northwestern Ophthalmology Application Screening",
    description="AI-assisted evaluation of medical trainee applications",
    version="1.0.0",
)

def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
        ]
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (local practicum use)
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_public(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "status": job["status"],
        "stage": job.get("stage"),
        "progress": job.get("progress") or {},
        "mode": job.get("mode"),
        "model": job.get("model"),
        "files": job.get("files") or [],
        "applicants": job.get("applicants") or [],
        "excel_name": job.get("excel_name"),
        "llm_usage": job.get("llm_usage"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


def _persist_job(job: dict[str, Any]) -> None:
    job_dir = Path(job["job_dir"])
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(
        json.dumps(job, indent=2, default=str),
        encoding="utf-8",
    )


def _scan_disk_jobs() -> list[dict[str, Any]]:
    if not UPLOAD_ROOT.is_dir():
        return []
    found: list[dict[str, Any]] = []
    for folder in sorted(UPLOAD_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not folder.is_dir():
            continue
        meta = folder / "job.json"
        if meta.is_file():
            try:
                found.append(json.loads(meta.read_text(encoding="utf-8")))
                continue
            except json.JSONDecodeError:
                pass
        uploads = list((folder / "uploads").glob("*.pdf")) if (folder / "uploads").is_dir() else []
        if not uploads and not (folder / "output").exists():
            continue
        found.append(
            {
                "id": folder.name,
                "status": "completed" if (folder / "output").exists() else "unknown",
                "stage": "complete",
                "progress": {},
                "mode": "full",
                "model": DEFAULT_MODEL,
                "files": [p.name for p in uploads],
                "applicants": [],
                "excel_name": "screening_scores.xlsx" if (folder / "output" / "screening_scores.xlsx").is_file() else None,
                "llm_usage": None,
                "error": None,
                "created_at": datetime.fromtimestamp(folder.stat().st_mtime, tz=timezone.utc).isoformat(),
                "updated_at": datetime.fromtimestamp(folder.stat().st_mtime, tz=timezone.utc).isoformat(),
                "job_dir": str(folder),
            }
        )
    return found


def _job_dir_for(job_id: str) -> Path | None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            return Path(job["job_dir"])
    disk = UPLOAD_ROOT / job_id
    if disk.is_dir():
        return disk
    return None


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


def _check_azure(model: str) -> dict[str, Any]:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    if not endpoint or not key:
        return {
            "ok": False,
            "available": False,
            "error": "Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY",
            "requested": model,
        }
    return {"ok": True, "available": True, "requested": model, "endpoint": endpoint}


def _check_llm(model: str) -> dict[str, Any]:
    if LLM_PROVIDER == "azure":
        status = _check_azure(model)
    else:
        status = _check_ollama(model)
    status["provider"] = LLM_PROVIDER
    return status


@app.get("/api/health")
def health() -> dict[str, Any]:
    template = ROOT / "rubric" / "template.xlsx"
    llm_status = _check_llm(DEFAULT_MODEL)
    return {
        "status": "ok",
        "template_present": template.is_file(),
        "default_model": DEFAULT_MODEL,
        "llm": llm_status,
        "ollama": llm_status,
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
        from api.pipeline import run_pipeline

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
            llm_usage=result.llm_usage,
            error=None,
        )
        with _lock:
            job = _jobs.get(job_id)
            if job:
                _persist_job(job)
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
            "llm_usage": None,
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
        if job:
            return _job_public(job)
    disk = UPLOAD_ROOT / job_id / "job.json"
    if disk.is_file():
        try:
            return _job_public(json.loads(disk.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    raise HTTPException(404, "Job not found")


@app.get("/api/jobs/{job_id}/excel")
def download_excel(job_id: str) -> FileResponse:
    job_dir = _job_dir_for(job_id)
    if job_dir is None:
        raise HTTPException(404, "Job not found")
    excel_name = "screening_scores.xlsx"
    with _lock:
        job = _jobs.get(job_id)
        if job:
            if job["status"] != "completed":
                raise HTTPException(400, "Job not completed")
            excel_name = job.get("excel_name") or excel_name
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
    job_dir = _job_dir_for(job_id)
    if job_dir is None:
        raise HTTPException(404, "Job not found")
    path = job_dir / "output" / "briefings" / safe
    if not path.is_file():
        raise HTTPException(404, "Markdown file not found")
    return FileResponse(path, filename=safe, media_type="text/markdown")


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, str]:
    with _lock:
        job = _jobs.pop(job_id, None)
    job_dir = Path(job["job_dir"]) if job else UPLOAD_ROOT / job_id
    if not job and not job_dir.exists():
        raise HTTPException(404, "Job not found")
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    return {"status": "deleted"}


@app.get("/api/developer/overview")
def developer_overview() -> dict[str, Any]:
    in_mem: dict[str, dict[str, Any]] = {}
    with _lock:
        in_mem = {job_id: job for job_id, job in _jobs.items()}
    merged: dict[str, dict[str, Any]] = {}
    for job in _scan_disk_jobs():
        merged[job["id"]] = job
    merged.update(in_mem)
    jobs = [_job_public(j) for j in merged.values()]
    jobs.sort(key=lambda j: j.get("updated_at") or j.get("created_at") or "", reverse=True)
    total_usd = 0.0
    total_tokens = 0
    total_calls = 0
    for job in jobs:
        usage = job.get("llm_usage") or {}
        total_usd += float(usage.get("estimated_usd") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
        total_calls += int(usage.get("calls") or 0)
    in_rate, out_rate = 0.40, 1.60
    for row in pricing_catalog():
        if row["model"] == (DEFAULT_MODEL or "gpt-4.1-mini"):
            in_rate, out_rate = row["input_usd_per_million"], row["output_usd_per_million"]
            break
    return {
        "provider": LLM_PROVIDER,
        "default_model": DEFAULT_MODEL,
        "pricing": pricing_catalog(),
        "formula": (
            "estimated_usd = (input_tokens / 1,000,000) × input_rate "
            "+ (output_tokens / 1,000,000) × output_rate"
        ),
        "example": {
            "model": DEFAULT_MODEL,
            "input_tokens": 19189,
            "output_tokens": 2322,
            "input_rate": in_rate,
            "output_rate": out_rate,
            "estimated_usd": round(estimate_usd_for(19189, 2322, DEFAULT_MODEL), 6),
            "note": "Actual Azure metrics from the first gpt-4.1-mini complete review on this account.",
        },
        "totals": {
            "jobs": len(jobs),
            "calls": total_calls,
            "tokens": total_tokens,
            "estimated_usd": round(total_usd, 6),
        },
        "jobs": jobs,
    }


@app.post("/api/developer/preview")
async def developer_preview(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(400, "Upload at least one PDF")
    from api.cloud_payload import cloud_payload_from_pdf

    payloads: list[dict[str, Any]] = []
    tmp = UPLOAD_ROOT / "_preview" / uuid.uuid4().hex[:10]
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        for upload in files:
            if not (upload.filename or "").lower().endswith(".pdf"):
                raise HTTPException(400, f"Only PDF files are accepted ({upload.filename})")
            dest = tmp / Path(upload.filename or "application.pdf").name
            dest.write_bytes(await upload.read())
            payloads.append(cloud_payload_from_pdf(dest))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"payloads": payloads, "sent_to_azure": False}


@app.get("/api/jobs/{job_id}/redacted")
def job_redacted(job_id: str) -> dict[str, Any]:
    job_dir = _job_dir_for(job_id)
    if job_dir is None:
        raise HTTPException(404, "Job not found")
    from api.cloud_payload import cloud_payload_from_pdf, placeholder_counts

    payloads: list[dict[str, Any]] = []
    redacted_dir = job_dir / "output" / "redacted_for_azure"
    uploads = job_dir / "uploads"
    saved = {p.stem: p for p in redacted_dir.glob("*.txt")} if redacted_dir.is_dir() else {}
    pdfs = list(uploads.glob("*.pdf")) if uploads.is_dir() else []

    def from_text(name: str, text: str) -> dict[str, Any]:
        return {
            "file": name,
            "kept_on_this_computer": {"applicant_name": None, "source_chars": None},
            "sent_to_azure": text,
            "azure_chars": len(text),
            "redaction_notes": [],
            "placeholder_counts": placeholder_counts(text),
        }

    if pdfs:
        for pdf in pdfs:
            saved_txt = saved.get(pdf.stem)
            if saved_txt:
                payloads.append(from_text(pdf.name, saved_txt.read_text(encoding="utf-8")))
            else:
                payloads.append(cloud_payload_from_pdf(pdf))
    elif saved:
        for path in saved.values():
            payloads.append(from_text(path.name, path.read_text(encoding="utf-8")))
    if not payloads:
        raise HTTPException(404, "No redacted payload for this job")
    return {"job_id": job_id, "payloads": payloads}


@app.get("/developer")
@app.get("/developer/")
def developer_spa() -> FileResponse:
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(404, "Frontend is not built")
    return FileResponse(index, media_type="text/html")


# Serve built frontend in production
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
