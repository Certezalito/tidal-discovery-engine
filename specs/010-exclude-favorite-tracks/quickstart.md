# Quickstart: Exclude Existing Favorite Tracks

## Prerequisites

- Python 3.12+
- Valid Tidal session (`tidal_session.json`) via existing auth flow
- Existing environment setup used by current CLI flows

## Basic Usage

Run playlist generation with favorites exclusion enabled:

```bash
python -m src.cli.main \
  --playlist-name "Discovery {date}" \
  --num-tidal-tracks 10 \
  --num-similar-tracks 5 \
  --exclude-favorites
```

## Gemini Variant

```bash
GEMINI_API_KEY=... python -m src.cli.main \
  --gemini \
  --playlist-name "Gemini Discovery {date}" \
  --num-tidal-tracks 10 \
  --num-similar-tracks 5 \
  --exclude-favorites
```

## Single-Seed Variant

```bash
python -m src.cli.main \
  --artist "Massive Attack" \
  --track "Teardrop" \
  --playlist-name "Seeded Discovery {date}" \
  --num-similar-tracks 8 \
  --exclude-favorites
```

## Expected Behavior

- With `--exclude-favorites`, favorites are fully loaded (paged) and used to filter output tracks.
- Matching uses ISRC first, then normalized title + primary artist fallback.
- If favorites retrieval is incomplete or fails after retries, execution aborts with a clear error and no playlist output.
- No favorites cache files are written.

## Validation Checklist

1. Run with `--exclude-favorites` and verify no output track is in favorites.
2. Run without `--exclude-favorites` and verify behavior matches current baseline.
3. Simulate page retrieval failure and verify fail-closed behavior.
4. Confirm no local favorites cache file is created during either run.
