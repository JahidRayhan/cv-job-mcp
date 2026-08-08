"""
Simple local JSON file storage. No database, no cloud service, no cost.
All data lives under ./data/ as JSON files.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent / "data"
CV_DIR = DATA_DIR / "cvs"
JOB_DIR = DATA_DIR / "jobs"
APP_DIR = DATA_DIR / "applications"
TAILORED_DIR = DATA_DIR / "tailored"

for d in (CV_DIR, JOB_DIR, APP_DIR, TAILORED_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def save_cv(parsed_text: str, source_filename: str) -> str:
    cv_id = _new_id("cv")
    record = {
        "cv_id": cv_id,
        "source_filename": source_filename,
        "text": parsed_text,
        "created_at": _now(),
    }
    (CV_DIR / f"{cv_id}.json").write_text(json.dumps(record, indent=2))
    return cv_id


def get_cv(cv_id: str) -> dict | None:
    path = CV_DIR / f"{cv_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_cvs() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(CV_DIR.glob("*.json"))]


def save_job(job: dict) -> str:
    """job should already contain title/company/location/description/url/source.
    Returns a stable job_id derived from source+external id when possible."""
    job_id = job.get("job_id") or _new_id("job")
    job["job_id"] = job_id
    job["saved_at"] = _now()
    (JOB_DIR / f"{job_id}.json").write_text(json.dumps(job, indent=2))
    return job_id


def get_job(job_id: str) -> dict | None:
    path = JOB_DIR / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_jobs() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(JOB_DIR.glob("*.json"), reverse=True)]


def save_tailored(cv_id: str, job_id: str, tailored_cv_text: str, cover_letter_text: str) -> str:
    tailored_id = _new_id("tlr")
    record = {
        "tailored_id": tailored_id,
        "cv_id": cv_id,
        "job_id": job_id,
        "tailored_cv_text": tailored_cv_text,
        "cover_letter_text": cover_letter_text,
        "created_at": _now(),
    }
    (TAILORED_DIR / f"{tailored_id}.json").write_text(json.dumps(record, indent=2))
    return tailored_id


def get_tailored(tailored_id: str) -> dict | None:
    path = TAILORED_DIR / f"{tailored_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def upsert_application(job_id: str, status: str, notes: str = "") -> dict:
    path = APP_DIR / f"{job_id}.json"
    record = json.loads(path.read_text()) if path.exists() else {
        "job_id": job_id,
        "history": [],
    }
    record["status"] = status
    record["updated_at"] = _now()
    record["history"].append({"status": status, "notes": notes, "at": _now()})
    path.write_text(json.dumps(record, indent=2))
    return record


def list_applications() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(APP_DIR.glob("*.json"), reverse=True)]
