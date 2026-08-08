"""
Standalone job search runner for cron scheduling.

Does NOT use Claude or any LLM — it just calls the same free job-source
modules the MCP server uses, saves results to the shared local storage,
and writes a plain-text log of anything NEW since the last run.

Configure your search terms via SEARCH_QUERIES in .env (comma-separated).
Run manually to test:
    ./venv/bin/python daily_job_check.py

Then schedule it with cron (see README.md "Automatic overnight search" section).
"""
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import storage
from job_sources import remotive, arbeitnow, adzuna

load_dotenv()

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
SEEN_FILE = BASE_DIR / "data" / "seen_job_ids.json"
LOG_DIR.mkdir(exist_ok=True)

# Comma-separated search terms, e.g. "backend developer,python engineer"
QUERIES = [q.strip() for q in os.getenv("SEARCH_QUERIES", "").split(",") if q.strip()]
LOCATION = os.getenv("SEARCH_LOCATION", "")
LIMIT_PER_SOURCE = int(os.getenv("SEARCH_LIMIT_PER_SOURCE", "15"))


def _load_seen_ids() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def _save_seen_ids(ids: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(ids)))


def _notify(title: str, message: str) -> None:
    """Best-effort desktop notification. Silently does nothing if notify-send
    isn't available (e.g. running headless via cron with no display)."""
    try:
        subprocess.run(
            ["notify-send", title, message],
            check=False,
            timeout=5,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
        )
    except Exception:
        pass


async def run_search_for_query(query: str) -> list[dict]:
    results = await asyncio.gather(
        remotive.search(query, limit=LIMIT_PER_SOURCE),
        arbeitnow.search(query, limit=LIMIT_PER_SOURCE),
        adzuna.search(query, location=LOCATION, limit=LIMIT_PER_SOURCE),
        return_exceptions=True,
    )
    jobs = []
    for r in results:
        if isinstance(r, Exception):
            continue
        jobs.extend(r)
    return jobs


async def main() -> None:
    if not QUERIES:
        print("No SEARCH_QUERIES configured in .env — nothing to search. "
              "Set e.g. SEARCH_QUERIES=backend developer,python engineer")
        return

    seen_ids = _load_seen_ids()
    all_jobs = []
    for query in QUERIES:
        jobs = await run_search_for_query(query)
        all_jobs.extend(jobs)

    # De-dupe by job_id across queries
    unique_jobs = {j["job_id"]: j for j in all_jobs}.values()

    new_jobs = [j for j in unique_jobs if j["job_id"] not in seen_ids]

    # Save everything (new and previously-seen) to the shared storage
    # so Claude can look them up by job_id later in a normal chat.
    for job in unique_jobs:
        storage.save_job(job)

    # Update the seen set
    seen_ids |= {j["job_id"] for j in unique_jobs}
    _save_seen_ids(seen_ids)

    # Write today's log
    timestamp = datetime.now(timezone.utc).isoformat()
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    lines = [f"=== Job search run at {timestamp} ===",
              f"Queries: {', '.join(QUERIES)}",
              f"Total jobs seen this run: {len(unique_jobs)}",
              f"NEW jobs since last run: {len(new_jobs)}",
              ""]
    if new_jobs:
        lines.append("--- NEW JOBS ---")
        for j in new_jobs:
            lines.append(f"[{j['job_id']}] {j['title']} @ {j['company']} ({j['location']})")
            lines.append(f"    {j['url']}")
        lines.append("")

    log_text = "\n".join(lines)
    with open(log_file, "a") as f:
        f.write(log_text + "\n")

    print(log_text)

    if new_jobs:
        _notify(
            "New job postings found",
            f"{len(new_jobs)} new job(s) matching your search. See {log_file}",
        )


if __name__ == "__main__":
    asyncio.run(main())
