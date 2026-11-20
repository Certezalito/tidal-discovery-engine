# Implementation Plan: Migrate to Current Gemini Interaction Method

**Branch**: `023-migrate-gemini-interactions` | **Date**: 2026-11-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-migrate-gemini-interactions/spec.md`

## Summary

Migrate Tidal Discovery Engine's Gemini integration from the legacy `generateContent` API (`client.models.generate_content` + `types.GenerateContentConfig`) to Google's current **Interactions API** (`client.interactions.create` in `google-genai>=2.25.0`), completely retiring legacy content-generation calls while preserving 100% backward compatibility across all CLI commands (`recommend`, `radio`, `organize` / `genre-organizer`), flags, `.env` settings, and local SQLite genre caches.

Key technical elements established by Phase 0 research:
- Upgrade `google-genai` minimum constraint in `pyproject.toml` to `>=2.25.0` (resolving to `3.6.1`).
- Replace `client.models.generate_content(...)` with `client.interactions.create(...)` using plain Python dicts/arguments (`model`, `input`, `store=False`, `service_tier`, `response_format`, `generation_config`), removing `types.GenerateContentConfig` and retired sampling parameters (`temperature`, `top_p`, `top_k`).
- Enforce Pydantic structured output schemas via top-level wrapper models (`RecommendationList` with strict `artist`/`title`-only `Song` items; `GenreClassificationList` with `GenreClassificationResult` items) validated against `interaction.output_text`.
- Retain `gemini-flash-latest` as the built-in default model and auto-substitute deprecated `gemini-1.5-*`, `gemini-2.0-*`, and `gemini-2.5-*` model identifiers with `gemini-flash-latest` plus a clear warning log.
- Configure task-appropriate reasoning effort via `generation_config={"thinking_level": ...}`: `"medium"` for recommendations (`recommend`, `radio`) and `"minimal"` for batch genre classification (`organize`) with automatic compatibility fallback to `"low"` on models that do not support `"minimal"`.
- Configure client-level timeouts via `genai.Client(api_key=api_key, http_options={"timeout": timeout_ms})` and unify exception/status-code handling across `genai.errors` and Interactions client exceptions.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `click`, `tidalapi`, `pylast`, `python-dotenv`, `google-genai>=2.25.0` (upgraded from `>=1.70.0`), `pydantic` (transitive via `google-genai`)  
**Storage**: Existing local SQLite genre cache (`data/genre_cache.db`, unchanged schema & read/write compatibility)  
**Testing**: `pytest>=9.1.1` (`uv run pytest`; 183 baseline passing tests)  
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows, interactive terminal & unattended cron/Task Scheduler)  
**Project Type**: CLI application with modular service layer  
**Performance Goals**: Zero regression on standard tier latency; preserve 15-minute (900s) configurable timeout and progressive retry backoff for flex tier; reuse 100% of cached genre classifications at zero AI token cost  
**Constraints**: Stateless single-turn requests (`store=False`); zero AI-generated ISRC codes (Principle VIII); strict default fail-fast flex cost protection (Principle VI); zero breaking CLI or `.env` changes  
**Scale/Scope**: Single cohesive service module (`src/services/gemini_service.py`), dependency manifest (`pyproject.toml` / `uv.lock`), automated test suite (`tests/test_gemini_service.py` plus regression verification across all test files), and end-user documentation (`README.md`, `.env.example`)

## Constitution Check

*GATE: Evaluated before Phase 0 research and re-evaluated post-Phase 1 design.*

| Principle / Quality Gate | Pre-Design Status | Post-Design Status | Verification Notes |
|--------------------------|-------------------|--------------------|--------------------|
| **I. User-Centricity & Understandability** | PASS | PASS | Zero breaking CLI/env changes; `README.md` & `.env.example` updates planned; all unknowns verified from live Google Gemini API docs (no guessing). |
| **II. Automation** | PASS | PASS | Deprecated `1.5`/`2.0`/`2.5` model auto-substitution prevents cron breakage; `Ctrl+C` exit `130` and flex fallback preserved. |
| **III. Personalization** | PASS | PASS | Higher reasoning (`medium`) for `recommend`/`radio` preserves and improves taste-tailored curation. |
| **IV. Extensibility** | PASS | PASS | Migration stays encapsulated inside `src/services/gemini_service.py`; `src/cli/main.py` and `src/services/genre_organizer_service.py` require zero interface changes. |
| **V. Reliability & Verifiability** | PASS | PASS | Unified exception/status extraction, single recovery retry on empty/blocked interactions, and targeted unit tests for every behavior change. |
| **VI. AI Cost & Token Efficiency** | PASS | PASS | Structured minimal JSON outputs, `minimal` (with `low` compatibility fallback) thinking on `organize`, flex tier & default fail-fast cost protection preserved. |
| **VII. Local Caching & Performance Efficiency** | PASS | PASS | Existing `data/genre_cache.db` SQLite cache schema and `genre`/`primary_genre`/`sub_genres` output contract preserved 100%. |
| **VIII. Grounded Metadata & Zero ISRC Hallucination** | PASS | PASS | `Song` Pydantic schema strictly contains `artist` and `title` only — no `isrc` requested or accepted from Gemini. |
| **IX. CLI Ergonomics & Friction Reduction** | PASS | PASS | All short commands (`tde`), flags, aliases, and sensible defaults remain unchanged. |
| **X. Critical Dependency Currency & Capability Discovery** | PASS | PASS | Verified latest `google-genai` (`3.6.1` on PyPI) and live Interactions API docs; `pyproject.toml` updated to `google-genai>=2.25.0`. |
| **XI. Human Readability & Inline Intent Documentation** | PASS | PASS | Implementation tasks include clear inline comments/docstrings explaining Interactions API idioms, `store=False`, `thinking_level` fallback, and removal of obsolete comments. |
| **Gate: Gemini SDK Idioms & Schema Standards** | PASS | PASS | Consulted `gemini-api-dev` skill + `references/migration.md` + official live docs; uses `client.interactions.create()`, Pydantic JSON Schema `response_format`, and `model_validate_json()`. |

No Constitution violations exist; all gates pass.

## Project Structure

### Documentation (this feature)

```text
specs/022-migrate-gemini-interactions/
├── spec.md                              # Feature specification (clarified 2026-11-19)
├── plan.md                              # This file (/speckit-plan output)
├── research.md                          # Phase 0 authoritative research decisions
├── data-model.md                        # Phase 1 Pydantic schemas, config entities & state machine
├── quickstart.md                        # Phase 1 end-to-end validation guide
├── contracts/
│   └── gemini-service-contract.md       # Phase 1 public service, error & CLI contracts
├── checklists/
│   └── requirements.md                  # Spec quality checklist (16/16 passing)
└── tasks.md                             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
pyproject.toml                           # Update google-genai>=2.25.0 (Principle X)
uv.lock                                  # Updated lockfile via uv
.env.example                             # Document deprecated-model substitution & Interactions notes
README.md                                # Document Interactions API migration, model substitution, reasoning posture

