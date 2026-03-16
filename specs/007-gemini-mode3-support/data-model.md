# Data Model: Gemini Support for Single-Seed Mode

## Entities

### SingleSeedGeminiRequest
Represents a Mode 3 invocation that requests Gemini recommendations from one user-provided seed track.

| Field | Type | Required | Description |
|---|---|---|---|
| artist | string | Yes | User-provided artist seed value from CLI. |
| track | string | Yes | User-provided track seed value from CLI. |
| gemini_enabled | boolean | Yes | Whether Gemini recommendation path is requested (`--gemini`). |
| shuffle_enabled | boolean | Yes | Whether deep-cuts Gemini intent should be applied (`--shuffle`). |
| num_similar_tracks | integer | Yes | Upper target for number of recommendations to return. |
| playlist_name | string | Yes | Destination playlist display name. |
| folder_name | string | No | Optional folder target for playlist placement. |

Validation rules:
- `artist` and `track` must be provided together for Mode 3.
- `num_similar_tracks` must be a positive integer.
- `gemini_enabled` controls whether Mode 3 runs Gemini path or existing non-Gemini path.

### GeminiSeedContext
Represents the normalized context sent to Gemini for recommendation generation.

| Field | Type | Required | Description |
|---|---|---|---|
| seed_text | string | Yes | Combined artist+track context used for prompting. |
| intent | enum | Yes | Recommendation intent: `standard` or `deep_cuts`. |
| catalog_match_status | enum | Yes | Match assessment for seed context: `exact`, `ambiguous`, `unavailable`. |

Validation rules:
- `intent` is `deep_cuts` only when `shuffle_enabled` is true.
- Gemini generation proceeds even when `catalog_match_status` is `ambiguous` or `unavailable`.

### GeminiRecommendationSet
Represents the recommendation output returned by Gemini before Tidal insertion.

| Field | Type | Required | Description |
|---|---|---|---|
| requested_count | integer | Yes | Requested upper target (`num_similar_tracks`). |
| produced_count | integer | Yes | Number of Gemini recommendations generated before insertion filtering. |
| recommendations | list[track_ref] | Yes | Ordered candidate recommendations (artist/title pairs). |

Validation rules:
- `produced_count` must be less than or equal to `requested_count` for accepted output.
- Empty set is considered failure for successful run criteria.

### PlaylistInsertionOutcome
Represents final insertion result after attempting to resolve recommendations on Tidal.

| Field | Type | Required | Description |
|---|---|---|---|
| inserted_count | integer | Yes | Number of tracks successfully inserted in destination playlist. |
| skipped_count | integer | Yes | Number of recommended tracks skipped due to unresolved Tidal matching. |
| skipped_preview | list[string] | Yes | Up to first 5 skipped track display names for warning output. |
| warning_emitted | boolean | Yes | Whether skipped-track warning message was emitted. |
| terminal_status | enum | Yes | `success`, `partial_success`, or `failure`. |

Validation rules:
- `skipped_preview` length must be less than or equal to 5.
- `warning_emitted` must be true when `skipped_count` > 0.
- `terminal_status` is `partial_success` when `inserted_count` > 0 and `skipped_count` > 0.

## Relationships

- `SingleSeedGeminiRequest` creates `GeminiSeedContext`.
- `GeminiSeedContext` drives generation of `GeminiRecommendationSet`.
- `GeminiRecommendationSet` is consumed to produce `PlaylistInsertionOutcome`.

## State Transitions

1. Parse Mode 3 CLI request and validate `artist`/`track` pairing.
2. Build seed context and determine recommendation intent (`standard` or `deep_cuts`).
3. Generate Gemini recommendations with best-effort count capped by requested target.
4. Resolve each recommendation against Tidal catalog for insertion.
5. Skip unresolved tracks, insert resolvable tracks, and produce warning details (count + first 5 names).
6. Return final outcome with actionable output when failure paths are triggered.
