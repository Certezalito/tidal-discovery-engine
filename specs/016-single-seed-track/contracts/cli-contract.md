# Phase 1 CLI Contract: Dedicated Radio Command

## 1. Primary Command: `radio`

### Signature
```bash
python -m src.cli.main radio [OPTIONS]
```

### Options

| Option Flag | Type | Required | Default | Description |
|---|---|---|---|---|
| `--artist` | `TEXT` | **Yes** | None | The artist of the seed track. Whitespace-trimmed. |
| `--track` | `TEXT` | **Yes** | None | The title of the seed track. Whitespace-trimmed. |
| `--playlist-name` | `TEXT` | No | `"{artist} - {track} Radio"` | Custom name for the new Tidal playlist. Supports `{date}` placeholder (`YYYYMMDD`). |
| `--num-tracks` | `INTEGER` | No | `50` | Desired total playlist track count (> 0). Default: 1 seed track + 49 recommendations = 50 tracks. |
| `--num-similar-tracks` | `INTEGER` | No | `50` | Backward-compatible alias for `--num-tracks`. |
| `--gemini` | `FLAG` | No | `False` | Use Google Gemini AI for recommendations instead of Last.fm. Requires `GEMINI_API_KEY`. |
| `--shuffle` | `FLAG` | No | `False` | Deep-cut underground discovery when combined with `--gemini`; shuffles track order when using Last.fm. |
| `--exclude-favorites`| `FLAG` | No | `False` | Exclude tracks already present in user's Tidal favorites library snapshot. |
| `--folder` | `TEXT` | No | `"Radio"` | Folder name to organize the generated playlist in Tidal (defaults to `"Radio"`). |

### Tracklist Ordering & Slicing
- **Track #1**: The resolved Tidal seed track matching `--artist` and `--track`.
- **Tracks #2–N**: Up to `num_tracks - 1` resolved recommended tracks (excluding any duplicate of the seed track), yielding exactly `num_tracks` total tracks in the created playlist.
- If the seed track cannot be resolved on Tidal catalog, the command logs an informative warning, fills the playlist with up to `num_tracks` recommendations, and notes the seed track in the playlist description metadata.

### Exit Codes
- `0`: Success — playlist created and tracks added.
- `1` / `2`: Error — input validation failure, missing credentials, API error, or zero tracks inserted.

### Standard Output & Logging
On success, the command prints:
```text
Playlist '<resolved_playlist_name>' created successfully!
View it here: https://tidal.com/browse/playlist/<playlist_id>
```

When partial tracks fail catalog resolution:
```text
WARNING [RADIO_UNRESOLVED_TRACKS]: One or more recommendations could not be matched on Tidal and were skipped. (skipped_count=N, preview=...)
```

When zero tracks can be added:
```text
ERROR [ZERO_TRACKS_INSERTED]: No tracks could be inserted into the playlist after recommendation resolution.
```

---

## 2. Command Separation: `recommend`

The `recommend` command is dedicated exclusively to library favorites discovery:
- Does NOT accept `--artist` or `--track`.
- If a user passes `--artist` or `--track` to `recommend`, Click rejects them with standard CLI error: `Error: No such option: --artist`.
- All single-seed track discovery MUST be invoked using the dedicated `radio` command.
