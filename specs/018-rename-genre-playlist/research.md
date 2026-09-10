# Research: Rename Genre Playlist Command to Genre Organizer

**Feature**: `specs/018-rename-genre-playlist/spec.md`  
**Branch**: `018-rename-genre-playlist`  
**Date**: 2026-09-10  

## Overview

This research document analyzes the technical approaches, decisions, and patterns needed to rename the `genre-playlist` CLI command to `organize` (with alias `genre-organizer`), intercept legacy invocations with a hidden stub, refactor the supporting service and test modules, and update end-user documentation.

---

## Findings & Decisions

### 1. Click CLI Command Aliasing Pattern

- **Decision**: Define a shared execution function `_execute_genre_organizer(folder, min_genre_size, db_path)` in `src/cli/main.py`. Define `@cli.command("organize")` as the primary command, and define `@cli.command("genre-organizer")` as an alias that forwards directly to the same shared logic with identical options and docstrings.
- **Rationale**: Click does not provide an `@alias` decorator natively on `click.Group` without custom group subclasses or external plugins like `click-aliases`. Defining two standard `@cli.command` definitions pointing to the shared implementation logic uses 100% standard Click, requires zero extra runtime dependencies, and allows both names to appear in CLI help documentation and accept identical option parameters.
- **Alternatives Considered**:
  - *Custom `AliasedGroup(click.Group)` subclass*: Overrides `get_command` to resolve prefix or alias names dynamically. Rejected because it introduces unnecessary metaclass/dispatch complexity when only one specific command needs an alias.
  - *`click-aliases` third-party library*: Rejected to avoid adding external runtime dependencies for a straightforward 2-command mapping.

### 2. Legacy Command Interception (`genre-playlist`)

- **Decision**: Implement `@cli.command("genre-playlist", hidden=True, context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))` that raises `click.ClickException("Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').")`.
- **Rationale**: 
  - Using `hidden=True` ensures that `genre-playlist` is completely omitted from `--help` listings.
  - Using `ignore_unknown_options=True` and `allow_extra_args=True` ensures that if a user or script passes legacy flags (e.g. `genre-playlist --folder "Custom" --min-genre-size 5`), Click does not abort with an unhandled option error before our command function can run; instead, it enters the command stub and immediately prints the exact migration error message.
  - `click.ClickException` automatically formats output to stderr with exit code 1, fulfilling requirement `FR-004` and `SC-003`.
- **Alternatives Considered**:
  - *Complete removal without stub*: Clicking returns standard `Error: No such command 'genre-playlist'`. Rejected because the user specifically requested actionable guidance to ease migration for existing scripts and muscle memory.
  - *Custom Click error handler*: Catches `UsageError` on unknown commands. Rejected because it risks misinterpreting typos for other commands.

### 3. Service Module and Function Refactoring Scope

- **Decision**:
  - Rename `src/services/genre_playlist_service.py` to `src/services/genre_organizer_service.py`.
  - Rename `run_genre_playlist_sync` to `run_genre_organizer_sync`.
  - Provide a lightweight backward-compatibility shim in `src/services/genre_playlist_service.py` that re-exports `run_genre_organizer_sync` as `run_genre_playlist_sync` with a deprecation warning, while updating all internal repository callers (`src/cli/main.py` and test files) to import directly from `src/services/genre_organizer_service.py`.
  - Rename `tests/test_cli_genre_playlist.py` to `tests/test_cli_genre_organizer.py` and update `tests/test_cli.py`.
- **Rationale**: Satisfies the user's choice (Q3 Option A) for a comprehensive codebase rename while preventing breaking changes in any external scripts that might import the Python service module directly.
- **Alternatives Considered**:
  - *Hard deletion of `genre_playlist_service.py` without shim*: Could break any downstream Python scripts importing the module. The lightweight shim provides defensive hygiene at zero cost.

### 4. Cache & Data Compatibility

- **Decision**: Retain default cache location at `data/genre_cache.db`.
- **Rationale**: Preserves cached track classifications for users running the updated command on an existing installation. Re-categorizing thousands of tracks with Gemini would waste AI tokens and incur unnecessary execution latency, violating Constitution Principle VI (AI Cost & Token Efficiency) and Principle VII (Local Caching).
- **Alternatives Considered**:
  - *Rename cache file to `data/genre_organizer_cache.db`*: Would discard existing caches unless an automatic file migration/copy was implemented. Unnecessary churn for an internal SQLite file.

### 5. Constitution Principle IX & CLI Ergonomics

- **Decision**:
  - Primary command `organize` (8 characters, single-word verb matching `radio` and `recommend`).
  - Alias `genre-organizer` (15 characters, descriptive kebab-case).
  - All options retain sensible defaults (`--folder "Genres"`, `--min-genre-size 10`, `--db-path "data/genre_cache.db"`).
- **Rationale**: Fully compliant with Principle IX: commands provide short, memorable names alongside descriptive aliases with sensible defaults and zero mandatory flags.

