# Quickstart Validation Guide: Genre Playlist Database Caching & Optimization

## Prerequisites

1. Set up virtual environment and install dependencies:
   ```bash
   uv venv && uv pip install -e .
   ```
2. Ensure valid Tidal session (`tidal_session.json`) and `GEMINI_API_KEY` in `.env`.

---

## Scenario 1: Initial Library Classification & Database Cache Population

**Goal**: Verify that the command builds a local SQLite cache database on the initial run.

**Run Command**:
```bash
uv run python -m src.cli.main genre-playlist --folder "Test Genres" --min-genre-size 5
```

**Expected Outcome**:
- Command queries Gemini for uncached library tracks.
- Creates/populates SQLite database at `data/genre_cache.db`.
- Creates playlists in Tidal folder "Test Genres".
- Genres with < 5 tracks are grouped into "Others".

---

## Scenario 2: Repeat Execution (100% Database Cache Hit Rate)

**Goal**: Verify that repeat execution reads strictly from the database cache and incurs zero Gemini token cost.

**Run Command**:
```bash
uv run python -m src.cli.main genre-playlist --folder "Test Genres" --min-genre-size 5
```

**Expected Outcome**:
- Output displays: `100% cached (hits)`, `0 uncached/unknown (misses)`.
- Zero Gemini API calls made.
- Execution finishes in seconds.

---

## Scenario 3: Changing Minimum Genre Threshold

**Goal**: Verify thresholding dynamically adjusts playlists without corrupting track assignments.

**Run Command**:
```bash
uv run python -m src.cli.main genre-playlist --folder "Test Genres" --min-genre-size 2
```

**Expected Outcome**:
- Genres previously grouped in "Others" that now meet threshold 2 are split out into their own dedicated genre playlists.
- Database cache is reused (0 Gemini calls).
- Playlists in Tidal folder are synchronized accordingly.
