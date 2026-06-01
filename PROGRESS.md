# Build Progress Log

Append entries chronologically. Latest entries at the bottom.
Each entry: date, what was done, what's next, any blockers/decisions.

For spec and rationale, see `PROJECT.md`. For code history, use `git log`.

---

## 2026-06-01 — Day 1 (in progress)

### Status: setup phase, no code committed yet

### Done
- Verified Python 3.13.0 installed
- Verified Git 2.53 installed
- Verified VS Code 1.122 installed
- Installed Docker Desktop 29.5.2 (per-user install)
- Verified `docker --version` and `docker run hello-world` work
- Installed `uv` 0.11.17 package manager
- Created project folder: `C:\Users\dhany\Projects\ingredient-safety`
- Ran `uv init --app --python 3.13`
- Created initial `pyproject.toml`
- Added deps via `uv add`: `fastapi`, `uvicorn[standard]`, `pydantic-settings`
- Added dev dep via `uv add --dev`: `ruff`
- `uv.lock` generated, `.venv` created
- Saved project memory + this PROGRESS.md + PROJECT.md spec

### In progress
- Day 1 step 2.6: replace placeholder `main.py` with FastAPI hello-world app
- Then: verify `uv run uvicorn main:app --reload` serves the endpoints
- Then: initialize Git, first commit, push to GitHub

### Next (Day 2)
- Sign up for Neon Postgres free tier
- Write `Dockerfile` + `docker-compose.yml`
- Set up SQLAlchemy 2.0 async + `create_all` on startup
- Create initial models: `User`, `Scan`
- Verify app in container can connect to Neon

### Decisions made today
- Per-user Docker install (solo developer use)
- Project lives at `C:\Users\dhany\Projects\ingredient-safety`
- Confirmed scope cuts: OAuth → email-only, no Alembic, no mypy/pre-commit/structlog, single-stage Dockerfile

### Blockers / open questions
- None

### Notes
- Persistent memory + PROJECT.md + this PROGRESS.md set up so future Claude sessions can pick up the project mid-build without losing context
