# Allerjeez

**Live demo:** [allerjeez.onrender.com](https://allerjeez.onrender.com)

AI-powered food ingredient safety analyser. Upload a photo of any food product, get a personalized safety report flagging your allergens, IARC-classified carcinogens, and controversial additives — each explained in plain English with citations to FDA, EFSA, IARC, and WHO.

> First-time load on Render's free tier takes ~30 seconds to wake from sleep. Subsequent loads are instant.

---

## What it does

1. You sign in with your email and set up a health profile — allergies, dietary preferences, conditions.
2. You upload a photo or screenshot of a food product (Indian snacks, US-style packaged food, soft drinks, anything).
3. Gemini Vision reads the ingredients off the label as structured JSON.
4. A rule-based matcher reconciles those ingredients against a 130+ entry authoritative knowledge base sourced from FDA, EFSA, IARC, and WHO.
5. For ingredients the rules don't recognize, a smaller LLM classifies them and writes the result back to the KB — so the knowledge base grows organically with use.
6. The system produces a personalized safety report: ingredients you're allergic to, IARC carcinogen flags, controversial additives, and harmless ingredients matched safely.
7. Each flag gets a 1-2 sentence plain-English explanation generated and cached by an LLM.

---

## Architecture

```
+----------------+       HTTPS
|  Streamlit UI  |  ----------------+
|  (port $PORT)  |                  |
+----------------+                  |
        |                           v
        |  http://127.0.0.1:8000   +----------------+
        +------------------------> |   FastAPI      |
                                   |  (async)       |
                                   +----------------+
                                          |
            +-----------------------------+--------------------------+
            |                             |                          |
            v                             v                          v
    +---------------+           +-------------------+      +-------------------+
    | Gemini Vision |           | Postgres (Neon)   |      |   Gemini Lite     |
    |  2.5-flash    |           |  - users          |      |  (explanations    |
    |  (multimodal  |           |  - scans          |      |   + unknown       |
    |   extraction) |           |  - ingredients KB |      |   ingredient      |
    +---------------+           |  - explanations   |      |   classification) |
                                +-------------------+      +-------------------+
```

A single Docker container runs both Streamlit (public port) and FastAPI (internal port 8000). Streamlit calls FastAPI directly over localhost.

---

## Headline features

| Feature | Details |
|---|---|
| **Multimodal ingredient extraction** | Gemini 2.5 Flash with Pydantic structured-output schemas. 99.2% ingredient recall on a 25-image gold set. |
| **Hybrid knowledge base** | 130+ authoritative rule entries (FDA, EFSA, IARC, WHO) + LLM fallback for novel ingredients. LLM-generated entries are tagged with their source model so authoritative vs synthetic data is always distinguishable. |
| **Personalized safety report** | Allergens matched against the user's profile; carcinogens flagged with IARC group; controversial additives surfaced with regulatory context. |
| **LLM-generated explanations** | Each flag gets a 1-2 sentence plain-English explanation. Cache-first, quota-tolerant — falls back gracefully when the LLM is rate-limited. |
| **Eval harness** | Resumable 25-image gold set, end-to-end pipeline metrics, per-image breakdown of which allergens / carcinogens were missed. |
| **Free-tier infrastructure** | Neon Postgres, Gemini API, Render hosting. Total monthly cost: $0. |

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.13 | Modern stdlib, type system |
| Web framework | FastAPI | Async-first, OpenAPI auto-gen, Pydantic native |
| ORM | SQLAlchemy 2.0 async | Industry standard for Python + Postgres |
| Database | Neon Postgres | Generous free tier, pgvector support, scales to zero |
| Vision + text LLM | Gemini 2.5 Flash | Best quality / cost ratio for structured extraction |
| Explainer LLM | Gemini 2.5 Flash Lite | Separate quota counter, cheaper for high-volume short generations |
| Structured outputs | Pydantic v2 | Schema-validated LLM responses, no prose parsing |
| Fuzzy ingredient matching | rapidfuzz | C-backed; token-set ratio handles "Soya Lecithin (E322)" -> "soy-lecithin" cleanly |
| Frontend | Streamlit | Ship a UI in hours; mobile-friendly via browser |
| Package management | uv | Faster than pip, modern lockfile workflow |
| Containerization | Docker (single-stage) | Render deploy, identical local + production behaviour |
| Hosting | Render free tier | Auto-deploy from main, $0/month |

Things deliberately **not** included, with the engineering reasoning:

- **LangChain / LangGraph** — the request flow is linear; direct SDK + Pydantic is simpler and easier to debug.
- **docker-compose** — single-service app, single container, single port. Compose would be ceremony.
- **Alembic migrations** — solo developer, single schema; `Base.metadata.create_all` at startup is sufficient. Alembic earns its keep on multi-developer teams.
- **mypy / pre-commit** — engineering hygiene without interview signal at portfolio scale.
- **Authentication / OAuth** — explicit scope decision. Portfolio demo only. Email-as-identity is documented in-app.

---

## Eval

Methodology lives in [`eval/README.md`](eval/README.md). Headline metrics from [`eval/results.md`](eval/results.md):

| Metric | Value |
|---|---|
| Ingredient recall (Gemini extraction) | **99.2%** |
| Ingredient precision | 99.4% |
| Ingredient F1 | 99.2% |
| Allergen recall (full pipeline) | _Latest in `eval/results.md`_ |
| Latency p50 (end-to-end scan) | ~10s |
| Latency p95 | ~15s |

The eval runs each gold image through the **full pipeline** — Gemini Vision -> rule-based matcher -> LLM fallback -> safety report -> personalized allergen flagging. This measures what users actually see, not the naive substring match of the first-pass eval (which under-counted allergens that needed alias resolution).

The eval is resumable: per-entry results are cached, so a Gemini quota error mid-run doesn't waste prior progress. Rerun the same command later and it picks up from the cache.

---

## Engineering details worth highlighting

### Hybrid symbolic + LLM knowledge base

Safety-critical classifications (allergens, IARC carcinogens, banned additives) come from authoritative data in `data/*.csv`, ingested into Postgres. Novel ingredients the rules don't recognize are classified by a smaller LLM and persisted back to the same table, tagged with `sources: ["llm:gemini-2.5-flash"]`. Future scans hit the cache. This is the 2026 standard for production LLM products: rules where correctness matters, LLM for the long tail.

### Quota-aware retry

Gemini calls are wrapped with exponential-backoff retry on 429 / 5xx (`app/services/vision.py`). The explainer service (`app/services/explainer.py`) goes one step further — quota exhaustion returns `None` silently, so a flag still renders, just without an explanation. No user-visible crash from upstream API hiccups.

### Eval-driven iteration

First-pass eval reported 77.7% allergen recall using naive substring matching. Root-causing showed the misses were almost all alias gaps (`soybean` not aliased to `soy`, `hazelnuts` not aliased to `tree-nuts`). The eval methodology was corrected to call the actual matcher pipeline, and the alias map was expanded based on which misses the gold set surfaced.

### Container architecture

A single Docker container runs FastAPI in the background and Streamlit on the front-door port. The `start.sh` exports the venv's PATH explicitly so both binaries resolve cleanly under the Render free-tier image — a real bug encountered and documented during deployment.

---

## Local development

Prerequisites: Python 3.13, Docker Desktop, uv, a Neon Postgres connection string, a Gemini API key.

```bash
# Install deps
uv sync

# Set up env
cp .env.example .env
# Fill in DATABASE_URL, GEMINI_API_KEY, GEMINI_VISION_MODEL=gemini-2.5-flash

# Run FastAPI
uv run uvicorn app.main:app --reload

# In a separate terminal, run Streamlit
uv run streamlit run frontend/streamlit_app.py
```

Or run everything in a container:

```bash
docker build -t allerjeez:dev .
docker run --rm -p 8080:8080 --env-file .env -e PORT=8080 allerjeez:dev
```

Then visit `http://localhost:8080`.

### Ingest the ingredient knowledge base

```bash
uv run python -m scripts.ingest_ingredients
```

Idempotent: rerun safely.

### Run the eval

```bash
uv run python -m eval.run_eval                # full run
uv run python -m eval.run_eval --limit 5      # smoke test on first 5
uv run python -m eval.run_eval --force        # ignore cache, redo all
```

Writes per-image metrics to `eval/results.md` and caches successful entries in `eval/.cache_results.jsonl` so reruns skip them.

---

## Future work

Honest list of things this project doesn't do yet:

- **RAG-powered Q&A** on top of a curated explainer corpus, so users can ask "is sodium benzoate dangerous for kids?" and get a sourced answer.
- **Eval gating in CI** — GitHub Actions running the eval on every PR and failing on regressions.
- **Production observability** — Langfuse traces of every LLM call for debugging + cost monitoring.
- **Drift monitoring** — track classifier accuracy over time as Gemini's underlying model changes.
- **Multi-language support** — Indian ingredient labels are often Hindi + English mixed; the current allergen alias map only partially covers Hindi terms.
- **Mobile-first UI** — Streamlit on mobile browser works, but a native PWA shell would be a real upgrade.

---

## License

MIT.
