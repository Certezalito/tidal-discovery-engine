# Implementation Plan: Gemini Flex Mode Support

**Branch**: `021-gemini-flex-mode` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-gemini-flex-mode/spec.md` with user direction: "the plan may need to handle the longer response time, more research may be needed here as I've never used the flex feature"

## Summary

Expand Gemini API integration to support Google's discounted "flex" inference tier (50% cheaper token rates with variable latency) across recommendation retrieval (`tde recommend`), single-seed radio curation (`tde radio`), and library genre classification (`tde organize`).

In accordance with official Google Gemini technical research, Flex mode utilizes opportunistic off-peak capacity resulting in variable response turnaround times of **1 to 15 minutes**. To ensure a robust user and runtime experience:
1. **Critical Dependency Currency (Constitution Principle X)**: Update `google-genai` in `pyproject.toml` to `>=1.70.0` (or modern release) to leverage native SDK `service_tier` and `http_options` support in `types.GenerateContentConfig`.
2. **Extended Client Timeout**: Configure an extended HTTP client timeout of 900 seconds (15 minutes / 900,000 ms) via `types.HttpOptions(timeout=...)` on flex requests, preventing premature SDK socket drops. Make this configurable via `GEMINI_FLEX_TIMEOUT_SECONDS` (default: 900).
3. **Upfront Liveness Feedback (Constitution Principle I & IX)**: Display an explicit informational notice before dispatching flex calls (`"Connecting to Gemini via Flex tier... turnaround is typically 1–15 minutes. Please wait..."`), eliminating user confusion.
4. **Clean Interruption & Diagnostics**: Catch `KeyboardInterrupt` (Ctrl+C) cleanly without stack traces (exit code 130), and provide actionable diagnostics if requests time out or fail due to capacity shedding (`category="flex-capacity"` or `"flex-timeout"`).
5. **Strict Cost Protection (Constitution Principle VI)**: Enforce fail-fast behavior on capacity exhaustion by default (`GEMINI_FLEX_FALLBACK_STANDARD=false`), strictly prohibiting unprompted fallback to full-price standard billing unless explicitly enabled.
6. **Centralized Precedence & Documentation**: Centralize tier and timeout resolution in `src/services/gemini_service.py` (`_resolve_service_tier`), support paired `--flex / --no-flex` CLI flags, and document all options, environment variables, and latency expectations in `README.md`.
7. **Structured Confirmation Logging & Terminal Notices (FR-015, FR-016, SC-008)**: Emit structured informational log messages at INFO level (`Gemini service tier resolution: tier='%s' source='%s' timeout=%sms`) and terminal notices confirming that flex mode is active and utilized during operations.
8. **Configurable Standard Tier Fallback (FR-017–FR-021, SC-009–SC-011)**: Add opt-in fallback to standard tier (`--flex-fallback-standard / --no-flex-fallback-standard` CLI flags and `GEMINI_FLEX_FALLBACK_STANDARD=true/false` in `.env`). When enabled, if flex capacity is exhausted (HTTP 503 / 429) or times out after progressive retries, the engine logs a warning and automatically recovers by executing under standard tier inference.
9. **Multi-Batch Sticky Fallback Semantics (FR-022)**: For multi-batch library organization (`tde organize`), once a batch triggers standard tier fallback, all subsequent batches within that execution run directly on standard tier to complete the sync without repeated multi-minute retry delays per batch.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `click`, `python-dotenv`, `google-genai>=1.70.0`, `pydantic`  
**Storage**: N/A (configuration resolution, runtime cache in SQLite, and API payloads)  
**Testing**: `pytest` (targeted unit and CLI tests in `tests/`)  
**Target Platform**: Linux CLI runtime (cross-platform compatible across Linux, macOS, Windows)  
**Project Type**: Single-project Command-Line Interface (CLI) application  
**Performance Goals**: No measurable overhead in argument parsing (<5ms); sub-second command validation; non-blocking user turnaround feedback  
**Latency & Timeout**: Standard tier turnaround: 1–5 seconds (timeout: 120s); Flex tier turnaround: 1–15 minutes (timeout: 900s, configurable via `GEMINI_FLEX_TIMEOUT_SECONDS`)  
**Constraints**: 100% backward compatibility when flex mode is omitted; fail fast on capacity preemption by default without unexpected standard tier billing; opt-in fallback to standard tier supported; graceful SIGINT exit (130)  
**Scale/Scope**: 1 dependency configuration file (`pyproject.toml`), 2 service modules (`gemini_service.py`, `genre_organizer_service.py`), 1 CLI module (`main.py`), 1 documentation file (`README.md`), test modules (`test_gemini_service.py`, `test_cli.py`, `test_cli_genre_organizer.py`)  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research & Post-Design Gate Evaluation

| Principle / Gate | Status | Design Evaluation & Notes |
|---|:---:|---|
| **Principle I: User-Centricity & Understandability** | **PASS** | Adds paired `--flex / --no-flex` and `--flex-fallback-standard / --no-flex-fallback-standard` flags, upfront turnaround notice (1–15 min), and documents latency and defaults in `README.md`. |
| **Principle II: Automation** | **PASS** | `GEMINI_SERVICE_TIER=flex` and `GEMINI_FLEX_FALLBACK_STANDARD=true` in `.env` enable unattended background/cron jobs to run cost-effectively while guaranteeing completion even during demand spikes. |
| **Principle III: Personalization** | **PASS** | Recommendation algorithms, taste profile seeding, and output schemas remain identical; only API billing tier, retries, and fallback change. |
| **Principle IV: Extensibility** | **PASS** | Centralized `_resolve_service_tier` and `_resolve_flex_fallback_standard` helpers in `gemini_service.py` cleanly encapsulate inference tier, timeout, and fallback resolution. |
| **Principle V: Reliability & Verifiability** | **PASS** | Targeted test cases cover precedence, flag validation, timeout configuration, capacity preemption error handling, progressive retries, standard fallback execution, and structured confirmation logging. |
| **Principle VI: AI Cost & Token Efficiency** | **PASS** | Core driver: 50% discount on token pricing; fail-fast rule is preserved by default (`fallback_standard=False`) so standard billing is strictly opt-in. |
| **Principle VIII: Grounded Metadata & Zero ISRC Hallucination** | **PASS** | Prompt structures and structured response models (`Song`, `GenreClassificationResult`) remain strictly catalog-grounded. |
| **Principle IX: CLI Ergonomics & Friction Reduction** | **PASS** | Paired `--flex / --no-flex` and `--flex-fallback-standard / --no-flex-fallback-standard` toggles allow intuitive per-command overrides; clean Ctrl+C cancellation without tracebacks. |
| **Principle X: Critical Dependency Currency** | **PASS** | Evaluated upstream `google-genai` capabilities, identified native `service_tier` and `HttpOptions(timeout=...)` in `>=1.70.0`, and updated `pyproject.toml`. |
| **Principle XI: Human Readability & Intent Documentation** | **PASS** | New helper functions, resolution logic, and CLI flags include clear explanatory docstrings and comments detailing latency management and fallback routing. |
| **Quality Gate: Error Handling for Unattended Execution** | **PASS** | Actionable `flex-capacity` and `flex-timeout` failure output clearly guides users on next steps when fallback is disabled; automatic standard fallback recovers cleanly when enabled. |
| **Quality Gate: Dependency Management via `uv`** | **PASS** | Upstream version constraint enforced via `uv` and PEP 621 `pyproject.toml`. |
| **Quality Gate: Documentation Updates Required** | **PASS** | Complete usage examples, timeout options, fallback options, and latency characteristics documented in `README.md`. |

No constitutional violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/021-gemini-flex-mode/
├── spec.md              # Feature specification (clarified with latency, timeout & fallback requirements)
├── plan.md              # Implementation plan (this file)
├── research.md          # Technical research & decisions (Phase 0, including latency profile & fallback)
├── data-model.md        # Entities, state transitions & resolution matrix (Phase 1)
├── quickstart.md        # Quickstart verification guide (Phase 1)
├── contracts/           # Interface contracts (Phase 1)
│   └── gemini-flex-contract.md
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Implementation tasks (/speckit-tasks output)
```

