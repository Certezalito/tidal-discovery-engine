# Implementation Plan: Multi-Genre Track Organization & Folder Wipe

**Branch**: `019-multi-genre-organizer` | **Date**: 2026-09-10 (Revised: 2026-09-14) | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/019-multi-genre-organizer/spec.md`

## Summary

Enhance the `organize` command (and `genre-organizer` alias) to:
1. Extract both a primary genre and up to 3 specific sub-genres (excluding broad umbrella categories) from Gemini, persist them in local SQLite cache (`data/genre_cache.db`), and populate tracks across both their primary genre playlist and qualifying sub-genre playlists in Tidal.
2. Enforce a default minimum genre size of 5 tracks (`--min-genre-size 5`), grouping smaller primary genres into "Others" and suppressing smaller sub-genres from standalone playlist creation.
3. Provide an opt-in folder wipe capability (`--wipe-folder` / `--wipe` and `--wipe-only` with `--yes` / `-y` override) that deletes all existing playlists inside the designated Tidal folder.
4. Keep the destination folder container intact to preserve the persistent Tidal folder URL link (`https://tidal.com/browse/folder/{folder_id}`) without requiring folder recreation or colliding with Tidal's backend constraint that non-empty folders cannot be removed.

---

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `click`, `google-genai`, `pydantic`, `tidalapi`, `sqlite3`  
**Storage**: SQLite (`data/genre_cache.db`, table `track_genre_cache`)  
**Testing**: `pytest` (`tests/test_genre_cache_service.py`, `tests/test_genre_playlist_service.py`, `tests/test_cli_genre_organizer.py`)  
**Target Platform**: Linux server / macOS / Windows CLI  
**Project Type**: CLI tool & service library  
**Performance Goals**: 
- Zero redundant AI calls on cached tracks; batched Gemini requests (50 songs per call); bounded sub-genres (max 3).
- Fast and reliable folder wiping: individually deletes playlists inside the target folder via `delete_playlist(session, pl.id)` and reuses the empty folder container, eliminating folder deletion/re-creation lag and preserving folder URLs.  
**Constraints**: 
- Comply with Constitution Principles I, II, V, VI, VII, VIII, and IX.
- Tidal API constraint: Folders cannot be deleted directly while containing playlists; playlists inside the folder must be deleted individually.
- Deletions must be strictly bounded to the target folder, never affecting root or other folders.  
**Scale/Scope**: Scales to personal Tidal libraries containing thousands of tracks and folders with dozens of genre playlists.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Quality Gate | Compliance Strategy | Status |
| :--- | :--- | :---: |
| **Principle I: User-Centricity & Understandability** | Clear CLI options (`--wipe-folder`, `--wipe-only`, `--yes`), documented in `--help`, README, and contract with examples. | **PASS** |
| **Principle II: Automation** | Complete batch synchronization runs unattended; `--yes` / `-y` enables non-interactive scheduled/cron execution. | **PASS** |
| **Principle III: Personalization** | Leverages favorite tracks and user library to create deep, multi-tier playlists. | **PASS** |
| **Principle IV: Extensibility** | Modular service contracts separating Gemini classification, caching, and Tidal folder sync/wipe operations. | **PASS** |
| **Principle V: Reliability & Verifiability** | Safe bounded deletion (target folder only); error logging for failed API playlist deletions; comprehensive unit/CLI tests. | **PASS** |
| **Principle VI: AI Cost & Token Efficiency** | Prompt forbids broad categories; bounded sub-genres (max 3); `--wipe-only` skips AI completely. | **PASS** |
| **Principle VII: Local Caching & Performance** | Sub-genres stored in SQLite; `--refresh-genres` avoids unwanted token re-queries. | **PASS** |
| **Principle VIII: Grounded Metadata & Zero ISRC** | No AI-generated ISRCs; track resolution relies purely on catalog metadata and library IDs. | **PASS** |
| **Principle IX: CLI Ergonomics & Sensible Defaults** | Sensible defaults (`min-genre-size 5`, wipe is opt-in, `--wipe` alias, interactive confirmation with `-y`). | **PASS** |

---

## Project Structure

### Documentation (this feature)

```text
specs/019-multi-genre-organizer/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 research findings (GUI vs API folder deletion)
├── data-model.md        # Data model, schema migration & wipe models
├── quickstart.md        # End-to-end validation guide (including wipe scenarios)
├── contracts/           # Interface contracts
│   └── cli-contract.md  # CLI synopsis with --wipe-folder, --wipe-only, --yes
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py                               # CLI organize command with --wipe-folder, --wipe-only, --yes flags
├── services/
│   ├── gemini_service.py                     # GenreClassificationResult & prompt updates
│   ├── genre_cache_service.py                # sub_genres column handling & backfill query
│   └── genre_organizer_service.py            # Multi-playlist mapping, folder wiping logic & summary metrics
└── lib/
    └── db.py                                 # SQLite schema migration for sub_genres

tests/
├── test_cli_genre_organizer.py               # Tests for CLI flags, confirmation prompt, --wipe-folder & --wipe-only
├── test_genre_cache_service.py               # Tests for SQLite sub_genres persistence
└── test_genre_playlist_service.py            # Tests for multi-playlist distribution & folder wipe service logic
```

**Structure Decision**: Single modular Python project using standard `src/` and `tests/` directories.

---

## Complexity Tracking

> *No constitutional violations or unnecessary complexity detected.*
