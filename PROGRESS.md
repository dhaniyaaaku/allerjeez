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

---

## 2026-06-02 — Day 3 (DONE)

### Status: complete. Full email -> profile flow working end-to-end against Neon.

### Done
- Added deps via `uv add`: `streamlit`, `httpx`, `pydantic[email]`
- Created `app/schemas/` folder with `__init__.py`
- Built Pydantic schemas in `app/schemas/user.py`: `UserCreate`, `UserProfileUpdate`, `UserRead`
- `UserRead` uses `model_config = ConfigDict(from_attributes=True)` for direct construction from SQLAlchemy model
- Email validation via Pydantic's `EmailStr` (email-validator backing it)
- Built 3 endpoints in `app/api/users.py`:
  - `POST /users` (idempotent: returns existing if email exists, else creates)
  - `GET /users/me?email=...` (404s if not found)
  - `PUT /users/me/profile?email=...` (partial update via `payload.model_dump(exclude_unset=True)`)
- Email normalization (`email.lower()`) everywhere
- Wired `users_router` into `app/main.py`
- Verified all 5 endpoints via Swagger UI: create, get, update, re-get, 422 on bad email, 404 on missing user
- Created `frontend/streamlit_app.py`:
  - `st.session_state["email"]` as the "logged in" check
  - Login screen (st.form) -> calls `POST /users`, stashes email in session_state
  - Profile screen with 3 multiselects (allergies, dietary_preferences, conditions)
  - Sidebar with display name + Log out button
  - Helpful constants: COMMON_ALLERGENS (14), DIETARY_PREFERENCES (9), CONDITIONS (10)
  - `API_BASE_URL` from env var with `127.0.0.1:8000` fallback (twelve-factor)
- Ran both services together (FastAPI on 8000, Streamlit on 8501)
- Verified end-to-end: login -> set allergies + dietary prefs + conditions -> save -> log out -> log back in -> data pre-filled

### Decisions made today
- Schemas live in `app/schemas/` (separate from `app/models/`). API contract != database schema. Clean separation.
- "Auth": just an email in `st.session_state`. No password, no JWT, no OAuth. Deliberate scope cut for portfolio app. Documented as such in the UI ("portfolio demo, not a production app").
- Streamlit "send all fields on save" instead of partial update from frontend. Backend supports both via `exclude_unset`; frontend chose clarity over minimal payload.
- Two terminal windows for dev: one for FastAPI, one for Streamlit. Both depend on WARP being on.

### Next (Day 4)
- Download Open Food Facts taxonomies (allergens.txt, additives.txt)
- Hand-curate small CSV of ~30 IARC carcinogens
- Build `Ingredient` SQLAlchemy model (canonical_name + aliases + e_number + category + iarc_group + regulatory flags + source URLs)
- Write `scripts/ingest_ingredients.py` to merge sources and bulk-insert
- Verify row count in Neon

### Blockers / open questions
- None

### Notes
- Day 3 pushed as commit `2639c0d`
- Project state at end of Day 3: 4 endpoints, 2 models, 1 working frontend, 1 deployed-ready Dockerfile, 0 secrets in Git
- Resume-defensible artifacts so far: FastAPI async, SQLAlchemy 2.0 async, Pydantic v2 schemas, JSONB+ARRAY column types, idempotent endpoints, partial-update semantics, Docker, Streamlit, Neon Postgres, full local dev loop working

---

## 2026-06-02 — Day 4 (DONE)

### Status: complete. 112 curated ingredients in Postgres, ready for Day 5 vision pipeline.

### Done
- Built `Ingredient` SQLAlchemy model with: canonical_name (unique+indexed), aliases (ARRAY), e_number (indexed), category (indexed), is_allergen, allergen_group, iarc_group (indexed), regulatory_flags (JSONB), common_concerns (ARRAY), notes (Text), sources (ARRAY)
- Registered Ingredient model in `app/models/__init__.py` so `create_all` picks it up
- Originally tried fetching Open Food Facts taxonomies via HTTPS. Both URLs now 404. The wiki redirects through Anubis (anti-scraping proof-of-work challenge). Public CDN paths are dead.
- **Pivoted to offline bundled CSVs in `/data`** — better engineering anyway: deterministic, no network dep, no fragility, curated quality > scraped quantity
- Hand-curated 3 CSVs:
  - `data/allergens.csv`: 14 entries covering FDA top-9 + EU top-14 (milk/eggs/peanuts/tree-nuts/soy/wheat/gluten/fish/shellfish/sesame/mustard/celery/sulphites/lupin) with rich aliases including Indian terms (atta, maida, suji, ghee, rai, etc.)
  - `data/additives.csv`: 75 E-numbered additives across colorants, preservatives, sweeteners, antioxidants, emulsifiers, thickeners, etc., with regulatory flags (banned-in-EU, hyperactivity-warning, IARC class, etc.)
  - `data/iarc_carcinogens.csv`: 30 hand-picked food-relevant IARC entries across Groups 1, 2A, 2B, 3
