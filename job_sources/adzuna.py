"""
Adzuna API — free tier (250 calls/month as of this writing).
Sign up for a free App ID + App Key at: https://developer.adzuna.com/
Set ADZUNA_APP_ID and ADZUNA_APP_KEY in your .env file.
Docs: https://developer.adzuna.com/docs/search
"""
import os
import httpx

# Adzuna country code, e.g. "gb", "us", "in". Defaults to "gb" if unset.
COUNTRY = os.getenv("ADZUNA_COUNTRY", "gb")
BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1"


async def search(query: str, location: str = "", limit: int = 15) -> list[dict]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        # Not configured — skip silently so the server still works with free
        # no-key sources (Remotive, Arbeitnow) even without Adzuna set up.
        return []

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": limit,
        "what": query,
    }
    if location:
        params["where"] = location

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    jobs = []
    for j in data.get("results", [])[:limit]:
        jobs.append({
            "job_id": f"adzuna_{j.get('id')}",
            "source": "adzuna",
            "title": j.get("title"),
            "company": (j.get("company") or {}).get("display_name"),
            "location": (j.get("location") or {}).get("display_name"),
            "description": j.get("description", ""),
            "url": j.get("redirect_url"),
            "salary": _salary_str(j),
            "posted_at": j.get("created"),
        })
    return jobs


def _salary_str(j: dict) -> str | None:
    lo, hi = j.get("salary_min"), j.get("salary_max")
    if lo and hi:
        return f"{lo:.0f}-{hi:.0f}"
    return None
