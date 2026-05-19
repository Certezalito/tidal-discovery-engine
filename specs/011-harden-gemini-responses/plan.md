# Implementation Plan: Harden Gemini Responses

**Branch**: `011-harden-gemini-responses` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from [spec.md](spec.md)

## Summary

Harden Gemini-backed playlist generation so structurally unusable responses, valid-but-empty parsed payloads, and transient provider failures are classified before exclude-favorites filtering runs. The implementation uses response fields plus status categories to apply one recovery retry, then fails closed with actionable Gemini-specific guidance when still unusable. For non-retryable status failures, existing fallback model behavior is preserved only when already configured; otherwise the run fails immediately.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: click, tidalapi, pylast, python-dotenv, google-genai; internal services in `src/services/`  
**Storage**: N/A; retry and classification state are in-memory only for a single CLI run  
**Testing**: `uv run python -m unittest` plus `ruff check .` for behavior and lint validation  
**Target Platform**: Linux CLI execution for interactive and unattended runs
**Project Type**: Single-project CLI application  
**Performance Goals**: Preserve current successful-run latency; add at most one recovery retry for weak or valid-empty Gemini responses  
**Constraints**: Fail closed on unrecoverable Gemini errors; distinguish API/status failures from structured-response failures; keep exclude-favorites attribution separate from provider failures; preserve configured fallback behavior only when present  
**Scale/Scope**: One recommendation path and its user-facing troubleshooting/docs; no new persistent storage or service boundaries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **User-Centricity & Understandability**: Behavior is defined in CLI terms with concrete quickstart and troubleshooting guidance.
- [x] **Evidence & Unknowns**: Gemini response semantics and status categories are captured from service evidence and provider docs.
- [x] **Automation**: Recovery behavior remains non-interactive and suitable for unattended runs.
- [x] **Personalization**: Existing recommendation and favorites personalization flows are preserved.
- [x] **Extensibility**: Classification/recovery changes remain within Gemini service and CLI orchestration boundaries.
- [x] **Reliability**: Single-retry policy, fail-closed outcomes, and clear attribution are explicitly defined.
- [x] **Verifiability**: Validation requirements map to targeted tests for retry, final failure, attribution, and regressions.
- [x] **Documentation Quality Gate**: README/quickstart behavior and failure guidance updates are included.

**Gate Result (Pre-Research)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/011-harden-gemini-responses/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── gemini-response-recovery-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py
├── services/
│   ├── gemini_service.py
│   ├── lastfm_service.py
│   └── tidal_service.py
└── lib/

tests/
├── test_cli.py
├── test_gemini_service.py
├── test_tidal_service.py
└── test_exclude_favorites.py
```

**Structure Decision**: Keep the existing single-project CLI structure. Implement recovery/classification in `src/services/gemini_service.py` with failure-attribution integration in `src/cli/main.py`; preserve modular boundaries and existing non-Gemini behavior.

## Phase 0: Research Output

See [research.md](research.md).

Resolved topics:

- Structured response usability boundaries (`parsed`, `candidates`, `prompt_feedback`, `finish_reason`)
- Status-code retry categories and fail-fast classes
- Single-retry behavior for valid-empty responses
- Preservation of existing configured fallback behavior for non-retryable status failures
- Failure-attribution separation from exclude-favorites filtering

## Phase 1: Design Output

- Data model: [data-model.md](data-model.md)
- Contract: [contracts/gemini-response-recovery-contract.md](contracts/gemini-response-recovery-contract.md)
- Quickstart: [quickstart.md](quickstart.md)

## Post-Design Constitution Check

- [x] User-visible behavior and remediation guidance are explicit for weak/empty responses.
- [x] Unknown external behavior is resolved or constrained by response and status contracts.
- [x] Reliability requirements capture one recovery retry and fail-closed semantics.
- [x] Validation scope includes exact valid-empty final-failure coverage and attribution safety.
- [x] Documentation artifacts are aligned with retry/failure terminology.

**Gate Result (Post-Design)**: PASS

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations requiring justification.
