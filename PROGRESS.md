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
