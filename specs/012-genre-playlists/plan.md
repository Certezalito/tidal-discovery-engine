# Implementation Plan: Genre Playlists

**Branch**: `012-genre-playlists` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from [spec.md](spec.md)

## Summary

Build a new genre-organization workflow that reads the full Tidal library, uses Gemini to classify tracks into a single best genre match (cached locally), creates or reuses a target Tidal folder, and maintains genre playlists with sync semantics (add new tracks and remove tracks no longer in the library). Existing groundwork already covers key primitives (library fetch, Gemini recommendation/classification integration patterns, folder creation, and playlist creation), so this feature focuses on orchestration logic, local cache management, deterministic sync behavior, and targeted tests.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: click, tidalapi, google-genai, python-dotenv; internal services in `src/services/`

**Storage**: Local JSON or SQLite file for Gemini genre cache (e.g., `.tde_genre_cache.json` or `.tde_genre_cache.db`); runtime processing of Tidal library

**Testing**: unittest test suite under `tests/` plus linting with `ruff check .`

**Target Platform**: Linux CLI execution (interactive and unattended runs)

**Project Type**: Single-project CLI application

**Performance Goals**: Successfully process a 5,000-track library in one run; incremental re-run avoids full rebuild where possible and preserves stable runtime for sync operations

**Constraints**: Must handle API paging/rate-limit realities, keep behavior non-interactive once configured, and fail gracefully with actionable logs when classification or playlist sync fails

**Scale/Scope**: One new CLI workflow and service orchestration path covering full-library genre classification, persistent local caching, configured minimum track thresholds for playlists, and ordered folder/playlist sync

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **User-Centricity & Understandability**: Feature behavior is framed as explicit CLI outcomes with planned quickstart usage and failure guidance.
- [x] **Evidence & Unknowns**: All clarified requirements are captured in `spec.md`; no unresolved clarification markers remain.
- [x] **Automation**: Workflow is designed for unattended execution once auth/config is in place.
- [x] **Personalization**: Genre playlists are derived directly from the user’s own library tracks.
- [x] **Extensibility**: Logic remains modular across CLI/service layers and can support future genre providers.
- [x] **Reliability**: Plan includes retry/error handling expectations for classification and Tidal operations.
- [x] **Verifiability**: Plan calls for targeted tests on sync behavior, unknown-genre handling, and idempotent reruns.
- [x] **Documentation Quality Gate**: Quickstart and contract artifacts are included for behavior clarity.

**Gate Result (Pre-Research)**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/012-genre-playlists/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── genre-playlist-sync-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py
├── services/
│   ├── gemini_service.py
│   ├── genre_playlist_service.py
│   └── tidal_service.py
└── lib/

tests/
├── test_cli.py
├── test_gemini_service.py
└── test_tidal_service.py
```

**Structure Decision**: Keep the existing single-project CLI structure. Implement feature orchestration in CLI and service methods without adding new top-level modules.

## Phase 0: Research Output

See [research.md](research.md).

Resolved topics:

- Full-library pagination and batching strategy
- Gemini genre classification behavior and unknown handling
- Local cache mechanics (storage, miss/hit rules, bypassing "Unknowns")
- Single-genre assignment and `Unknown` fallback semantics
- Minimizing playlist sprawl via size thresholds (grouping into "Others")
- Ordered playlist sync to leverage Tidal's native "Updated date" sorting
- Playlist sync algorithm (add new + remove deleted) without duplicate churn
- Error-handling boundaries and logging strategy

## Phase 1: Design Output

- Data model: [data-model.md](data-model.md)
- Contract: [contracts/genre-playlist-sync-contract.md](contracts/genre-playlist-sync-contract.md)
- Quickstart: [quickstart.md](quickstart.md)

## Post-Design Constitution Check

- [x] User-visible behavior is explicit for classification, unknown genres, and sync updates.
- [x] Reliability rules define safe handling for API and classification failures.
- [x] Validation scope captures behavior-changing paths and rerun idempotence.
- [x] Documentation artifacts define run and verification scenarios for end users.

**Gate Result (Post-Design)**: PASS

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations requiring justification.
