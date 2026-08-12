# Implementation Plan: Fix Duplicate Genre Playlists

**Branch**: `015-fix-genre-playlist-duplicates` | **Date**: 2026-08-11 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/015-fix-genre-playlist-duplicates/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Modify the genre playlist generation logic to correctly paginate Tidal folder items and clean up duplicate playlists to ensure true idempotency.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12+

**Primary Dependencies**: tidalapi

**Storage**: SQLite (caching only)

**Testing**: pytest

**Target Platform**: CLI

**Project Type**: CLI

**Performance Goals**: Minimal API calls via deltas

**Constraints**: N/A

**Scale/Scope**: Support 50+ playlists

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*


1. **User-Centricity**: N/A (bug fix, no new CLI args).
2. **Idempotency**: P1! The core of this feature is enforcing idempotency.
3. **Local Caching & Performance**: Relying on pagination efficiently.
*GATE Status*: Passed.


## Project Structure

### Documentation (this feature)

```text
specs/015-fix-genre-playlist-duplicates/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── services/
│   ├── genre_playlist_service.py
│   └── tidal_service.py
tests/
└── test_genre_playlist_service_clean.py
```
**Structure Decision**: Modifying existing service files to introduce pagination and duplicate cleanup.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
