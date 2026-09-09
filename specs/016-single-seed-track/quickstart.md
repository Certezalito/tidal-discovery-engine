# Phase 1 Quickstart Validation Guide: Dedicated Radio Command

## Prerequisites
- Python 3.12+ with virtual environment managed by `uv`
- Active Tidal session (`tidal_session.json` present or configured)
- `.env` configured with Tidal API credentials and optional `GEMINI_API_KEY`

---

## Scenario 1: Quick Zero-Friction Radio Station
Validate that the dedicated `radio` command works without specifying a custom playlist name or track count.

### Command
```bash
python -m src.cli.main radio --artist "Underworld" --track "Born Slippy"
```

### Expected Outcome
1. Command starts without errors.
2. Resolves the seed track `"Born Slippy"` by Underworld on Tidal.
3. Places the seed track at Track #1 in the playlist.
4. Generates 49 recommendations based on the seed track and appends them after Track #1 (total 50 tracks in playlist).
5. Automatically names the playlist: `"Underworld - Born Slippy Radio"`.
6. Sets the playlist description containing the seed track information: `"Seed track: Born Slippy by Underworld • Total tracks: 50"`.
7. Automatically organizes the playlist inside folder `"Radio"` on Tidal.
8. Prints the playlist URL.

---

## Scenario 2: Dynamic Date Replacement & Folder Placement
Validate that custom playlist naming with dynamic `{date}` token and folder organization work as expected.

### Command
```bash
python -m src.cli.main radio \
  --artist "Bicep" \
  --track "Glue" \
  --playlist-name "Bicep Radio {date}" \
  --folder "Electronic Stations"
```

### Expected Outcome
1. Playlist is created inside folder `"Electronic Stations"` (created if absent).
2. Playlist title resolves `{date}` to `YYYYMMDD` (e.g., `"Bicep Radio 20260903"`).
3. Playlist contains `"Glue"` by Bicep as Track #1, followed by recommendations.
4. Playlist description metadata reflects seed track `"Glue" by Bicep`.

---

## Scenario 3: AI Recommendations with Deep Cuts & Exclude Favorites
Validate full feature parity when combining Gemini AI recommendations, deep cuts (`--shuffle`), and library favorite exclusion.

### Command
```bash
python -m src.cli.main radio \
  --artist "Burial" \
  --track "Archangel" \
  --gemini \
  --shuffle \
  --exclude-favorites \
  --num-tracks 25
```

### Expected Outcome
1. Requires and uses `GEMINI_API_KEY`.
2. Places `"Archangel"` by Burial as Track #1.
3. Requests 24 underground/deep-cut recommendations from Gemini tailored to `"Archangel"` by Burial.
4. Filters out any candidate tracks already present in user's Tidal favorites.
5. If unresolvable tracks occur, logs a capped warning preview (max 5 items) and succeeds as long as at least 1 track was added.

---

## Scenario 4: Command Separation & Option Isolation in `recommend`
Validate that `recommend` no longer accepts single-seed parameters and functions strictly as a library-discovery command.

### Command
```bash
# 1. Attempting single-seed flags on recommend is rejected
python -m src.cli.main recommend --artist "Faithless" --track "Insomnia"
```

### Expected Outcome
1. Click immediately rejects the invocation:
   ```text
   Error: No such option: --artist
   ```
2. Library discovery runs cleanly without single-seed options:
   ```bash
   python -m src.cli.main recommend --num-tidal-tracks 5 --num-similar-tracks 10
   ```

---

## Scenario 5: Input Validation Errors in `radio`
Validate fast rejection of invalid inputs.

```bash
# 1. Missing track
python -m src.cli.main radio --artist "Orbital"
# Expected: Error stating both --artist and --track are required.

# 2. Whitespace-only artist
python -m src.cli.main radio --artist "   " --track "Halcyon"
# Expected: Error stating --artist cannot be empty.

# 3. Non-positive track count
python -m src.cli.main radio --artist "Orbital" --track "Halcyon" --num-tracks 0
# Expected: Error stating --num-tracks must be a positive integer.
```

---

## Automated Verification Suite
Run the test suite verifying all single-seed and radio command flows:

```bash
uv run pytest tests/test_cli.py
```
