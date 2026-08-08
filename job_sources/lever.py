"""
Lever Postings API — free, public, no API key required.
Per-company only: you need the company's Lever site slug
(e.g. jobs.lever.co/netflix -> "netflix").
Docs: https://github.com/lever/postings-api
"""
import httpx

BASE_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"


async def list_company_jobs(company_slug: str, query: str = "", limit: int = 15) -> list[dict]:
    url = BASE_URL.format(slug=company_slug)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    query_lower = query.lower()
    jobs = []
    for j in data:
        title = j.get("text", "")
        if query_lower and query_lower not in title.lower():
            continue
        categories = j.get("categories", {})
        jobs.append({
            "job_id": f"lever_{company_slug}_{j.get('id')}",
            "source": "lever",
            "title": title,
            "company": company_slug,
            "location": categories.get("location"),
            "description": j.get("descriptionPlain", j.get("description", "")),
            "url": j.get("hostedUrl"),
            "salary": None,
            "posted_at": j.get("createdAt"),
        })
        if len(jobs) >= limit:
            break
    return jobs
