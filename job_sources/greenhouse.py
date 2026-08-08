"""
Greenhouse Job Board API — free, public, no API key required.
Per-company only: you need the company's Greenhouse "board token"
(usually the slug in their careers page URL, e.g. boards.greenhouse.io/stripe -> "stripe").
Docs: https://developers.greenhouse.io/job-board.html
"""
import httpx

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


async def list_company_jobs(board_token: str, query: str = "", limit: int = 15) -> list[dict]:
    url = BASE_URL.format(token=board_token) + "?content=true"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    query_lower = query.lower()
    jobs = []
    for j in data.get("jobs", []):
        title = j.get("title", "")
        if query_lower and query_lower not in title.lower():
            continue
        jobs.append({
            "job_id": f"greenhouse_{board_token}_{j.get('id')}",
            "source": "greenhouse",
            "title": title,
            "company": board_token,
            "location": (j.get("location") or {}).get("name"),
            "description": j.get("content", ""),
            "url": j.get("absolute_url"),
            "salary": None,
            "posted_at": j.get("updated_at"),
        })
        if len(jobs) >= limit:
            break
    return jobs