- Rewrote `scripts/ingest_ingredients.py`:
  - Three CSV loaders (`stage_allergens`, `stage_additives`, `stage_iarc`) producing `StagedIngredient` dataclasses
  - `merge_staged()` unions aliases/concerns/sources across sources for entries sharing the same slug
  - `slugify()` normalizes canonical names
  - Bulk upsert via Postgres `INSERT ... ON CONFLICT (canonical_name) DO UPDATE SET ...` — idempotent
  - Excludes `id`, `canonical_name`, `created_at` from the conflict-update set
  - Prints per-category and per-IARC-group counts as a sanity report
- Ran ingestion: 14 + 75 + 30 = 119 raw -> 112 unique after merge (7 overlaps deduplicated)
- Verified in Neon:
  - 112 rows total
  - 9 Group 1 carcinogens (aflatoxins, arsenic, benzene, benzo-a-pyrene, cadmium, ethylene-oxide, formaldehyde, PCBs, processed-meat)
  - 14 allergen rows with rich Indian-friendly aliases (`milk` row includes ghee, atta, etc.)
  - 22 colorants, 19 contaminants, 12 sweeteners, 11 preservatives — healthy distribution

### Decisions made today
- **Cut runtime Open Food Facts fetching entirely.** Bundled CSVs in `/data`. Defensible engineering: smaller dependency surface, deterministic, faster ingestion, curated > scraped.
- IARC carcinogen count: 30 hand-picked food-relevant entries. Defensible: covers process contaminants, mold toxins, heavy metals, controversial additives. Full IARC list has 1000+ entries but most are occupational (asbestos, etc.) not food-relevant.
- Allergen aliases include Indian food terms (atta, maida, suji for wheat; ghee for milk; rai/sarson for mustard) — better fit for Indian food labels.
- Idempotent upsert via Postgres `ON CONFLICT DO UPDATE` — re-running the script is safe.
- Ingestion is a standalone script, not part of app startup. Run manually after data edits.

### Skipped
- pgvector setup (deferred to Week 3 RAG work)
- Open Food Facts live API for product lookups (deferred; could add as fallback later if needed)

### Next (Day 5)
- Get Gemini API key from Google AI Studio (free tier 1500 req/day)
- Add `google-generativeai` and `pillow` deps
- Build `app/services/vision.py`: takes image bytes, returns Pydantic-validated structured ingredient list
- Build `POST /scan/upload` endpoint accepting multipart image
- Use Gemini structured output (response_schema) so the LLM returns valid JSON not free text
- Smoke-test on real food product photos
- Add GEMINI_API_KEY to .env (and to .env.example)

### Blockers / open questions
- None

### Notes
- Day 4 pushed as commit `342c422`
- Project state at end of Day 4: 4 endpoints, 3 models (User/Scan/Ingredient), 112 ingredients in Postgres, 1 frontend, 1 ingestion script, full data foundation for AI pipeline
- Interview-defensible: "I chose offline curated CSVs over runtime scraping after my source's anti-scraping protection broke ingestion. Better engineering — smaller dependency surface, no fragility, curated quality."

---

## 2026-06-02 — Day 5 (DONE)

### Status: complete. Gemini Vision is extracting structured ingredient lists from real food photos.

### Done
- Signed up for Gemini API via Google AI Studio. Created API key.
- Added `GEMINI_API_KEY` and `GEMINI_VISION_MODEL` to `.env` (gitignored) and to `.env.example` (committed).
- Added deps via `uv add`: `google-genai`, `pillow`, `python-multipart`
- Used the modern `google-genai` SDK (not the older `google-generativeai`).
- Updated `app/config.py` to read `gemini_api_key` (required) + `gemini_vision_model` (default "gemini-2.0-flash", override-able via env).
- Built `app/schemas/vision.py` with `ExtractedIngredients`:
  - `is_food_product: bool` (first field; LLM commits before extracting)
  - `product_name: str | None`
  - `language: str | None` (handles Hindi/English mixed)
  - `ingredients: list[str]` (in printed order, E-numbers preserved)
  - `confidence: float` (0.0-1.0, LLM self-reports)
  - `notes: str | None` (LLM-written user-friendly note on weirdness)
  - Each field's `description` doubles as an instruction to Gemini via the response_schema.
