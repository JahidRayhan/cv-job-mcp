# CV & Job Application MCP Server

A local MCP server that lets Claude search jobs, pull job descriptions, and
help you tailor your CV — with **you** always doing the final "submit" click.

**100% free to run.** No paid API keys required. No hosting cost (runs on your
own machine). No separate LLM billing (Claude does the reasoning; this server
only fetches/stores data).

## What it does

- Parses your CV (PDF/DOCX/TXT/MD) into text Claude can read.
- Searches free job APIs: **Remotive** and **Arbeitnow** (no signup needed),
  plus **Adzuna** (free tier, optional signup) and any company's
  **Greenhouse**/**Lever** job board.
- Stores jobs, tailored CVs, and application status locally as JSON files in `./data/`.
- Assembles a ready-to-review application package with the real apply link —
  **it never submits anything for you.**

## 1. Install

```bash
cd cv-job-mcp
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. (Optional) Set up Adzuna

Remotive and Arbeitnow work immediately with zero configuration. If you also
want Adzuna:

1. Sign up free at https://developer.adzuna.com/ (free tier: 250 calls/month).
2. Copy `.env.example` to `.env` and fill in `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
3. Set `ADZUNA_COUNTRY` to your target country code (gb, us, in, etc).

If you skip this, `search_jobs` still works fine — it just quietly skips Adzuna.

## 3. Connect it to Claude Desktop

Open (or create) your Claude Desktop MCP config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add this server:

```json
{
  "mcpServers": {
    "cv-job-assistant": {
      "command": "/absolute/path/to/cv-job-mcp/venv/bin/python",
      "args": ["/absolute/path/to/cv-job-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop. You should see the tools appear when you start a new chat.

## 4. Typical usage in Claude

```
"Upload my CV from ~/Documents/resume.pdf"
"Search for backend engineer jobs, remote"
"Analyze job [job_id] against my CV and give me a fit score"
"Tailor my CV for job [job_id] and write a cover letter"
"Prepare the application package for job [job_id]"
```

Claude will do the parsing/analysis/tailoring reasoning itself (using the tools
for data), then call `save_tailored_application` and `prepare_application` to
package everything. You get a package with the direct apply URL — you open it
and click submit yourself.

## Available tools

| Tool | What it does |
|---|---|
| `upload_cv` | Extract text from a CV file, store it, return a `cv_id` |
| `list_cvs` | List stored CVs |
| `search_jobs` | Search Remotive + Arbeitnow + Adzuna by keyword |
| `search_company_jobs` | List jobs at one company via Greenhouse/Lever |
| `get_job` | Get full details of a saved job |
| `list_saved_jobs` | List all jobs saved from past searches |
| `save_tailored_application` | Save Claude-generated tailored CV + cover letter |
| `prepare_application` | Assemble final review package with apply URL |
| `update_application_status` | Track status (Submitted, Interview, Offer, etc.) |
| `list_applications` | See all tracked applications |

## Notes on cost & compliance

- **No paid services used.** Adzuna's free tier (250 calls/month) is the only
  optional signup, and everything works without it.
- **LinkedIn is intentionally excluded** — LinkedIn's job data API requires a
  paid partner agreement (~$900+/month), and scraping violates its Terms of
  Service. If you find a LinkedIn job manually, you can still ask Claude to
  analyze/tailor for it — just paste the job description in chat.
- **Nothing auto-submits.** `prepare_application` only assembles a package and
  returns the real apply URL. You always do the final click.

## Automatic overnight search (no Claude, no LLM cost)

`daily_job_check.py` is a standalone script — it doesn't use Claude or any
MCP tooling. It just calls the same free job-source modules directly, saves
results to the shared `./data/` storage (so Claude can look them up later in
chat), and logs anything **new** since the last run to `./logs/`.

### 1. Configure your search terms

In your `.env` file, set:

```
SEARCH_QUERIES=backend developer,python engineer
SEARCH_LOCATION=
SEARCH_LIMIT_PER_SOURCE=15
```

`SEARCH_QUERIES` is comma-separated — add as many terms as you want checked
each run.

### 2. Test it manually first

```bash
cd /path/to/cv-job-mcp
./venv/bin/python daily_job_check.py
```

You should see a summary printed, and a new file appear under `./logs/`
(e.g. `logs/2026-08-08.log`). Run it a second time immediately — it should
report 0 new jobs, since it remembers what it's already seen
(`data/seen_job_ids.json`).

### 3. Schedule it with cron

Open your crontab:

```bash
crontab -e
```

Add a line to run it every night at 2 AM (adjust the path and time as needed):

```
0 2 * * * /home/jahid/Downloads/cv-job-mcp/venv/bin/python /home/jahid/Downloads/cv-job-mcp/daily_job_check.py >> /home/jahid/Downloads/cv-job-mcp/logs/cron.log 2>&1
```

Save and exit. Cron will now run the search every night, log new postings to
`./logs/`, and (if your desktop is on and `notify-send` is available) pop up
a desktop notification when new jobs are found.

### 4. Review results the next day

Either:
- Open the day's log file directly: `cat logs/2026-08-08.log`, or
- Open Claude Desktop and ask: **"List all jobs saved so far"** or
  **"Show me the newest saved jobs and check them against my CV"** — since
  the script saves everything to the same storage the MCP server reads from,
  Claude can pick up right where the overnight run left off.

This path costs nothing extra — no LLM calls happen until you actually open
a chat and ask Claude to look at the results.

## Extending it

- Add more free sources (e.g. RemoteOK, USAJobs, other companies' Greenhouse/Lever
  boards) by adding a new file under `job_sources/` following the same pattern
  as `remotive.py`.
