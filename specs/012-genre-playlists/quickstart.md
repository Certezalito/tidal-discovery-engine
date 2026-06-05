# Quickstart: Genre Playlists

## What This Feature Delivers

A CLI workflow that:

- Reads your full Tidal library
- Uses Gemini to classify tracks into genres
- Creates/uses a target folder
- Creates genre playlists (plus `Unknown` when needed)
- Syncs playlists on rerun (add new, remove stale)

## Prerequisites

- Valid Tidal authentication/session
- `GEMINI_API_KEY` configured
- Project dependencies installed via `uv`

## Run Scenario 1: First Genre Build

1. Execute the genre-playlist command with your desired folder name (or use the default "Genres"):
   ```bash
   uv run python -m src.cli.main genre-playlist
   # Or with a custom folder:
   uv run python -m src.cli.main genre-playlist --folder "My Music Styles"
   ```
2. Confirm the run reports library scan progress.
3. Verify folder creation and multiple genre playlists appear.
4. Verify tracks with no usable genre appear in `Unknown`.

Expected outcome:

- Folder exists.
- Genre playlists are created.
- Membership reflects current library classification.

## Run Scenario 2: Sync on Rerun

1. Add and remove a few tracks in Tidal library.
2. Re-run the same genre-playlist command against the same folder.
3. Check progress summary for `tracks_added` and `tracks_removed`.

Expected outcome:

- Existing playlists are updated, not duplicated.
- Removed source tracks are removed from affected genre playlists.
- New source tracks are inserted in matching genre playlists.

## Validation Checklist

- Full library was scanned (not a partial subset)
- Multi-genre tracks appear in multiple genre playlists
- Unknown classifications appear in `Unknown`
- No duplicate playlists created on rerun
- Sync operation reflects current library state

## References

- Data model: [data-model.md](data-model.md)
- Sync behavior contract: [contracts/genre-playlist-sync-contract.md](contracts/genre-playlist-sync-contract.md)