src/
├── cli/
│   └── main.py                          # Unchanged public callers of gemini_service (verified by tests)
├── lib/
│   └── database.py                      # Unchanged SQLite infrastructure
└── services/
    ├── gemini_service.py                # Primary migration target: client.interactions.create(), schemas, thinking_level, store=False, deprecated-model substitution, unified error handling
    ├── genre_cache_service.py           # Unchanged local genre cache
    ├── genre_organizer_service.py       # Unchanged caller of classify_tracks_genres (verified by tests)
    ├── lastfm_service.py                # Unchanged Last.fm provider
    └── tidal_service.py                 # Unchanged Tidal provider

tests/
├── test_gemini_service.py               # Updated & expanded tests for Interactions API, schemas, store=False, thinking_level, deprecated-model substitution, error & flex handling
├── test_cli.py                          # Regression verification (no breaking CLI changes)
├── test_cli_genre_organizer.py          # Regression verification (organize + sticky fallback)
└── ...                                  # Remaining suite (all 183+ tests passing)
```

**Structure Decision**: Single-project modular CLI structure matching the existing repository layout. All Gemini SDK and Interactions API migration logic is localized to `src/services/gemini_service.py` to preserve loose coupling (Principle IV) and avoid unnecessary churn in `src/cli/main.py` or `src/services/genre_organizer_service.py`.

## Complexity Tracking

> No Constitution Check violations to justify.