- Built `app/services/vision.py`:
  - Cached `genai.Client` (one instance, reused)
  - `extract_ingredients_from_image(bytes, mime_type)` async function
  - Calls `client.aio.models.generate_content(model, contents=[image_part, prompt], config=GenerateContentConfig(response_mime_type="application/json", response_schema=ExtractedIngredients, temperature=0.0))`
  - 5 MB upload limit
  - Pillow `img.verify()` to reject corrupt/non-image uploads pre-API
  - Strict prompt forbidding inference; rules to strip bullets, preserve E-numbers, lower confidence honestly
- Built `app/api/scans.py` with `POST /scan/extract`:
  - Multipart upload via FastAPI `UploadFile`
  - Allowed MIME types: jpeg/png/webp/heic/heif
  - HTTP error mapping: 415 (wrong type), 413 (too big), 422 (corrupt), 502 (upstream LLM failure)
- Wired `scans_router` into `app/main.py`
- Tested in Swagger UI:
  - Real Snickers package photo (Indian variant with E-numbers): extracted 18 ingredients at confidence 1.0, including `Emulsifer (Soya lecithin E322)`, both occurrences of `Sugar`, and `iodized salt`. Detected English. Product name "SNICKERS".
  - Non-food image (code editor screenshot): `is_food_product=false`, empty ingredients list, helpful `notes` explaining what the image showed.

### Bug encountered and fixed
- First Snickers test failed with 502 "RESOURCE_EXHAUSTED, limit: 0" on `gemini-2.0-flash`. Quota on that model is zero by default for new Google AI Studio API keys (Google routes you to paid Lite by default for new projects).
- Fix: switched to `gemini-2.5-flash` via env override (`GEMINI_VISION_MODEL=gemini-2.5-flash`). Worked immediately. No code change required — the model name being a setting paid off.
- Interview talking point: "I made the model name configurable via env so swapping providers/models is a config change, not a code change."

### Decisions made today
- **Model**: gemini-2.5-flash (free, generous quota, matched extraction quality)
- **Temperature**: 0.0 (deterministic; extraction is not a creative task)
- **Structured output via response_schema**: forces valid JSON, eliminates prose parsing
- **First field `is_food_product`**: makes the LLM commit to a binary decision before generating the rest. Defensive prompt engineering.
- **Schema field descriptions are prompts**: the `description=...` on each Pydantic field is part of the schema sent to Gemini. Instructions live with the field they constrain.
- **Validation order**: MIME type -> size -> Pillow verify -> LLM. Cheap checks first.
- **Status codes per error class**: 415/413/422/502 rather than generic 500. Recruiter signal.

### Next (Day 6)
- Build `app/services/ingredient_lookup.py`: fuzzy-match extracted strings to Postgres ingredients via rapidfuzz
- Build `app/services/safety_report.py`: produce structured personalized safety report
- Layer in user profile: allergens flagged against user's allergies, conditions raise extra flags (e.g., aspartame + pregnancy)
- Persist Scan to DB at the end of /scan/extract flow
- Add `GET /scans/me?email=` endpoint for scan history

### Blockers / open questions
- None

### Notes
- Day 5 pushed as commit `1e3357a`
- Project state at end of Day 5: 5 endpoints (1 AI-backed), 3 models, 112 ingredients KB, Gemini Vision integration with structured outputs, defensive validation
- Headline interview moment: "Snickers photo in, 18 structured ingredients out in 2 seconds. That's the AI engineer signal."

---

## 2026-06-02 — Day 6 (DONE)

### Status: complete. Full personalized safety pipeline working with hybrid rule+LLM lookup.

### Done
- Added `rapidfuzz` dep (was in plan but not installed)
- Built `app/services/ingredient_lookup.py`:
  - Three-tier matching: E-number regex (`E322` from "Soya lecithin E322") -> normalized exact -> fuzzy
  - Two fuzzy scorers: `WRatio` + `token_set_ratio`, take max
  - Threshold lowered to 82 after testing (was 88 — too strict, missed "Emulsifier (Soy lecithin)")
  - Returns `IngredientMatch` with raw, matched, score, method
