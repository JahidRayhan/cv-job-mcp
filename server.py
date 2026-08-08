"""
CV & Job Application MCP Server.

Design principle: this server only fetches/stores/parses DATA.
All reasoning (analysis, fit scoring, CV tailoring, cover letter writing)
is done by Claude itself in conversation, using the data these tools return.
This avoids any second, separate paid LLM API call.

Run with: python server.py
Configure in Claude Desktop's claude_desktop_config.json as a stdio MCP server
(see README.md for the exact config snippet).
"""
import asyncio
import json
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

import storage
import cv_parser
from job_sources import remotive, arbeitnow, adzuna, greenhouse, lever

load_dotenv()

mcp = FastMCP("cv-job-assistant")


@mcp.tool()
def upload_cv(file_path: str) -> str:
    """Parse a CV/resume file (PDF, DOCX, TXT, or MD) from a local file path
    and store its extracted text for later use. Returns a cv_id."""
    text = cv_parser.extract_text(file_path)
    cv_id = storage.save_cv(text, file_path)
    return f"CV stored as {cv_id}.\n\nExtracted text:\n{text}"


@mcp.tool()
def list_cvs() -> str:
    """List previously uploaded CVs with their cv_id and filename."""
    cvs = storage.list_cvs()
    summary = "\n".join(f"- {c['cv_id']}: {c['source_filename']} ({c['created_at']})" for c in cvs)
    return summary or "No CVs uploaded yet."


@mcp.tool()
async def search_jobs(query: str, location: str = "", limit_per_source: int = 10) -> str:
    """Search for job postings across free sources (Remotive, Arbeitnow, and Adzuna
    if configured). Returns raw job postings for Claude to analyze against a CV.
    Location is optional and mainly used by Adzuna."""
    results = await asyncio.gather(
        remotive.search(query, limit=limit_per_source),
        arbeitnow.search(query, limit=limit_per_source),
        adzuna.search(query, location=location, limit=limit_per_source),
        return_exceptions=True,
    )

    all_jobs = []
    errors = []
    for source_name, r in zip(["remotive", "arbeitnow", "adzuna"], results):
        if isinstance(r, Exception):
            errors.append(f"{source_name}: {r}")
        else:
            all_jobs.extend(r)

    for job in all_jobs:
        storage.save_job(job)

    lines = [f"Found {len(all_jobs)} jobs:"]
    for j in all_jobs:
        lines.append(f"- [{j['job_id']}] {j['title']} @ {j['company']} ({j['location']}) — {j['url']}")
    if errors:
        lines.append("\nSource errors (non-fatal, e.g. Adzuna not configured):")
        lines.extend(f"- {e}" for e in errors)
    return "\n".join(lines)


@mcp.tool()
async def search_company_jobs(provider: str, company_token: str, query: str = "") -> str:
    """List open jobs at a specific company via its Greenhouse or Lever job board
    (free, public, no key needed). provider must be 'greenhouse' or 'lever'.
    company_token is the board token/company slug, usually visible in the company's
    careers page URL (e.g. boards.greenhouse.io/COMPANY or jobs.lever.co/COMPANY)."""
    if provider not in ("greenhouse", "lever"):
        return "provider must be 'greenhouse' or 'lever'"
    fn = greenhouse.list_company_jobs if provider == "greenhouse" else lever.list_company_jobs
    jobs = await fn(company_token, query)
    for job in jobs:
        storage.save_job(job)
    lines = [f"Found {len(jobs)} jobs at {company_token} ({provider}):"]
    for j in jobs:
        lines.append(f"- [{j['job_id']}] {j['title']} ({j['location']}) — {j['url']}")
    return "\n".join(lines)


@mcp.tool()
def get_job(job_id: str) -> str:
    """Retrieve full stored details (including description) for a previously
    searched/saved job by job_id."""
    job = storage.get_job(job_id)
    if not job:
        return "Job not found."
    return json.dumps(job, indent=2)


@mcp.tool()
def list_saved_jobs() -> str:
    """List all jobs saved so far from prior searches."""
    jobs = storage.list_jobs()
    lines = [f"- [{j['job_id']}] {j['title']} @ {j['company']}" for j in jobs]
    return "\n".join(lines) or "No jobs saved yet."


@mcp.tool()
def save_tailored_application(cv_id: str, job_id: str, tailored_cv_text: str, cover_letter_text: str) -> str:
    """Save a tailored CV and cover letter (already written by Claude in conversation)
    for a given cv_id + job_id pair. Returns a tailored_id. Call this after Claude has
    generated the tailored text conversationally — this tool does not do any writing itself."""
    tailored_id = storage.save_tailored(cv_id, job_id, tailored_cv_text, cover_letter_text)
    storage.upsert_application(job_id, "Prepared", notes="Tailored CV generated")
    return f"Tailored application saved as {tailored_id}."


@mcp.tool()
def prepare_application(job_id: str, tailored_id: str) -> str:
    """Assemble the final application package for the user to review: tailored CV,
    cover letter, and the direct apply URL. The user must open the URL and submit
    manually — this tool NEVER submits anything automatically."""
    job = storage.get_job(job_id)
    tailored = storage.get_tailored(tailored_id)
    if not job or not tailored:
        return "Job or tailored application not found."
    package = (
        f"APPLICATION PACKAGE\n"
        f"====================\n"
        f"Job: {job['title']} @ {job['company']}\n"
        f"Apply URL (open this and submit manually): {job['url']}\n\n"
        f"--- TAILORED CV ---\n{tailored['tailored_cv_text']}\n\n"
        f"--- COVER LETTER ---\n{tailored['cover_letter_text']}\n\n"
        f"NOTE: This tool does not submit anything. Review the package, "
        f"open the apply URL above, and submit it yourself."
    )
    storage.upsert_application(job_id, "Prepared", notes="Package ready for review")
    return package


@mcp.tool()
def update_application_status(job_id: str, status: str, notes: str = "") -> str:
    """Record/update the status of an application after the user has manually
    submitted it or heard back. status must be one of: Prepared, Submitted,
    Interview, Rejected, Offer, Withdrawn."""
    valid = {"Prepared", "Submitted", "Interview", "Rejected", "Offer", "Withdrawn"}
    if status not in valid:
        return f"status must be one of {sorted(valid)}"
    record = storage.upsert_application(job_id, status, notes)
    return f"Status updated: {record['status']}"


@mcp.tool()
def list_applications() -> str:
    """List all tracked applications and their current status."""
    apps = storage.list_applications()
    lines = [f"- {a['job_id']}: {a['status']} (updated {a['updated_at']})" for a in apps]
    return "\n".join(lines) or "No applications tracked yet."


if __name__ == "__main__":
    mcp.run()
