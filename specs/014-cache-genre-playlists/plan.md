# Implementation Plan: Genre Playlist Database Caching & Optimization

**Branch**: `014-cache-genre-playlists` | **Date**: 2026-07-23 | **Spec**: [specs/014-cache-genre-playlists/spec.md](specs/014-cache-genre-playlists/spec.md)

**Input**: Feature specification from `specs/014-cache-genre-playlists/spec.md`

## Summary

Optimize the `genre-playlist` CLI command by introducing a persistent local SQLite database cache for Gemini track genre classifications, establishing a configurable minimum track threshold (`--min-genre-size`) for obscure genre grouping into an "Others" playlist, and implementing idempotent Tidal playlist folder synchronization.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: `sqlite3` (standard library), `click`, `google-genai`, `tidalapi`

**Storage**: SQLite local database (`data/genre_cache.db`)

**Testing**: `pytest`

**Target Platform**: CLI application (macOS/Linux/Windows)

**Project Type**: CLI Application

**Performance Goals**: < 20% execution time on repeat cached runs vs initial un-cached run; 100% cache hits on unchanged library.

**Constraints**: Zero duplicate tracks across playlists; handle rate limits gracefully; unattended execution support.

**Scale/Scope**: Libraries up to 10,000+ tracks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. User-Centricity & Understandability**: PASS (simple CLI flags `--min-genre-size` and clear progress/cost reporting).
- **II. Automation**: PASS (unattended scheduled execution safe).
- **V. Reliability & Verifiability**: PASS (SQLite transaction safety, fallback logic, pytest coverage).
- **VI. AI Cost & Token Efficiency**: PASS (caches Gemini responses, zero token calls on cached hits).
- **VII. Local Caching & Performance Efficiency**: PASS (SQLite database persistence for track genres with "Unknown" re-evaluation).

## Project Structure

### Documentation (this feature)

```text
specs/014-cache-genre-playlists/
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # SQLite schema & state transitions
├── quickstart.md        # Validation scenarios
└── contracts/
    └── genre-playlist-cli-contract.md # CLI contract
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py          # Updated CLI options (--min-genre-size, --db-path)
├── services/
│   ├── genre_cache_service.py   # SQLite database cache management
│   ├── gemini_service.py        # Gemini genre classification
│   └── genre_playlist_service.py# Genre grouping & folder sync logic
└── lib/
    └── db.py                    # SQLite helper connection/migration utilities

tests/
├── test_genre_cache_service.py  # SQLite cache unit tests
├── test_genre_playlist_service.py# Grouping, thresholding & sync tests
└── test_cli.py                  # CLI integration tests
```

```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
