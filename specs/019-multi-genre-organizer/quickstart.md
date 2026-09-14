# Quickstart & Validation Guide: Multi-Genre Track Organization & Folder Wipe

**Feature**: `019-multi-genre-organizer`

This guide outlines runnable scenarios to validate multi-genre classification, caching, multi-playlist synchronization, and folder wiping features.

---

## 1. Prerequisites & Environment

Ensure project dependencies are installed and test environment variables are loaded:
```bash
# Verify virtual environment
./.venv/bin/python --version

# Verify API keys exist
./.venv/bin/python -c "from dotenv import dotenv_values; v = dotenv_values('.env'); assert 'GEMINI_API_KEY' in v"
```

---

## 2. Automated Test Execution

Run the targeted pytest test suite to verify database migrations, Gemini response parsing, multi-genre distribution, and folder wipe behaviors:

```bash
# Run cache service unit tests (schema migration + sub_genres storage)
./.venv/bin/pytest tests/test_genre_cache_service.py -v

# Run genre organizer service tests (multi-playlist placement, min-genre-size 5, folder wipe)
./.venv/bin/pytest tests/test_genre_playlist_service.py -v

# Run CLI command tests (flags, confirmation prompts, --wipe-folder, --wipe-only)
./.venv/bin/pytest tests/test_cli_genre_organizer.py -v
```

---

## 3. End-to-End Validation Scenarios

### Scenario A: Verify Gemini Schema & Sub-Genre Extraction
Directly test Gemini's classification with the updated primary + sub-genre schema:
```bash
./.venv/bin/python -c "
from src.services.gemini_service import classify_tracks_genres
from dotenv import dotenv_values
api_key = dotenv_values('.env')['GEMINI_API_KEY']
tracks = [{'artist': 'Foals', 'title': 'Tron', 'isrc': 'GBVKZ0725315'}]
results = classify_tracks_genres(api_key, tracks)
print('Primary Genre:', results[0].get('primary_genre'))
print('Sub-Genres:', results[0].get('sub_genres'))
assert len(results[0].get('sub_genres', [])) > 0, 'Should return at least 1 sub-genre'
"
```
**Expected Outcome**: Returns a primary genre (e.g., `Math Rock`) and a list of specific sub-genres (e.g., `['Dance-Punk', 'Post-Punk Revival']`) without broad categories like `Rock` or `Pop`.

---

### Scenario B: Verify Database Cache Persistence
Check that the SQLite cache persists both primary and sub-genres:
```bash
./.venv/bin/python -c "
from src.services.genre_cache_service import GenreCacheService
cache = GenreCacheService()
# Test save
cache.save_track_genres([{
    'track_id': 'test:1',
    'artist': 'Foals',
    'title': 'Tron',
    'primary_genre': 'Math Rock',
    'sub_genres': ['Dance-Punk', 'Post-Punk Revival'],
    'status': 'CLASSIFIED'
}])
# Test retrieve
cached = cache.get_cached_genres(['test:1'])
print('Retrieved from DB:', cached.get('test:1'))
assert cached['test:1']['primary_genre'] == 'Math Rock'
assert 'Dance-Punk' in cached['test:1']['sub_genres']
"
```
**Expected Outcome**: Primary genre and sub-genres are properly serialized to and retrieved from `data/genre_cache.db`.

---

### Scenario C: Dry-Run Playlist Generation with `--refresh-genres`
Run the CLI in dry-run mode to verify that tracks are mapped across all qualifying playlists:
```bash
./.venv/bin/python -m src.cli.main organize --limit 10 --dry-run --refresh-genres
```
**Expected Outcome**: 
1. Log indicates `--refresh-genres` is active.
2. Tracks are grouped into their primary genre playlist as well as each of their sub-genre playlists.
3. Summary displays created primary and sub-genre playlists.

---

### Scenario D: Folder Wipe-and-Resync with `--wipe-folder --yes`
Run organize with `--wipe-folder` and `--yes` to wipe existing playlists and rebuild fresh genre playlists:
```bash
./.venv/bin/python -m src.cli.main organize --folder "Test_Genres" --wipe-folder --yes
```
**Expected Outcome**:
1. Locates or creates folder `"Test_Genres"`.
2. Deletes all pre-existing playlists inside `"Test_Genres"` without prompting.
3. Generates fresh genre playlists according to the 5-track threshold.
4. Summary reports `Playlists Wiped:` and prints the direct folder URL link.

---

### Scenario E: Standalone Wipe-Only with `--wipe-only --yes`
Run organize with `--wipe-only` and `--yes` to empty the folder without creating new playlists:
```bash
./.venv/bin/python -m src.cli.main organize --folder "Test_Genres" --wipe-only --yes
```
**Expected Outcome**:
1. Deletes all playlists inside `"Test_Genres"`.
2. Exits immediately without querying Gemini or generating new playlists.
3. Reports `Playlists Wiped:` and prints the folder URL link.
