# Build Progress Log

Append entries chronologically. Latest entries at the bottom.
Each entry: date, what was done, what's next, any blockers/decisions.

For spec and rationale, see `PROJECT.md`. For code history, use `git log`.

---

## 2026-06-01 — Day 1 (DONE)

### Status: complete. App scaffolded, FastAPI verified locally, code pushed to GitHub.

### Done
- Verified Python 3.13.0 installed
- Verified Git 2.53 installed
- Verified VS Code 1.122 installed
- Installed Docker Desktop 29.5.2 (per-user install)
- Verified `docker --version` and `docker run hello-world` work
- Installed `uv` 0.11.17 package manager
- Created project folder: `C:\Users\dhany\Projects\ingredient-safety`
- Ran `uv init --app --python 3.13`
- Added runtime deps via `uv add`: `fastapi`, `uvicorn[standard]`, `pydantic-settings`
- Added dev dep via `uv add --dev`: `ruff`
- `uv.lock` generated, `.venv` created
- Extended `.gitignore` for env files, IDE, OS junk, test/coverage artifacts, local data
- Replaced placeholder `main.py` with FastAPI app (root + /health endpoints)
- Verified `uv run uvicorn main:app --reload` serves all endpoints (/, /health, /docs)
- Swagger UI at /docs verified
- Configured Git identity: `dhaniyaaaku` / `karadhanya@gmail.com`
- First commit: `3abc3c0` — "Initial scaffold: FastAPI hello world + project spec"
- Renamed branch `master` → `main`
- Picked brand name: **Allerjeez** (pun on "allergy" + "jeez")
- Created GitHub repo: https://github.com/dhaniyaaaku/allerjeez
- Connected `origin`, pushed first commit (main branch)
- Saved persistent memory + PROJECT.md + this PROGRESS.md

### Next (Day 2)
- Sign up for Neon Postgres free tier
- Write `Dockerfile` + `docker-compose.yml`
- Set up SQLAlchemy 2.0 async + `create_all` on startup
- Create initial models: `User`, `Scan`
- Verify app in container can connect to Neon

---

## 2026-06-02 — Day 2 (DONE)

### Status: complete. Database layer working, app containerized, both verified against Neon.

### Done
- Signed up for Neon Postgres free tier (project: `allerjeez`, region: AWS Singapore, Postgres 17)
- Got direct connection string from Neon, saved to `.env` (gitignored)
- Created `.env.example` placeholder for the repo
- Restructured codebase: flat `main.py` -> `app/` package with `api/`, `models/`, `config.py`, `db.py`
- Added deps via `uv add`: `sqlalchemy[asyncio]`, `asyncpg`, `greenlet`, `pgvector`
- Built `app/config.py` (pydantic-settings reading `.env`)
- Built `app/db.py` with async engine; small URL normalizer strips sync-driver-only params (`sslmode=require`) and translates SSL into asyncpg `connect_args`. Real bug encountered and fixed.
- Built `app/models/base.py` (Base + TimestampMixin)
- Built `User` model: email (unique, indexed) + allergies/dietary_preferences/conditions (ARRAY) + extra_profile (JSONB) + timestamps
- Built `Scan` model: user_id FK with CASCADE delete + extracted_ingredients (JSONB) + safety_report (JSONB) + timestamps
- Added `lifespan` context manager to `main.py` that runs `Base.metadata.create_all` at startup
- Verified app starts cleanly and creates `users` + `scans` tables on Neon
- Hit `ConnectionResetError 10054` on college Wi-Fi (port 5432 blocked). Diagnosed as campus firewall, fixed by installing Cloudflare WARP. WARP must be on when working from campus.
- Wrote `Dockerfile` (single-stage, python:3.13-slim, deps-before-code caching pattern, EXPOSE 8000, host 0.0.0.0)
- Wrote `.dockerignore` (excludes .venv, .git, .env, caches, docs)
- Built image `allerjeez:dev` (135MB content) successfully
- Ran container with `docker run --rm -p 8000:8000 --env-file .env allerjeez:dev`, confirmed Neon connection + endpoints work identically to direct uvicorn

### Decisions made today
- Connection string format: used Neon's direct connection (no `-pooler` toggle visible in UI). Can switch to pooled later if connection limits become an issue.
- SSL handling: translate Neon's `sslmode=require` into asyncpg's `connect_args={"ssl": True}` instead of editing the URL in `.env`. URL stays in standard Postgres format; code adapts.
- **Skipped `docker-compose.yml`** entirely. Single-container app, Postgres at Neon. Compose would have been ceremony with no benefit. Defensible answer in interviews: "considered it, single service, opted out."
- Cloudflare WARP added to dev startup checklist (campus blocks port 5432)
- Skipped Alembic per scope cut. `create_all` at startup is idempotent and sufficient for this schema.

### Skipped (for now)
- `docker-compose.yml` (per scope decision above)
- Local Postgres in Docker (would need compose; not justified)

### Blockers / open questions
- None

### Next (Day 3)
- Build the `/users` endpoint: create/get user by email
- Add `/users/me/profile` endpoint: update allergies/conditions/dietary_preferences
- Wire up minimal Streamlit frontend: email "login" + profile setup form
- Use HTTP cookie to remember email between requests (no real auth, just identity)

### Notes
- WARP is required on every dev session from campus Wi-Fi
- Container size (135MB) is reasonable; can optimize with multi-stage later if needed (not now)
- All Day 2 work pushed to GitHub: commits `cedd86c` (db layer) and the upcoming Docker commit

### Decisions made today
- Per-user Docker install (solo developer use)
- Project folder: `C:\Users\dhany\Projects\ingredient-safety`
- Brand name: **Allerjeez** (memorable, recruiter conversation-starter)
- GitHub repo name: `allerjeez` (brand), with descriptive description for searchability
- Email used for Git commits: karadhanya@gmail.com (Dhanya's own, NOT Saikanth's — Saikanth shares the Claude subscription but is unrelated to this project)
- Confirmed scope cuts: OAuth → email-only, no Alembic, no mypy/pre-commit/structlog, single-stage Dockerfile

### Blockers / open questions
- None

### Notes
- Persistent memory + PROJECT.md + this PROGRESS.md set up so future Claude sessions can pick up the project mid-build without losing context
- LF/CRLF warnings on Windows are harmless; Git auto-converts line endings
