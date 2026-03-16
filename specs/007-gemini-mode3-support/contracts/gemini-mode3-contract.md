# Contract: Gemini in Mode 3 (Single-Seed Flow)

## Scope
Defines the CLI and runtime behavior contract for using Gemini recommendations with Mode 3 (`--artist` + `--track`).

## Inputs

| Input | Required | Description |
|---|---|---|
| `--artist` | Conditionally | Required with `--track` for Mode 3 seed input. |
| `--track` | Conditionally | Required with `--artist` for Mode 3 seed input. |
| `--gemini` | No | Enables Gemini recommendation path in Mode 3. |
| `--shuffle` | No | In Gemini Mode 3, switches recommendation intent to deep cuts. |
| `--num-similar-tracks` | No | Upper target for recommendation count. |
| `--playlist-name` | Yes | Destination playlist name. |
| `--folder` | No | Optional folder for playlist placement. |

## Behavioral Rules

1. If `--gemini` is present with valid Mode 3 seed input, system uses Gemini recommendation generation for Mode 3.
2. If `--gemini` is absent, existing non-Gemini Mode 3 behavior remains unchanged.
3. In Gemini Mode 3, `--shuffle` must apply deep-cuts/underground recommendation intent.
4. If seed catalog matching is ambiguous/unavailable, system continues using text seed context (`artist` + `track`).
5. `--num-similar-tracks` is an upper target for Gemini Mode 3; system may return fewer valid recommendations (best-effort).
6. During Tidal insertion, unresolved recommendations are skipped, not fatal for the entire run.
7. When any recommendations are skipped, CLI warning includes:
   - skipped count
   - up to first 5 skipped track names

## Error and Warning Contract

| Condition | Contracted behavior |
|---|---|
| Missing `--artist` or `--track` pair in Mode 3 | Fail fast with corrective validation message. |
| Gemini provider/model failure | Return actionable Gemini failure output consistent with existing Gemini modes. |
| Some recommendations unresolved on Tidal | Continue playlist creation and emit skipped warning (count + first 5 names). |
| No valid recommendations available | Return actionable failure output (playlist not considered successful). |

## Acceptance Contract

- Valid Mode 3 + Gemini invocation creates playlist with non-empty inserted tracks when at least one recommendation resolves.
- Output never reports more recommendations than requested by `--num-similar-tracks`.
- Unresolved insertions do not abort successful insertion of remaining tracks.
- Skipped-track warning detail is constrained to count and up to five names.
- README and quickstart include Mode 3 Gemini usage examples for standard and shuffle variants.
