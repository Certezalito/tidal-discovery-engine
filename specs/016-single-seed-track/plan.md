# Implementation Plan: Dedicated Radio CLI Command

**Branch**: `016-single-seed-track` | **Date**: 2026-09-03 | **Spec**: [specs/016-single-seed-track/spec.md](spec.md)

**Input**: Feature specification from `specs/016-single-seed-track/spec.md`

## Summary

Extract the single-seed track recommendation mode (Mode 3) from the overloaded `recommend` command into a dedicated, highly ergonomic CLI command: `radio`. Refactor the existing single-seed pipeline in `src/cli/main.py` into a dedicated runner function (`generate_track_radio`), allowing the new `radio` command to execute it with streamlined options (optional `--playlist-name` defaulting to `"{artist} - {track} Radio"`, `--num-tracks` defaulting to 50). Remove the legacy `--artist` and `--track` options completely from `recommend`, establishing a clean separation of concerns where `recommend` is dedicated solely to library favorites discovery and `radio` is dedicated to single-seed discovery. Do not support the `track-radio` alias. In user documentation, present commands and parameter tables in the order: `recommend`, `radio`, `genre-playlist`. Ensure the resolved seed track is inserted as Track #1 in the playlist followed by recommendations, seed track provenance is preserved in playlist description metadata, catalog resolution strictly adheres to Principle VIII (Zero ISRC Hallucination), and the CLI interface adheres to Principle IX (CLI Ergonomics).

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `click` (CLI framework), `tidalapi` (streaming integration), `pylast` (Last.fm similarity), `google-genai` (AI recommendations), `uv` (dependency & environment management)  
**Storage**: File-based session persistence (`tidal_session.json`); SQLite (`genre_cache.db`) for caching  
**Testing**: `pytest`, `unittest`, `click.testing.CliRunner`  
**Target Platform**: Linux / macOS CLI  
**Project Type**: CLI tool  
**Performance Goals**: Playlist generation and creation under 30 seconds for standard recommendation counts (up to 50 tracks)  
**Constraints**:
- Principle VIII: Grounded Metadata & Zero ISRC Hallucination (AI prompts must never request or produce ISRCs; track resolution relies exclusively on text search).
- Principle IX: CLI Ergonomics & Friction Reduction (sensible defaults for optional playlist name and track count; clear error guidance; unambiguous single-purpose commands).
- Tidal API: Playlist description capped at 500 characters.
- Strict positive integers for track counts.  
**Scale/Scope**: Single-seed track queries, retrieving 50–150 candidate recommendations and inserting up to 50 tracks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Quality Gate | Compliance Status | Assessment & Mitigations |
|---|---|---|
| **I. User-Centricity & Understandability** | PASS | Documentation in `README.md` ordered logically (`recommend` -> `radio` -> `genre-playlist`), with each command clearly scoped and documented with concrete examples. |
| **II. Automation** | PASS | Operates fully unattended once invoked; suitable for scripts and scheduler usage. |
| **III. Personalization** | PASS | Starts with the seed track, tailors discovery to the seed, and supports `--exclude-favorites` to avoid library duplicates. |
| **IV. Extensibility** | PASS | Reusable single-seed execution pipeline, completely decoupled from library-sampling flow. |
| **V. Reliability & Verifiability** | PASS | Gracefully handles unresolvable tracks with capped previews; comprehensive automated tests in `tests/test_cli.py`. |
| **VI. AI Cost & Token Efficiency** | PASS | Prompts restrict AI generation strictly to artist and title strings, avoiding extraneous tokens. |
| **VII. Local Caching & Performance Efficiency** | PASS | Reuses existing cached sessions and network connections. |
| **VIII. Grounded Metadata & Zero ISRC Hallucination** | PASS | AI models are never queried for ISRCs; catalog resolution relies exclusively on authoritative string search. |
| **IX. CLI Ergonomics & Friction Reduction** | PASS | Short command `radio` with sensible defaults (50 tracks, automatic naming); clean removal of legacy flags from `recommend` eliminates command confusion; seed track placed at Track #1. |
| **Quality Gate: Validation** | PASS | Targeted automated unit/CLI tests covering argument validation, default naming, Gemini fallback, and strict command separation. |
| **Quality Gate: Documentation** | PASS | README updated with command order: `recommend` -> `radio` -> `genre-playlist`. |

## Project Structure

### Documentation (this feature)

```text
specs/016-single-seed-track/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-contract.md  # CLI interface specification
└── checklists/
    └── requirements.md  # Quality verification checklist
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py          # Adds `radio` command, removes single-seed flags from `recommend`
├── services/
│   ├── tidal_service.py # Seed track resolution, description formatting, and playlist creation
│   ├── gemini_service.py# AI recommendation generation
│   └── lastfm_service.py# Last.fm similarity retrieval
└── lib/
    └── logging.py       # Stable warning codes (e.g. RADIO_UNRESOLVED_TRACKS, SEED_NOT_RESOLVED_ON_TIDAL)

tests/
└── test_cli.py          # Unit & CLI runner tests for radio, defaults, Track #1, and recommend isolation
```

**Structure Decision**: Standard single-project CLI layout within `src/cli/` and `src/services/`. Single-seed orchestration logic resides in a dedicated runner in `src/cli/main.py`. `recommend` contains only library-discovery logic.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(No violations. Clean extraction and separation of existing functionality adhering directly to constitutional principles).*