- Built `app/schemas/safety_report.py`:
  - `IngredientFlag`: ingredient_name, raw_text_from_label, severity, reason, personalized, sources
  - `SafetyReport`: product_name, overall_verdict, personal_allergens, other_allergens, carcinogens, controversial_additives, safe_known_ingredients, unknown_ingredients, embedded extraction
- Built `app/services/safety_report.py`:
  - Four-tier classification: personal_allergen -> other_allergen -> carcinogen -> controversial_additive -> safe_known -> unknown
  - IARC severity mapping: 1/2A=high, 2B=medium, 3/4=low
  - Verdict computed deterministically: any_personal -> avoid-for-you, any_high_carc -> avoid-for-you, any_concern -> caution-for-you, else safe-for-you
  - `safe_known_ingredients`: matched-but-not-flagged. Separates harmless-known from unknown.
- Built `POST /scan/analyze`: full pipeline (Gemini extract -> rule lookup -> LLM fallback -> safety report -> persist Scan -> return)
- Built `GET /scan/me`: scan history per user, newest first
- Expanded `data/additives.csv` with ~20 common safe foods (sugar, salt, cocoa-butter, vanillin, etc.) so they go to safe_known instead of unknown
- Tested Snickers: avoid-for-you verdict, correctly flagged milk/peanuts as personal allergens, hydrogenated vegetable oil + soy lecithin as controversial. 13 unknowns -> 0 unknowns after fix.

### Hybrid KB + LLM fallback (architecture upgrade)
- User flagged that "huge knowledge base" was needed. Discussed 4 options:
  - A: Hybrid KB + LLM fallback with cache (PICKED — best hiring story, scales infinitely)
  - B: Bulk-import Open Food Facts dump (no safety signal, bloat)
  - C: Multiple FDA/EFSA/FSSAI lists (heavy parsing for marginal gain)
  - D: Keep at 130 (declined — user wanted bigger KB)
- Built `app/schemas/llm_lookup.py` with `LLMIngredientClassification`: canonical_name, is_real_food_ingredient, category (Literal enum), has_known_concerns, concerns, aliases, e_number
- Built `app/services/llm_ingredient_lookup.py`:
  - `classify_unknowns()` runs after rule-based matcher
  - Cache check: normalize raw -> slug -> lookup in DB (might be LLM-cached from before)
  - LLM call: Gemini classify single string against the strict schema with `temperature=0.0`
  - Persist: insert as new `Ingredient` row tagged `sources=["llm:gemini-2.5-flash"]` — audit trail
  - LLM never overrides authoritative entries; only fills gaps
- Wired into `POST /scan/analyze` between rule-based match and report build
- VERIFIED: tested with oyster sauce (rare ingredient), Neon shows new row `modified-corn-starch` with `category=thickener` and `sources={llm:gemini-2.5-flash}`. KB self-grew from observed data.

### Decisions made today
- Fuzzy threshold = 82 (down from 88) after empirical testing on Snickers
- `safe_known_ingredients` new bucket: matched-but-unflagged ingredients deserve their own list, not the "unknown" graveyard
- LLM fallback runs AFTER rule-based matching, only for unmatched. No double work.
- LLM source tagging: `sources=["llm:gemini-2.5-flash"]` enables future querying like "which classifications need expert review" or "what's authoritative vs generated"
- KB grows organically: every novel ingredient seen on a real product becomes a permanent KB entry. Production-shaped data over time.
- Hybrid symbolic + LLM = the 2026 production AI architecture. Rules where correctness matters; LLM for the long tail.

### Next (Day 7)
- Update Streamlit frontend: add scan upload page calling `POST /scan/analyze`, render the SafetyReport with sectioned UI (personal allergens, carcinogens, controversial, safe-known)
- Add scan history page calling `GET /scan/me`
- Sign up for Render free tier
- Create Render Web Service from GitHub repo, point at Dockerfile
- Configure env vars on Render (DATABASE_URL, GEMINI_API_KEY, GEMINI_VISION_MODEL)
- Deploy, smoke-test live URL end-to-end
- Decide how to run Streamlit + FastAPI together in one container (probably honcho/foreman or a simple supervisor script)

### Blockers / open questions
- None

### Notes
- Day 6 pushed as commit `a429789`
- Project state: 7 endpoints, 3 models, 132+ KB entries (growing), hybrid AI/rule pipeline, full personalized safety reports
- Headline interview moment: "Hybrid knowledge base — rules for safety-critical classifications, LLM for the long tail with cache+audit-trail. Every novel ingredient seen becomes a KB entry."

