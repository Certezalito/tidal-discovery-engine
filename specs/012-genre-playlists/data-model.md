# Data Model: Genre Playlists

## LibraryTrack

Represents a track loaded from the user’s Tidal library.

### Fields

- `track_id`: Tidal track identifier.
- `isrc`: Optional ISRC used for stable identity when available.
- `title`: Track title.
- `primary_artist`: Primary artist name.
- `identity_key`: Canonical comparison key (`isrc:*` when available, fallback text key otherwise).

### Notes

- `identity_key` is used for deduplication and playlist sync comparisons.

## GenreClassification

Represents the classification output from Gemini or the local cache for a single library track.

### Fields

- `identity_key`: Reference to `LibraryTrack.identity_key`.
- `genre`: Single normalized genre label (the best match).
- `classification_state`: `classified`, `unknown`, or `cached`.
- `source`: `gemini` or `cache`.

### State Rules

- If `genre` is empty or unusable, state is `unknown` and the track is routed to `Unknown`. The result is NOT cached.
- If a single `genre` is present, the track is mapped to that genre playlist. The result IS cached.

## GenrePlaylistTarget

Represents desired playlist membership for a specific genre.

### Fields

- `folder_id`: Target Tidal folder identifier.
- `playlist_name`: Genre playlist name.
- `genre_label`: Canonical genre key for matching.
- `desired_track_keys`: Set of track identity keys expected in the playlist.

### Notes

- One `GenrePlaylistTarget` exists per genre plus one for `Unknown` when needed.

## ExistingPlaylistSnapshot

Represents current playlist state fetched from Tidal before sync.

### Fields

- `playlist_id`: Tidal playlist identifier.
- `playlist_name`: Existing playlist name.
- `existing_track_keys`: Set of current track identity keys.

## SyncDelta

Represents the delta between desired and existing playlist contents.

### Fields

- `playlist_id`: Target playlist identifier.
- `to_add`: Track keys/IDs present in desired set but not in existing set.
- `to_remove`: Track keys/IDs present in existing set but not in desired set.

### Transition

- Apply `to_add` then `to_remove` (or equivalent safe order supported by API), then emit progress metrics.

## RunSummary

Represents user-visible completion statistics.

### Fields

- `library_tracks_scanned`: Total library tracks processed.
- `classified_tracks`: Count successfully mapped to at least one explicit genre.
- `unknown_tracks`: Count routed to `Unknown`.
- `playlists_created`: Number of new genre playlists created.
- `playlists_updated`: Number of playlists synced with non-empty delta.
- `tracks_added`: Aggregate additions across all playlists.
- `tracks_removed`: Aggregate removals across all playlists.
