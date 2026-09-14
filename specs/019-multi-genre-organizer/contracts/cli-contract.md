# CLI Contract: `organize` Command

## Command Synopsis

```bash
python -m src.cli.main organize [OPTIONS]
# or via alias
python -m src.cli.main genre-organizer [OPTIONS]
```

### Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--min-genre-size` | Integer | `5` | Minimum track count required for a genre or sub-genre playlist. Smaller primary genres are grouped into 'Others'; smaller sub-genres are suppressed. |
| `--folder` | Text | `Genres` | Destination Tidal playlist folder name. |
| `--limit` | Integer | `None` | Maximum number of favorite tracks to process (useful for testing/dry-runs). |
| `--refresh-genres` | Boolean Flag | `False` | Force re-classification of existing cached tracks to discover and backfill sub-genres from Gemini. |
| `--wipe-folder`, `--wipe` | Boolean Flag | `False` | Delete all existing playlists inside the target folder before synchronizing new playlists. |
| `--wipe-only` | Boolean Flag | `False` | Delete all existing playlists inside the target folder and terminate immediately without synchronizing new playlists. |
| `--yes`, `-y` | Boolean Flag | `False` | Skip interactive confirmation prompt when wiping playlists. |
| `--dry-run` | Boolean Flag | `False` | Run classification and playlist diff calculations without making actual changes to Tidal playlists. |
| `--help` | Flag | - | Show help message and exit. |

---

## Interactive Confirmation Contract

When `--wipe-folder` or `--wipe-only` is provided in an interactive terminal session without `--yes` / `-y`:
```text
Are you sure you want to delete all 5 playlists in folder 'Genres'? [y/N]: 
```
- If the user responds with `y` or `yes` (case-insensitive), deletion proceeds.
- If the user responds with `n`, `no`, or presses enter, the command aborts cleanly with:
  ```text
  Aborted.
  ```

---

## Output Contract & Logs

### Standard Sync Invocation
```text
Loaded 124 tracks from local cache.
Found 12 new/unclassified tracks. Classifying with Gemini...
Batch 1/1: Classified 12 tracks. Saved to cache.

Genre Summary:
- Math Rock: 15 tracks (Primary)
- Dance-Punk: 6 tracks (Sub-genre)
- Post-Punk Revival: 8 tracks (Sub-genre)
- Indie Rock: 22 tracks (Primary)
- Others: 14 tracks (consolidated primary genres < 5 tracks)
- Suppressed: 3 sub-genres (< 5 tracks) omitted from playlist creation

Synchronizing Tidal Playlists in folder 'Genres'...
[1/5] Synced 'Dance-Punk' (6 tracks: +6, -0)
[2/5] Synced 'Post-Punk Revival' (8 tracks: +8, -0)
[3/5] Synced 'Others' (14 tracks: +14, -0)
[4/5] Synced 'Math Rock' (15 tracks: +15, -0)
[5/5] Synced 'Indie Rock' (22 tracks: +22, -0)

Complete! 5 playlists synchronized.
Folder URL: https://tidal.com/browse/folder/abcd-1234
View folder 'Genres' here: https://tidal.com/browse/folder/abcd-1234
```

### With `--wipe-folder` (Wipe and Sync)
```text
Wiping existing playlists in folder 'Genres'...
Deleted playlist 'Old Math Rock' (id: 1111)
Deleted playlist 'Old Dance-Punk' (id: 2222)
Wiped 2 existing playlists in folder 'Genres'.

Synchronizing Tidal Playlists in folder 'Genres'...
[1/4] Synced 'Dance-Punk' (6 tracks: +6, -0)
...

==================================================
Genre Organizer Sync Complete
Tracks Processed:       124
Cached Tracks:          124
New Classified:         0
Primary Genres:         2
Sub-Genres:             2
Playlists Created:      4
Playlists Updated:      0
Playlists Deleted:      0
Playlists Wiped:        2
Folder URL:             https://tidal.com/browse/folder/abcd-1234
==================================================

View folder 'Genres' here: https://tidal.com/browse/folder/abcd-1234
```

### With `--wipe-only`
```text
Wiping existing playlists in folder 'Genres'...
Deleted playlist 'Math Rock' (id: 1111)
Deleted playlist 'Dance-Punk' (id: 2222)

==================================================
Genre Organizer Sync Complete
Playlists Wiped:        2
Folder URL:             https://tidal.com/browse/folder/abcd-1234
==================================================

Folder 'Genres' wiped clean.
View folder 'Genres' here: https://tidal.com/browse/folder/abcd-1234
```
