# Interface Contract: CLI `genre-playlist` Command

## Command Signature

```bash
uv run python -m src.cli.main genre-playlist [OPTIONS]
```

## Command Options

| Option | Type | Default | Description |
|---|---|---|---|
| `--folder` | TEXT | `"Genre Playlists"` | Tidal playlist folder name where genre playlists will be created/synced. |
| `--min-genre-size` | INT | `5` | Minimum number of tracks required for a genre to receive its own playlist. Genres below this threshold are grouped into "Others". |
| `--db-path` | PATH | `"data/genre_cache.db"` | Path to the local SQLite database cache. |
| `--force-reclassify` | FLAG | `False` | Optional flag to bypass cache and re-query Gemini for all tracks. |

## Expected Output Format

```text
Scanning Tidal library... Found 1,250 tracks.
Checking local database cache (data/genre_cache.db)...
Cache status: 1,180 cached (hits), 70 uncached/unknown (misses).

Querying Gemini for 70 uncached tracks...
Gemini processing complete. Saved 65 new classifications, 5 unknown.

Categorizing genres (min size: 5):
  - Rock: 320 tracks
  - Hip-Hop: 210 tracks
  - Electronic: 145 tracks
  - Jazz: 85 tracks
  - Others (12 obscure genres): 18 tracks
  - Unknown: 5 tracks

Synchronizing Tidal folder "Genre Playlists"...
  [1/5] Updating playlist "Others" (18 tracks)... Done.
  [2/5] Updating playlist "Jazz" (85 tracks)... Done.
  [3/5] Updating playlist "Electronic" (145 tracks)... Done.
  [4/5] Updating playlist "Hip-Hop" (210 tracks)... Done.
  [5/5] Updating playlist "Rock" (320 tracks)... Done.

Successfully synchronized 5 genre playlists in Tidal folder "Genre Playlists".
Token cost savings: ~94.4% reduction via local SQLite cache.
```