### Source Code (repository root)

```text
pyproject.toml                         # [MODIFY] Update google-genai dependency to >=1.70.0
README.md                              # [MODIFY] Document --flex / --no-flex, --flex-fallback-standard, GEMINI_SERVICE_TIER, GEMINI_FLEX_FALLBACK_STANDARD, and GEMINI_FLEX_TIMEOUT_SECONDS
src/
├── cli/
│   └── main.py                        # [MODIFY] Add --flex/--no-flex, --flex-fallback-standard/--no-flex-fallback-standard to recommend, radio, organize; add validation, upfront notice, and SIGINT handling
└── services/
    ├── gemini_service.py              # [MODIFY] Add _resolve_service_tier, _resolve_flex_fallback_standard, configure HttpOptions, retries, and standard tier fallback logic
    └── genre_organizer_service.py     # [MODIFY] Propagate flex tier and fallback setting into classify_tracks_genres batch calls with sticky fallback
tests/
├── test_gemini_service.py             # [MODIFY] Unit tests for service tier resolution, fallback resolution, retry policy, and fallback execution
├── test_cli.py                        # [MODIFY] CLI tests for flag validation, overrides, timeout handling, fallback flags, and error cases
└── test_cli_genre_organizer.py        # [MODIFY] CLI tests for organize flex flag and fallback propagation
```

**Structure Decision**: Standard single-project Python CLI structure. Modifications are isolated to the service layer (`gemini_service.py`, `genre_organizer_service.py`), CLI controllers (`main.py`), dependency definitions (`pyproject.toml`), and end-user documentation (`README.md`).

## Complexity Tracking

> *No constitutional violations. Table left blank.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| *None* | *N/A* | *N/A* |
