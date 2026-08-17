# JobPulse

A job aggregator with resume-based match scoring, saved search campaigns, and
application tracking. It fetches openings from job-board APIs, merges the same
posting across boards, scores each against your resume, and helps you prepare
a tailored application — which **you** submit yourself.

## What it does, and what it does not

**It does:**
- Aggregate live openings from **company career boards** (Greenhouse, Lever,
  Ashby), the **Indian portals** (Naukri, LinkedIn, Indeed and others, reached
  through licensed aggregators), **Adzuna** and **Remotive**
- Merge the same posting found on more than one board into a single entry
- Extract required skills from job descriptions and score them against your resume
- Run **loops** — saved searches that re-run on a schedule and collect what is new
- Prepare an application kit per job: match breakdown, tailored resume guidance, cover note
- Track what you applied to and report a real funnel (reply rate, time to reply, per-resume performance)

**It does not:**
- Submit applications to employer portals on your behalf. Auto-filling and
  submitting third-party ATS forms breaks those portals' terms of service, so
  the app prepares the materials and opens the real listing for you to submit.
- Scrape recruiter email addresses or send cold outreach.
- Scrape Naukri, Indeed or LinkedIn directly. Their postings are reached
  through licensed aggregators instead — see below.

## Sources, and the Indian market

| Source | Credentials | Coverage |
|---|---|---|
| **Company boards** (Greenhouse / Lever / Ashby) | none | Indian product companies and funded startups, posted first-party |
| **JSearch** | free tier API key | Google for Jobs — Naukri, LinkedIn, Indeed, Foundit, Shine, Internshala |
| **Careerjet** | free affiliate key | Indian portals and company sites, `en_IN` locale |
| **Jooble** | free key on request | Indian index at `in.jooble.org` |
| **Adzuna** | free API key | Country-scoped aggregator; `ADZUNA_COUNTRY=in` |
| **Remotive** | none | Remote-first roles, global |

**How Naukri, LinkedIn and Indeed postings get here.** None of the three can be
queried directly. Naukri publishes no public API and prohibits scraping; Indeed
retired its Publisher API and XML feed, leaving an NDA-gated enterprise data
partnership; LinkedIn keeps job data behind Talent Solutions partnership and is
the most aggressive of the three about scraping. What all three *do* is
syndicate into Google for Jobs, which licensed aggregators index and resell —
so the postings arrive through a channel the portals opted into.

A posting keeps the identity of the portal it was published on: a Naukri
listing is stored with `source: naukri`, badged **Naukri** in the UI, and
filterable as Naukri. The aggregator is plumbing, not the brand. Set
`JSEARCH_PUBLISHERS=naukri,linkedin,indeed` to restrict results to specific
portals.

Every one of these keys is optional and independent. With none of them set the
app still works on the company career boards, which need no credentials —
those are first-party postings with no aggregator lag, no reposting, and a real
apply link, and they remain the highest-quality source in the mix.

Add or remove employers with `ATS_BOARDS` (`platform:company-slug`, comma
separated). A slug that 404s is skipped with a warning rather than breaking
the search, and each board is cached for 15 minutes so a multi-keyword search
does not refetch it per keyword.

India-specific behaviours worth knowing:

- **City aliases.** Bangalore/Bengaluru, Gurgaon/Gurugram, Bombay/Mumbai and
  friends are normalised, so searching one spelling finds the other. This also
  feeds the dedup fingerprint — without it, the same role listed as
  "Bangalore, Karnataka" and "Bengaluru-VTP, India" appeared twice.
- **Lakh/crore salaries.** "12-18 LPA", "₹12,00,000" (2-2-3 grouping),
  "₹12,00,000 - ₹18,00,000 per year" and "1.5 crore" are parsed to annual INR
  and displayed as ₹12L – ₹18L. Monthly quotes are annualised, which matters
  here because Indian postings quote monthly pay far more often than Western
  ones. Figures are validated against plausible salary bounds and rejected
  when the surrounding text is a business metric — Indian company blurbs quote
  user counts in crore, which once made every PhonePe posting report a ₹60 Cr
  salary.
- **Local title conventions.** The SDE ladder ("SDE-2", "SDE II") is matched
  against "Software Engineer", "fresher" is understood as an entry-level term,
  and stack acronyms (MERN, MEAN, ".NET") resolve to what they mean. Portal
  title noise — "Urgent Requirement for Java Developer | 3-5 Yrs | Bangalore"
  — is stripped before matching.
- **India-only by default.** `INDIA_ONLY=true` keeps results to postings
  reachable from India, including worldwide-remote roles. Without it the
  remote-first and global sources bury local results. Set it to `false` to
  search worldwide.

## How search filtering works

Sources fetch; one filter decides what matches. `app/services/job_filter.py`
applies the role, location, remote and market rules to every source alike, so
a new adapter inherits them and no source can invent a looser definition of
"this job matches".

The role rule is the part that matters most. A query's *discriminating* words
must appear in the job title or its extracted skills — a mention in the
description does not count. That distinction is the whole point: matching on
the description meant "data engineer" returned any frontend role whose text
happened to contain both words, which is most of them. Query words are sorted
into three kinds and enforced differently:

| Kind | Example | Rule |
|---|---|---|
| Seniority | senior, fresher, SDE-2 | Soft — rejects only a real conflict, so a senior search still surfaces "Backend Engineer" but never an internship |
| Role noun | engineer, analyst, manager | Matched by equivalence class: developer ≡ engineer, but analyst ≢ engineer |
| Domain | java, react, devops | Hard requirement, satisfied by the title or the skill list |

