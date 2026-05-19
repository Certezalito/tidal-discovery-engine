# Contract: Exclude Existing Favorite Tracks (CLI)

## Scope

Defines CLI/runtime behavior for excluding tracks already present in the user's Tidal favorites when generating a playlist.

## Inputs

| Input | Required | Description |
|---|---|---|
| `--exclude-favorites` | No | Enables favorites exclusion mode for recommendation output. |
| `--playlist-name` | Yes | Destination playlist name. |
| `--num-tidal-tracks` | No | Seed selection count for default mode. |
| `--num-similar-tracks` | No | Recommendation target count. |
| `--gemini` | No | Enables Gemini recommendation branch. |
| `--artist` + `--track` | Conditionally | Single-seed mode inputs when used together. |

## Behavioral Rules

1. When `--exclude-favorites` is absent, behavior remains identical to baseline and favorites retrieval is not invoked.
2. When `--exclude-favorites` is present, system retrieves the complete favorites set before finalizing playlist tracks.
3. Favorites retrieval paginates all pages and retries failed page requests up to 2 times per page.
4. If retrieval fails or remains partial after retries, run aborts with clear error and no playlist output.
5. Exclusion match logic:
   - Primary key: ISRC
   - Fallback key: normalized title + primary artist
6. Exclusion data is in-memory only and must not be persisted to disk.
7. If exclusions reduce available tracks below requested count, system attempts supplementation with additional non-favorite candidates.
8. If supplementation cannot fully meet requested count, system emits an informative shortfall message and proceeds with partial output where allowed by the spec path.

## Error and Warning Contract

| Condition | Contracted behavior |
|---|---|
| Favorites retrieval hard failure | Error with corrective guidance; no playlist creation/output. |
| Favorites retrieval partial/incomplete | Treated as hard failure; no playlist creation/output. |
| All candidates are favorites | Informative message indicating no non-favorite candidates were available. |
| Requested count not met after filtering | Informative shortfall message with reason. |

## Observability Contract

- Logging MUST include whether exclusion mode is enabled.
- Logging MUST include favorites retrieval progress/failure summary.
- Logging MUST include exclusion counts (input, excluded, remaining).

## Validation Contract

- Exclusion-enabled path must demonstrate zero favorite leakage in output.
- Exclusion-disabled path must demonstrate no favorites retrieval call.
- Retry behavior must demonstrate up to 2 retries per failed page and fail-closed on persistent failure.
- No disk cache artifacts may be produced by exclusion flow.
