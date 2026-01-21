# Quickstart: Update README Examples

This feature updates the main `README.md`. The new section to be added is:

## Organizing Playlists

You can organize your generated playlists into a specific folder using the `--folder` argument. If the folder doesn't exist, it will be created automatically.

**Example:**
```bash
uv run python -m src.cli.main --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}" --folder "My Discovery Mixes"
```