Results are ranked by how well they match, with a title hit outranking a skill
hit, and ties broken on recency.

## Architecture

| Layer | Stack |
|---|---|
| Frontend | React 18, Vite 6, Tailwind v4, TypeScript |
| Backend | FastAPI, SQLAlchemy 2 (async), asyncpg |
| Database | PostgreSQL 15, schema managed by Alembic |
| AI | Optional — Google Gemini or OpenAI |
| Infrastructure | Docker Compose |

## Quick start

```bash
cp .env.example .env      # then fill in what you need — see below
docker compose up -d --build
```

Dashboard: <http://localhost:8080> · API docs: <http://localhost:8000/docs>

### Credentials

All credentials are **server-side only** and are never sent to the browser.
Set them in `.env`; there is no UI field for an API key, by design.

- **No keys at all** — the app works. Remotive needs no credentials, and
  matching uses a deterministic keyword scorer. Every score is labelled with
  the method that produced it, so a heuristic result is never presented as an
  AI judgement.
- **`JSEARCH_API_KEY`** — adds Naukri, LinkedIn, Indeed, Foundit, Shine and
  Internshala postings via Google for Jobs. Free tier at
  <https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch>. This is the single
  highest-impact key for the Indian market. Optionally narrow it with
  `JSEARCH_PUBLISHERS=naukri,linkedin,indeed`.
- **`CAREERJET_API_KEY`** — free affiliate key at
  <https://www.careerjet.com/partners/>, `en_IN` locale.
- **`JOOBLE_API_KEY`** — free key on request at
  <https://jooble.org/api/about>; uses the Indian index.
- **`ADZUNA_APP_ID` / `ADZUNA_APP_KEY`** — adds Adzuna as another source.
  Free tier at <https://developer.adzuna.com>. Also set `ADZUNA_COUNTRY`: it
  selects the endpoint *and* the currency salaries come back in.
- **`GOOGLE_API_KEY` or `OPENAI_API_KEY`** — enables AI evaluation when you
  open a job. Job lists and scheduled loop runs stay deterministic on purpose;
  one model call per card would be slow and expensive for a ranking number.

## Local development

```bash
# Frontend
npm install
npm run dev            # http://localhost:5173
npm run typecheck      # `npm run build` runs this first — see the note below

# Backend
cd backend
python -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/python -m alembic upgrade head
./.venv/Scripts/python -m uvicorn app.main:app --reload
./.venv/Scripts/python -m pytest        # 50 tests, no services required
```

> **`vite build` does not typecheck.** A green build says nothing about type
> correctness — that is how a missing icon import once shipped as a runtime
> `ReferenceError`. `npm run build` now runs `tsc --noEmit` first so this
> cannot recur.

The test suite runs against in-memory SQLite and needs no Postgres.

## Database migrations

Alembic owns the schema.

```bash
cd backend
alembic upgrade head                                  # apply
alembic revision --autogenerate -m "describe change"  # after editing models
alembic downgrade -1                                  # roll back one
```

`Base.metadata.create_all` still runs at startup for convenience on a fresh
local database, but it only ever *creates missing tables* — it will not add a
column to a table that already exists. Any schema change needs a migration.

## How matching works

Score components, blended by weight:

| Component | Weight | Source |
|---|---|---|
| Skill coverage | 65 | Skills mined from the job description vs. your resume |
| Title alignment | 20 | Job title vs. your target role |
| Experience fit | 15 | Years the posting asks for vs. years on your resume |

Components with no data are dropped rather than guessed, and the result
carries a `confidence` value describing how much evidence the score rests on —
separate from how high the score is. A job with nothing extractable reports
that instead of returning a number.

Skill coverage saturates at 6 matched requirements. Job ads pad: one real
Remotive posting for a DevOps role ended with the agency's roster of every
stack they hire for, yielding fifteen "requirements" for one infrastructure
job. A straight matched/total ratio punished genuine matches for not knowing
stacks nobody asked for.

Source-provided tags are used only when the description corroborates them, for
the same reason — Remotive's tags are browse categories, not requirements.

## Project layout

```
backend/
  alembic/            migrations
  app/
    api/endpoints/    jobs, ai, applications, analytics, loops, profile
    models/           SQLAlchemy models
    schemas/          Pydantic request/response models
    services/
      ai/             provider transports + shared logic + heuristic scorer
      sources/        one adapter per job board
      job_service.py  persistence, dedup, skill attachment
      loop_service.py campaign execution
      scheduler.py    background runner
  tests/
src/
  components/         UI
  services/           API clients
  types/job.ts        shared types
```

## Adding a job source

Implement `JobSource` in `app/services/sources/`, returning `NormalizedJob`
objects, and register it in `default_sources()` in `sources/manager.py`.
Deduplication, skill extraction and persistence are handled for you, and the
UI builds its source filter from whatever comes back — no frontend change is
needed.

Two things to get right:

- **Do not write your own matching.** Filter server-side where the endpoint
  supports it, but let `job_filter` decide what matches. Returning a few extra
  postings is fine; a private definition of "matches" is what made results
  differ between sources.
- **Set `uses_location_param = False`** if the endpoint takes no location.
  `SourceManager` then asks once per keyword instead of once per city, rather
  than refetching the same list and discarding the copies.

If the source needs credentials, return `[]` and log when they are missing, so
an unconfigured key costs that one source rather than the whole search.
