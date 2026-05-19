# Implementation Plan: Exclude Existing Favorite Tracks

**Branch**: `010-exclude-favorite-tracks` | **Date**: 2026-05-08 | **Spec**: `/specs/010-exclude-favorite-tracks/spec.md`
**Input**: Feature specification from `/specs/010-exclude-favorite-tracks/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add an optional CLI parameter to exclude tracks already present in the user's Tidal favorites from playlist output while preserving default behavior when the flag is absent. The implementation will load favorites through existing `tidal_service` pagination, build in-memory exclusion keys (ISRC first, normalized title + primary artist fallback), fail closed on incomplete retrieval, and validate behavior with targeted CLI/service tests.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: click, tidalapi, pylast, python-dotenv, google-genai; internal services in `src/services/`  
**Storage**: In-memory exclusion snapshot only (no new persistent storage)  
**Testing**: pytest tests in `tests/` (CLI/service behavior and failure-path assertions)  
**Target Platform**: Linux CLI execution (compatible with existing unattended scheduler usage)
**Project Type**: Single-project CLI application  
**Performance Goals**: Additional runtime for favorites filtering <=5s for typical libraries (~2,000 favorites)  
**Constraints**: Fail-closed on favorites retrieval failure; max 2 retries per failed favorites page; no favorites disk cache  
**Scale/Scope**: One new CLI option and related service/filter logic affecting recommendation finalization paths

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **User-Centricity & Understandability**: User-facing behavior and failure semantics are explicit; README/quickstart update tasks are planned with concrete examples.
- [x] **Evidence & Unknowns**: External capability unknowns were resolved via repository evidence (`src/services/tidal_service.py`, `debug_isrc.py`, `inspect_tidal_isrc.py`) and captured in `research.md`.
- [x] **Automation**: Feature remains non-interactive after setup and compatible with unattended runs.
- [x] **Personalization**: Exclusion logic uses user-specific favorites to improve novelty relevance.
- [x] **Extensibility**: Changes are scoped to CLI option parsing plus service/filter modules, preserving modular boundaries.
- [x] **Reliability**: Explicit retry policy, fail-closed behavior, and clear error messaging are part of the design.
- [x] **Verifiability**: Each behavior-changing path maps to targeted automated tests (enabled/disabled/failure/retry/no-cache).
- [x] **Documentation Quality Gate**: Plan includes quickstart and README update requirements for new option and failure guidance.

**Gate Result (Pre-Research)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/010-exclude-favorite-tracks/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── exclude-favorites-cli-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py
├── services/
│   ├── tidal_service.py
│   ├── lastfm_service.py
│   └── gemini_service.py
└── lib/

tests/
├── test_cli.py
├── test_tidal_service.py
└── test_gemini_service.py
```

**Structure Decision**: Keep the existing single-project CLI layout and implement behavior in existing CLI/service layers; add only feature documentation artifacts under the current spec directory.

## Phase 0: Research Output

See `/specs/010-exclude-favorite-tracks/research.md`.

Resolved topics:

- Favorites retrieval API and pagination approach
- Identity matching strategy (ISRC + normalized fallback)
- Failure policy and retry semantics
- Memory-only data retention boundary
- Performance target interpretation

## Phase 1: Design Output

- Data model: `/specs/010-exclude-favorite-tracks/data-model.md`
- Contract: `/specs/010-exclude-favorite-tracks/contracts/exclude-favorites-cli-contract.md`
- Quickstart: `/specs/010-exclude-favorite-tracks/quickstart.md`

## Post-Design Constitution Check

- [x] User-facing option behavior, examples, and failure guidance are fully specified.
- [x] Unknown external behavior is resolved or explicitly constrained by design contracts.
- [x] Reliability requirements (retry/fail-closed/logging) are represented in contract and data model.
- [x] Validation scope is concrete for CLI and service behavior regressions.
- [x] Documentation artifacts are present and aligned with terminology (`--exclude-favorites`).

**Gate Result (Post-Design)**: PASS

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations requiring justification.
