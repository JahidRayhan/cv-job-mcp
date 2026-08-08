"""
Remotive API — fully free, no API key required.
Docs: https://remotive.com/api-documentation
"""
import httpx

BASE_URL = "https://remotive.com/api/remote-jobs"


async def search(query: str, limit: int = 15) -> list[dict]:
    params = {"search": query, "limit": limit}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    jobs = []
    for j in data.get("jobs", [])[:limit]:
        jobs.append({
            "job_id": f"remotive_{j['id']}",
            "source": "remotive",
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("candidate_required_location", "Remote"),
            "description": j.get("description", ""),
            "url": j.get("url"),
            "salary": j.get("salary") or None,
            "posted_at": j.get("publication_date"),
        })
    return jobs
