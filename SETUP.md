# JobPulse — setup from the shared zip

Everything you need to run this on your own machine. Takes about five minutes.

> **There are no API keys in this zip.** Credentials were deliberately left
> out. The app runs fully without any — see [Optional: add API keys](#optional-add-api-keys)
> if you want the extras.

---

## Option A — Docker (recommended)

The only prerequisite is **Docker Desktop** (<https://docker.com/products/docker-desktop>).
Make sure it's actually running — the whale icon in your system tray should be
steady, not animating.

```bash
# 1. Unzip, then open a terminal in the project folder
cd job-pulse-auto-apply

# 2. Create your config from the template
cp .env.example .env          # Windows PowerShell: copy .env.example .env

# 3. Build and start everything
docker compose up -d --build
```

First build takes 3–5 minutes. When it finishes:

- **App:** <http://localhost:8080>
- **API docs:** <http://localhost:8000/docs>

Check all three containers are healthy:

```bash
docker compose ps
```

You want `healthy` next to `job-pulse-backend`, `job-pulse-frontend` and
`job-pulse-postgres`. The frontend waits for the backend on purpose, so if you
open the page the moment you hit enter you may briefly see it still starting.

To stop: `docker compose down`. To wipe the database too: `docker compose down -v`.

---

## Option B — run it directly (no Docker)

Needs **Node 20+** and **Python 3.11+**.

```bash
# ---- Backend ----
cd backend
python -m venv .venv

# activate it
source .venv/Scripts/activate     # Git Bash on Windows
# .venv\Scripts\activate          # PowerShell
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
cp .env.example .env              # defaults to SQLite — no database server needed
alembic upgrade head              # create the tables
uvicorn app.main:app --reload --port 8000
```

Then in a **second terminal**:

```bash
# ---- Frontend ----
npm install
npm run dev
```

Open <http://localhost:5173>.

---

## First run: what to do in the app

1. **Resumes tab → Upload PDF.** Nothing is scored until a resume exists — the
   app will tell you so rather than inventing a match score.
2. **Jobs tab → Search.** Try `DevOps Engineer` with location `Bangalore`.
   Results come live from Indian company career boards plus Remotive.
3. **Loops tab → New loop.** A saved search that re-runs on a schedule and
   collects new postings between visits.

Job results are live API calls, so an empty result usually means the query was
too narrow — not that something is broken.

---

## Optional: add API keys

The app works with none of these. Add them to `.env` and restart
(`docker compose up -d` again, or restart uvicorn).

| Variable | What it adds | Where to get it |
|---|---|---|
| `GOOGLE_API_KEY` | AI match evaluation and cover letters. Without it, scoring uses a keyword algorithm and every result is labelled as such. | <https://aistudio.google.com/apikey> |
| `OPENAI_API_KEY` | Same, if you prefer OpenAI. Also set `LLM_PROVIDER=openai`. | <https://platform.openai.com/api-keys> |
| `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | Adds Adzuna as an extra job source. Set `ADZUNA_COUNTRY=in` for India. | <https://developer.adzuna.com> (free tier) |

**Never prefix a key with `VITE_`.** Anything named `VITE_*` gets compiled into
the public JavaScript bundle and is readable by anyone who loads the page. The
variables above are read only by the server.

If you set `GOOGLE_API_KEY` and AI still doesn't kick in, the model name is the
usual cause — model ids get retired. List the ones your key can use:

```bash
curl -H "x-goog-api-key: YOUR_KEY" https://generativelanguage.googleapis.com/v1beta/models
```

Then set `GEMINI_MODEL` in `.env` to one of them.

---

## Troubleshooting

**"Failed to fetch" in the browser.** The backend is still starting — it runs
database migrations first. Wait ~15 seconds and reload. If it persists,
`docker compose logs backend` will say why.

**Port already in use.** Something else is on 8080, 8000 or 5432. Either stop
it, or change the left-hand side of the port mappings in `docker-compose.yml`
(e.g. `"9080:80"`).

**Docker build fails on `npm run build`.** That step typechecks before
building, so a type error stops the build by design. The error message names
the file and line.

**Nothing in the Jobs tab.** Confirm the backend answers:
`curl http://localhost:8000/health` should return `{"status":"healthy",...}`.

---

## What this app does and doesn't do

It aggregates jobs, scores them against your resume, and tracks what you
applied to. It **does not** auto-submit applications to employer portals or
send cold emails to recruiters — that breaks those portals' terms of service.
It prepares the application and opens the real listing for you to submit.

Running the tests, if you're curious:

```bash
cd backend && pytest        # 101 tests, no services needed
npm run typecheck           # from the project root
```
