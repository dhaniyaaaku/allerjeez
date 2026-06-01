# Allerjeez — Living Project Spec

(Working title: "Ingredient Safety Analyser". Brand name: **Allerjeez** — pun on "allergy" + "jeez", capturing the user moment of discovering what's actually in their food.)

This file is the single source of truth for the project's scope, decisions, and rationale.
Update it whenever scope, stack, or strategy changes. Commit it to Git alongside code.

For the running build log (what's done, what's next), see `PROGRESS.md`.

---

## One-sentence pitch
A web app where a user signs in (email only), sets up an allergy/health profile, uploads a photo or screenshot of a food product, and receives a personalized safety report flagging allergens, IARC-classified carcinogens, and controversial additives — with plain-English explanations and source citations. Users can ask follow-up questions answered via RAG.

## Strategic context
- Author: Dhanya, final-month BSc CS (AI/ML), SRM AP, no industry experience
- Existing portfolio: research-heavy (QHSA-Net hyperspectral classification + ADRET paper)
- This project's role: engineering/product/deployment complement, NOT duplicate ML depth
- Target roles: AI Engineer, LLM Engineer, Applied AI Engineer, Backend+AI Engineer, Junior MLOps
- NOT targeting: Data Analyst, pure Data Engineer
- Budget: $0/month, free-tier only
- Timeline: tight; cut ornamental features

## Locked feature scope
1. Email-only "login" (no OAuth, no passwords)
2. Profile setup: allergies, conditions (pregnancy, diabetes, etc.), dietary preferences
3. Image/screenshot upload of food product
4. Gemini Vision extracts ingredients (Pydantic-validated structured output)
5. Fuzzy-match ingredients to Postgres knowledge base (rapidfuzz)
6. Personalized safety report:
   - Allergens flagged against user profile
   - IARC carcinogen classifications
   - Regulatory flags (banned/restricted ingredients)
   - LLM-generated plain-English explanations
   - Source citations on every claim
7. Follow-up Q&A via RAG (demo centerpiece) — answered from ~50 curated ingredient explainer chunks in pgvector
8. Scan history per user

## Cut features (with rationale)
| Cut | Why |
|---|---|
| Google OAuth | Highest-risk-to-demo, lowest-AI-signal. Email-only is enough for portfolio. |
| Alembic migrations | Over-engineering for single dev on single schema. Use `create_all` at startup. |
| mypy, pre-commit hooks, structlog | Engineering hygiene without interview signal at fresher AI level. |
| Multi-stage Dockerfile | Single-stage is fine for portfolio scale. |
| LangChain / LangGraph | Flow is linear. Direct Gemini SDK + Pydantic is simpler. |
| XGBoost ingredient classifier | Research projects already demonstrate ML signal. |
| Barcode scanning | Out of scope for v1. |
| URL input | Scraping fragility (Amazon/Flipkart actively block). |
| Product comparison | Out of scope for v1. |
| Native mobile app | Streamlit on mobile browser is enough. |
| Cosmetics products | Food-only for v1. |
| Fine-tuning | Prompt engineering + RAG hits targets. |
| Kubernetes / microservices | Premature. Single service, single container. |

## Tech stack (locked)
| Layer | Choice | Free? |
|---|---|---|
| Language | Python 3.13 | Yes |
| Backend | FastAPI | Yes |
| Frontend | Streamlit | Yes |
| Auth | Email-only (DB-stored) | Yes |
| Multimodal LLM | Google Gemini 2.0 Flash | Yes (1500 req/day) |
| Embeddings | sentence-transformers `BAAI/bge-small-en-v1.5` | Yes (local) |
| Vector store | pgvector inside Neon Postgres | Yes |
| Database | Neon Postgres free tier (0.5GB) | Yes |
| ORM | SQLAlchemy 2.0 async + `create_all` | Yes |
| Fuzzy matching | rapidfuzz | Yes |
| Structured outputs | Pydantic v2 | Yes |
| Linting | ruff | Yes |
| Container | Docker + docker-compose | Yes |
| Observability | Langfuse free cloud (Week 4 only) | Yes |
| CI/CD | GitHub Actions (ruff + pytest) | Yes |
| Hosting | Render free web service | Yes |
| Testing | pytest + httpx | Yes |
| Config | pydantic-settings | Yes |
| **Total monthly cost** | | **$0** |

## Data sources (all free, all official, no scraping)
- **Open Food Facts** taxonomies for allergens + additives (primary KB)
- **IARC carcinogen list** — hand-curated ~30 entries (CSV in repo)
- **PubMed E-utilities API** + **EFSA scientific opinions** + **FDA additive pages** — curated ~50 chunks for RAG knowledge base

## Headline metric for resume
"Achieved X% allergen recall on N hand-labeled real food products" (measure honestly during build).

## Demo centerpiece
The RAG Q&A flow. Polish this harder than the scan flow. The scan is the setup; Q&A is where the LLM earns its place.

## Eval harness (first-class, not Week 4 polish)
Three gold sets, all hand-labeled:
1. **Extraction accuracy:** 50 (image → expected ingredients) pairs
2. **Allergen recall (headline metric):** 30 (profile + product → expected allergen flags) pairs
3. **RAG quality:** 30 (question → expected answer + source) pairs

Results tracked in `eval/results.md`, committed to repo, regenerated as project evolves.

## Build timeline
| Phase | Goal |
|---|---|
| Week 1 (Days 1-7) | Core scan loop end-to-end, deployed to Render |
| Week 2 | LLM explanations + extraction eval gold set |
| Week 3 | RAG Q&A (demo centerpiece) + allergen recall eval |
| Week 4 | Polish: Langfuse, README results table, demo video, GitHub Actions CI |
| Post-build (2 weeks) | Deep-study every component for interview defense |

## Decisions & rationale (append as we go)

### 2026-06-01
- Spec locked after ~16 rounds of pressure-testing against alternatives (text-to-SQL, resume screener, kirana bot, tax assistant, social media decoder, climate tracker, loan risk analyser, content moderation, code migration, etc.)
- Email-only auth chosen over Google OAuth after second-opinion LLM flagged OAuth as highest-risk-to-demo, lowest-AI-signal
- Evals promoted from Week 4 polish to first-class concern after second-opinion LLM flagged it as the #1 interview probe for LLM/AI Eng roles
- RAG Q&A designated as demo centerpiece (not the scan flow)
- XGBoost ingredient classifier cut after confirming Dhanya's research projects already cover ML depth signal

## How to resume this project in a future conversation
1. Read the memory file: `C:\Users\dhany\.claude\projects\C--Users-dhany\memory\project_ingredient_safety.md`
2. Read this `PROJECT.md` for spec
3. Read `PROGRESS.md` for status
4. Check `git log` for actual code history
5. Continue from where `PROGRESS.md` left off
