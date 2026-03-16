# Quickstart: Gemini Support for Single-Seed Mode

## Goal
Generate Mode 3 playlists from a single seed track using Gemini recommendations.

## Prerequisites
- Project setup complete (`uv venv`, `uv pip install -e .`).
- Valid Tidal authentication session (`tidal_session.json`).
- Valid Gemini credentials available via environment (`GEMINI_API_KEY`, and optional model variables).

## 1. Run standard Gemini Mode 3

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --num-similar-tracks 20 --playlist-name "Gamemaster Gemini" --folder "Tidal Discovery Engine"
```

Expected behavior:
- Gemini recommendations are generated from single-seed artist/track context.
- Playlist is created using resolvable recommendations.

## 2. Run deep-cuts Gemini Mode 3 (`--shuffle`)

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --shuffle --num-similar-tracks 20 --playlist-name "Gamemaster Gemini Deep Cuts" --folder "Tidal Discovery Engine"
```

Expected behavior:
- Gemini recommendation intent switches to deep-cuts/underground style.
- Playlist creation remains best-effort on recommendation and insertion validity.

## 3. Validate best-effort count behavior

Run with a higher target count and inspect output:

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --num-similar-tracks 50 --playlist-name "Gamemaster Gemini Best Effort"
```

Expected checks:
- Output count does not exceed requested target (`50`).
- If fewer valid recommendations are available, run still succeeds when at least one track is inserted.

## 4. Validate unresolved-track warning behavior

Use a seed likely to produce hard-to-resolve recommendations and check warning output.

Expected checks:
- Run continues if some tracks cannot be resolved on Tidal.
- Warning log contains `TDE_WARN|code=MODE3_UNRESOLVED_TRACKS`.
- Warning includes skipped count and up to first 5 skipped track names.

## 5. Validation and failure checks

### Missing pair validation

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --gemini --playlist-name "Invalid Mode3"
```

Expected:
- Command fails with message indicating `--artist` and `--track` must be provided together.

### Gemini failure path

Use invalid model configuration to trigger Gemini error handling.

Expected:
- Actionable Gemini error output includes model identifier/failure guidance consistent with existing Gemini behavior.
- For unavailable/not-found model errors in Mode 3, run falls back to Last.fm and continues.
- For auth/quota/permission errors, run does not fallback.

### Zero-insert failure behavior

Expected:
- If recommendation resolution yields zero insertable Tidal tracks, command fails.
- Error log contains `TDE_ERROR|code=ZERO_TRACKS_INSERTED`.

## 6. Verification Matrix

| Scenario ID | Command Focus | Expected Result |
|---|---|---|
| QM3-001 | Mode 3 + `--gemini` standard | Playlist created with Gemini-derived recommendations. |
| QM3-002 | Mode 3 + `--gemini --shuffle` | Deep-cuts intent applied; playlist created best-effort. |
| QM3-003 | High `--num-similar-tracks` target | Returned recommendations do not exceed target; may be fewer. |
| QM3-004 | Partial insertion | Unresolved tracks skipped; warning includes count + first 5 names. |
| QM3-005 | Missing seed pair | Validation error before generation. |
| QM3-006 | Gemini model/provider failure | Actionable Gemini failure output. |
| QM3-007 | Unavailable model in Mode 3 | Last.fm fallback path is used. |
| QM3-008 | Zero insertions | Command fails with explicit zero-insert error. |

## 7. Validation Log (2026-03-10)

- Executed: `uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --num-similar-tracks 1 --playlist-name "Mode3 Gemini Smoke {date}" --folder "Tidal Discovery Engine"`
- Result: PASS
- Observed: Playlist `Mode3 Gemini Smoke 20260310` created with 1 inserted track (`https://tidal.com/browse/playlist/f005a458-433a-44d3-ae4e-02ba649d58df`).

- Executed: `uv run python -m src.cli.main --artist "Lost Tribe" --gemini --playlist-name "Invalid Mode3"`
- Result: PASS
- Observed: Failed fast with `Both --artist and --track are required together for single-seed mode.`

- Executed: `uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --num-similar-tracks 0 --playlist-name "Invalid Count"`
- Result: PASS
- Observed: Failed fast with `--num-similar-tracks must be a positive integer.`
