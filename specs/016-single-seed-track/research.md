# Phase 0 Research: Dedicated Radio CLI Command

## Overview
This document records technical investigations, design decisions, and architectural patterns for establishing the single seed track recommendation flow as a dedicated, ergonomic CLI command (`radio`), cleanly separated from library discovery (`recommend`).

## Key Decisions

### Decision 1: CLI Command Naming & Interface
- **Decision**: Register `@cli.command("radio")` as the canonical command. Do NOT support the `track-radio` alias.
- **Rationale**: Per user direction and Principle IX (CLI Ergonomics & Friction Reduction), `radio` is concise, recognizable, and standard in music streaming platforms. Removing the alias eliminates unnecessary command surface area and cognitive clutter.
- **Alternatives Considered**:
  - *Retaining `track-radio` alias*: Rejected per user request to keep the CLI clean and minimal.
  - *Nested subcommands (e.g. `recommend track`)*: Adds unnecessary keystrokes and verbosity.

### Decision 2: Separation of Concerns & Removal of Legacy Single-Seed Flags
- **Decision**: Completely remove `--artist` and `--track` from the `recommend` command rather than maintaining a deprecation period.
- **Rationale**: Clean command boundaries: `recommend` is strictly responsible for library-favorite-based playlist generation, while `radio` is strictly responsible for single-seed track discovery. Removing the legacy flags prevents parameter confusion and avoids maintaining dead delegation paths.
- **Alternatives Considered**:
  - *Retaining legacy flags on `recommend` with deprecation warnings*: Rejected per user preference ("also i dont need the legacy single seed flag").

### Decision 3: Default Playlist Naming and Dynamic Date Tokens
- **Decision**: Make `--playlist-name` optional in `radio`, defaulting to `f"{artist} - {track} Radio"`. Support `{date}` token replacement formatting `datetime.date.today().strftime("%Y%m%d")` in both defaulted and user-supplied names.
- **Rationale**: Implements Principle IX (CLI Ergonomics & Friction Reduction). Users can spontaneously launch a radio station with minimal typing (`uv run python -m src.cli.main radio --artist "Underworld" --track "Born Slippy"`), while preserving full custom naming flexibility.
- **Alternatives Considered**:
  - *Strictly required `--playlist-name`*: Imposes needless friction on spontaneous exploration.
  - *Generic default like `"Track Radio"`*: Loses musical context in the Tidal library; `"{artist} - {track} Radio"` provides immediate context.

### Decision 4: Seed Track Placement (Track #1) & Description Metadata
- **Decision**: The resolved seed track is placed at Track #1 in the generated playlist, followed by recommendations up to the total requested count (`num_tracks - 1` recommendations). Playlist description metadata includes: `"Seed track: {track} by {artist} • Total tracks: {total_count}"`, safely truncated to 500 characters for Tidal API compliance.
- **Rationale**: Placing the seed song at the start gives immediate auditory confirmation of the station anchor before moving into discovery. Preserving seed metadata in the description guarantees permanent provenance in the streaming UI.
- **Alternatives Considered**:
  - *Omit seed track from playlist items*: Rejected per user instruction ("make the seed track track #1").
  - *Append seed track at the end*: Defeats anchor function; listeners expect the seed at the beginning.

### Decision 5: Total Track Count Parameter & Default (50 Tracks)
- **Decision**: Standardize on `--num-tracks` as the primary flag with a default of 50 tracks (1 seed track + 49 recommendations), while accepting `--num-similar-tracks` as a backward-compatible alias.
- **Rationale**: Defaulting to 50 tracks ensures volume parity with the legacy recommendation experience, giving listeners a full playlist.
- **Alternatives Considered**:
  - *20 tracks default*: Too brief for extended listening sessions.
  - *Exclude seed track from the count*: Calculating total playlist size as 1 seed + (N - 1) recs keeps the final playlist size exactly equal to `--num-tracks`.

### Decision 6: Documentation Hierarchy in README
- **Decision**: In `README.md` and documentation guides, commands and option parameter tables must be presented in the exact sequence:
  1. `recommend` (library discovery)
  2. `radio` (single-seed discovery)
  3. `genre-playlist` (genre-based discovery)
- **Rationale**: User explicitly specified this ordering to maintain a logical progression from core library discovery to track radio to genre stations.
