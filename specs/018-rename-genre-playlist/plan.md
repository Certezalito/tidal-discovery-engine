# Implementation Plan: Rename Genre Playlist Command to Genre Organizer

**Branch**: `018-rename-genre-playlist` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/018-rename-genre-playlist/spec.md`

## Summary

This feature renames the `genre-playlist` CLI command to `organize` (providing `genre-organizer` as a supported descriptive alias), satisfying Constitution Principle IX (CLI Ergonomics & Friction Reduction) by matching the concise single-word pattern of `radio` and `recommend`. To prevent broken scripts or user confusion, a hidden `genre-playlist` command stub is implemented to cleanly exit with code 1 and display actionable migration guidance. In addition, internal service modules (`genre_organizer_service.py`), orchestration functions (`run_genre_organizer_sync`), automated test suites (`tests/test_cli_genre_organizer.py`), and project documentation (`README.md`) are comprehensively refactored to align with the new naming.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `click`, `uv` (dependency & environment manager)  
**Storage**: SQLite (`data/genre_cache.db` - cache path preserved for backward compatibility)  
**Testing**: `pytest`  
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)  
**Project Type**: Command-line application  
**Performance Goals**: Sub-second command dispatch and error guidance (<100ms); zero regression in library scanning or AI classification throughput  
**Constraints**: Must preserve existing SQLite cache without requiring re-classification; must maintain identical option flags (`--folder`, `--min-genre-size`, `--db-path`); must provide clear migration error on retired command  
**Scale/Scope**: 5 files affected across CLI, services, tests, and documentation  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (User-Centricity & Understandability)**: PASS - Usage instructions, option flags, and examples are updated in `README.md` and CLI `--help`.
- **Principle II (Automation)**: PASS - Workflows remain 100% automatable in cron/scripts with sensible defaults.
- **Principle III (Personalization)**: PASS - Existing user library categorization functionality is preserved.
- **Principle IV (Extensibility)**: PASS - Modular architecture is maintained with decoupled service functions.
- **Principle V (Reliability & Verifiability)**: PASS - Robust error handling and comprehensive automated tests in `tests/test_cli_genre_organizer.py` and `tests/test_cli.py`.
- **Principle VI (AI Cost & Token Efficiency)**: PASS - Reuses existing cache database, preventing redundant Gemini API calls.
- **Principle VII (Local Caching & Performance Efficiency)**: PASS - `data/genre_cache.db` is maintained as the default cache path.
- **Principle VIII (Grounded Metadata & Zero ISRC Hallucination)**: PASS - No changes to AI track resolution or metadata handling.
- **Principle IX (CLI Ergonomics & Friction Reduction)**: PASS - `organize` provides an 8-character single-word primary command matching `radio` and `recommend`; `genre-organizer` is supported as an alias; sensible defaults eliminate mandatory arguments.
- **Quality Gates**: PASS - All gates satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/018-rename-genre-playlist/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-contract.md  # CLI command interfaces & behavior contract
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py                     # [MODIFY] Register 'organize', 'genre-organizer', and hidden 'genre-playlist' stub
└── services/
    ├── genre_organizer_service.py   # [NEW] Renamed service module with run_genre_organizer_sync
    └── genre_playlist_service.py    # [MODIFY] Deprecation shim re-exporting run_genre_organizer_sync

tests/
├── test_cli_genre_organizer.py      # [NEW] Renamed from test_cli_genre_playlist.py and updated
└── test_cli.py                     # [MODIFY] Update existing tests to invoke 'organize' and patch new service

README.md                           # [MODIFY] Update documentation and command reference
```

**Structure Decision**: Standard single-project layout. The service module is migrated to `genre_organizer_service.py` with a lightweight backward-compatibility shim in `genre_playlist_service.py`. The CLI commands in `src/cli/main.py` route both `organize` and `genre-organizer` to `run_genre_organizer_sync`.

## Complexity Tracking

*No constitutional violations; no additional complexity tracking required.*
