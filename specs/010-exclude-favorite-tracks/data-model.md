# Data Model: Exclude Existing Favorite Tracks

## Entity: FavoriteTrackIdentity

Represents the minimum identity data needed from a user favorite for exclusion checks.

### Fields

- `track_id` (string, optional): Tidal track ID when available.
- `isrc` (string, optional): Canonicalized uppercase ISRC.
- `normalized_title` (string, optional): Normalized track title for fallback matching.
- `normalized_primary_artist` (string, optional): Normalized primary artist for fallback matching.
- `identity_key` (string, derived):
  - `isrc:{ISRC}` when ISRC exists
  - else `fallback:{normalized_title}|{normalized_primary_artist}`

### Validation Rules

- At least one identity strategy MUST be derivable:
  - valid non-empty ISRC, or
  - non-empty normalized title + normalized primary artist pair.
- ISRC comparison MUST be case-insensitive after canonicalization.
- Normalization MUST trim and lowercase text fields.

## Entity: RecommendedTrackIdentity

Represents the identity view of a candidate recommendation before final insertion.

### Fields

- `source_track` (object): Track object resolved from Tidal or recommendation pipeline.
- `isrc` (string, optional)
- `normalized_title` (string, optional)
- `normalized_primary_artist` (string, optional)
- `identity_key` (string, derived using same rule as favorites)

### Validation Rules

- Identity derivation logic MUST exactly match `FavoriteTrackIdentity` derivation.
- If no identity key can be derived, the track is considered non-matchable by exclusion and remains eligible unless additional policy is introduced.

## Entity: FavoritesSnapshot

In-memory runtime container for exclusion filtering.

### Fields

- `identity_keys` (set[string]): All favorite identity keys for O(1) membership checks.
- `total_favorites` (int): Count of favorites loaded.
- `pages_loaded` (int): Number of successful favorites pages retrieved.
- `load_complete` (bool): True only when full pagination completed.

### Validation Rules

- Snapshot MUST only exist in-process memory for current run.
- `load_complete` MUST be true before exclusion filtering begins.
- If pagination is incomplete after retry policy, snapshot is invalid and run aborts.

## Entity: ExclusionFilterResult

Result of applying favorites exclusion to recommendations.

### Fields

- `input_count` (int): Number of candidate tracks before filtering.
- `excluded_count` (int): Number of candidates removed as favorites.
- `remaining_tracks` (list[RecommendedTrackIdentity]): Tracks eligible for playlist output.
- `shortfall` (int): Remaining count below requested output size after supplement attempts.

### State Transitions

1. `unfiltered` -> `filtered` when favorites snapshot is complete and membership test applied.
2. `filtered` -> `supplemented` when additional non-favorite candidates are appended.
3. `supplemented` -> `finalized` when requested count is met or candidate space is exhausted.
4. Any favorites load failure transitions process to `aborted` (no playlist output).
