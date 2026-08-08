"""
Arbeitnow API — fully free, no API key required.
Docs: https://www.arbeitnow.com/api/job-board-api
"""
import httpx

BASE_URL = "https://www.arbeitnow.com/api/job-board-api"


async def search(query: str, limit: int = 15) -> list[dict]:
    jobs = []
    query_lower = query.lower()
    async with httpx.AsyncClient(timeout=15) as client:
        # Arbeitnow has no server-side text search param; page through and filter client-side.
        page = 1
        while len(jobs) < limit and page <= 3:
            resp = await client.get(BASE_URL, params={"page": page})
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", [])
            if not results:
                break
            for j in results:
                title = j.get("title", "")
                tags = " ".join(j.get("tags", []))
                haystack = f"{title} {tags}".lower()
                if query_lower in haystack:
                    jobs.append({
                        "job_id": f"arbeitnow_{j.get('slug')}",
                        "source": "arbeitnow",
                        "title": title,
                        "company": j.get("company_name"),
                        "location": j.get("location") or ("Remote" if j.get("remote") else ""),
                        "description": j.get("description", ""),
                        "url": j.get("url"),
                        "salary": None,
                        "posted_at": j.get("created_at"),
                    })
                if len(jobs) >= limit:
                    break
            page += 1
    return jobs
