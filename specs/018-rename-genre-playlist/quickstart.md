# Quickstart & Verification Guide: Genre Organizer

**Feature**: `specs/018-rename-genre-playlist/spec.md`  
**Branch**: `018-rename-genre-playlist`  
**Date**: 2026-09-10  

This guide provides step-by-step commands to manually and automatically verify all aspects of the renamed genre organizer feature.

---

## Prerequisites

Ensure dependencies are installed and the environment is active:

```bash
# Ensure virtual environment and dependencies are synchronized
uv sync
source .venv/bin/activate
```

---

## Verification Scenarios

### 1. Verify Top-Level CLI Help Listing

Run top-level CLI help to ensure new commands are discoverable and the retired command is hidden:

```bash
python -m src.cli.main --help
```

**Expected Outcome:**
- `organize` appears under `Commands:`.
- `genre-organizer` appears under `Commands:`.
- `genre-playlist` is **NOT** present in the listing.

---

### 2. Verify Command Help & Options

Check help text and default parameters for both `organize` and `genre-organizer`:

```bash
python -m src.cli.main organize --help
python -m src.cli.main genre-organizer --help
```

**Expected Outcome:**
- Both display:
  - `--folder TEXT` (default: `"Genres"`)
  - `--min-genre-size INTEGER` (default: `10`)
  - `--db-path PATH` (default: `"data/genre_cache.db"`)

---

### 3. Verify Retired Command Guidance (`genre-playlist`)

Test invoking the retired command name with and without flags:

```bash
# Invocation without arguments
python -m src.cli.main genre-playlist

# Invocation with legacy options
python -m src.cli.main genre-playlist --folder "Old Genres" --min-genre-size 5
```

**Expected Outcome:**
- Exit code: `1`
- Output on stderr:
  ```text
  Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').
  ```

---

### 4. Verify Automated Test Suite

Run the renamed and updated unit and integration tests:

```bash
pytest tests/test_cli_genre_organizer.py tests/test_cli.py -v
```

**Expected Outcome:**
- All tests pass with 100% success rate and zero warnings.

---

### 5. Verify Full Pipeline Execution (Manual / Staging)

With valid Tidal credentials and `GEMINI_API_KEY` configured:

```bash
python -m src.cli.main organize --folder "Test Genres" --min-genre-size 5
```

**Expected Outcome:**
- Tracks are scanned and categorized.
- Summaries display cache hits and playlist counts.
- Tidal folder `Test Genres` contains the updated genre playlists.