---

## 2026-06-02 — Day 7 (DONE) — WEEK 1 SHIPPED

### Status: LIVE at https://allerjeez.onrender.com

### Done
- Themed Streamlit frontend with custom neo-brutalist CSS (orange page, chunky black borders, hard drop-shadows, pastel tiles)
- Built brand-coherent landing page: "allerjeez." headline + tagline + login form + 3-step "how it works" strip + "FDA · EFSA · IARC · WHO" trust badge
- Built scan page: greeting pill, giant headline, action buttons, personalized profile card with allergy/condition pills, dashed-border dropzone with file upload + camera options
- Iterated CSS through multiple rounds (button heights, label sizes, label fonts, color matching). Honest acknowledgement of Streamlit's CSS friction limits; stopped at "good enough" instead of pixel-perfect.
- Built `app/api/stats.py` for `/stats` endpoint
- Added `_resolve_display_name` helper to handle stale "string" placeholders from earlier testing
- Built `Dockerfile` v2: copies frontend/, data/, scripts/, start.sh; exposes 8080
- Built `start.sh`: exports venv path to PATH, launches FastAPI in background on 127.0.0.1:8000, exec's Streamlit on $PORT (Render's required port). Explicit `[start.sh]` log lines for debugging.
- Added retry-with-exponential-backoff to `app/services/vision.py` for transient Gemini 5xx/429 errors (4 attempts, base 2s, doubles each retry)
- Bug encountered: `start.sh` initially used `uv run streamlit` but the container PATH lost the uv binary location after FastAPI background launch. Fix: set PATH to `/app/.venv/bin` explicitly, call binaries directly without `uv run` prefix.
- Bug encountered: Initial `set -e` in start.sh silently killed the script. Removed and replaced with explicit echo logging.
- Tested locally: rebuilt image, ran `docker run --rm -p 8080:8080 --env-file .env -e PORT=8080 allerjeez:dev`. Both FastAPI + Streamlit started. End-to-end scan flow verified in browser at localhost:8080.

### Deployment
- Signed up for Render via GitHub
- Created Web Service from `dhaniyaaaku/allerjeez` repo
- Region: Singapore (closest to India)
- Instance type: Free (512MB RAM, 0.1 CPU, sleeps after 15min idle)
- Auto-deploy: on every push to main
- Env vars set on Render: DATABASE_URL (Neon), GEMINI_API_KEY, GEMINI_VISION_MODEL=gemini-2.5-flash
- Health check path: empty (Render falls back to TCP probe — `HEAD /` returns 405 which is harmless)
- Build took ~5-6 min, service went Live
- Smoke-tested live URL: login works, scan works, report renders correctly

### Decisions made today
- Streamlit-as-front-door: Streamlit on $PORT, FastAPI on internal 127.0.0.1:8000. One container, one public port, no docker-compose needed.
- Pivoted from `uv run X` to direct venv-binary invocation inside the container to avoid PATH issues at runtime.
- Retry on 503: production reliability for upstream LLM hiccups. 4 attempts with exponential backoff (2, 4, 8, 16s).
- Deferred several Streamlit polish issues (peach action buttons not yellow/coral, dropzone background) — diminishing returns vs deployment value.
- Render free tier: acceptable for portfolio. Cold start ~20-30s on first request after 15min idle. Pre-warm before interviews.

### Headline shipped today
- Public URL: **https://allerjeez.onrender.com**
- 7 backend endpoints + Streamlit UI + Postgres KB + Gemini Vision + hybrid rule/LLM classifier + retry-resilient pipeline
- Total monthly cost: $0
- Commit deployed: `3ab435e`

### Week 1 — DONE
- All 7 days completed
- Project: live, deployed, working end-to-end
- Headline metric for resume (still to measure in Week 2): allergen recall on hand-labeled gold set

### Next (Week 2)
- Build first eval gold set: 50 image -> expected ingredients hand-labeled pairs
- Add Gemini-generated plain-English explanations per flagged ingredient
- Run eval, get baseline extraction accuracy %, add to README
- Tweak prompt/temperature based on eval results
- This is the rigor that turns a working demo into a defensible engineering project

### Blockers / open questions
- None
- Future cosmetic polish on scan page (dropzone styling, action button colors) deferred — not blocking

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
