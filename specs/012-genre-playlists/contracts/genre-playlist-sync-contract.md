# Genre Playlist Sync Contract

## Purpose

Define expected CLI and service behavior for building and maintaining genre playlists from a full Tidal library using Gemini classification.

## Contract

### Input Contract

- User provides a destination folder name.
- Workflow reads the complete library (paged retrieval).
- Genre classification source is Gemini.

### Classification Contract

- Each track is classified into exactly one "best match" genre.
- When a track has a successful classification, it must be stored in the local cache.
- When no usable genre is returned, the track must be assigned to `Unknown`.
- Tracks assigned to `Unknown` must NOT be stored in the local cache, ensuring they are re-checked on subsequent runs.

### Folder/Playlist Contract

- If destination folder does not exist, create it.
- After classification, genres containing fewer tracks than the configured threshold (default 2) must be grouped into an `Others` playlist.
- For every discovered genre that meets the threshold (plus `Unknown` and `Others` when needed), create or resolve a playlist in that folder.
- Playlist naming must be deterministic for repeated runs.

### Sync Contract

For each genre playlist on rerun:

- Playlist creation and sync operations must be executed in ascending order of their desired track count.
- `to_add = desired_membership - existing_membership`
- `to_remove = existing_membership - desired_membership`
- Apply both sets so final membership matches desired state.
- Duplicate entries must not be introduced.

### Progress and Outcome Contract

CLI output must include:

- Number of library tracks processed
- Number of playlists created/updated
- Number of tracks added/removed
- Count of tracks sent to `Unknown`

### Failure Contract

- If library retrieval fails: stop and return actionable error.
- If Gemini classification fails for a subset: continue when possible and route unresolved tracks to `Unknown` unless failure is total.
- If playlist mutation fails for a playlist: log clear playlist-specific error and fail run unless explicitly configured for partial success (not in scope for this feature).
