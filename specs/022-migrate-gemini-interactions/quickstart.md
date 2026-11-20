# Quickstart Validation Guide: Migrate to Current Gemini Interaction Method

**Feature**: `022-migrate-gemini-interactions`  
**Spec**: [spec.md](./spec.md) | **Data Model**: [data-model.md](./data-model.md) | **Contract**: [contracts/gemini-service-contract.md](./contracts/gemini-service-contract.md)

## Prerequisites

1. Python 3.12+ and `uv` installed.
2. Dependencies synced with upgraded `google-genai>=2.25.0`:
   ```bash
   uv sync
   ```
3. For live smoke tests (optional beyond automated unit tests): valid `.env` with `GEMINI_API_KEY` and authenticated `tidal_session.json`.

---

## Validation Scenarios

### 1. Automated Regression & Contract Verification
Run the full automated test suite to verify Interactions API migration, structured output validation, `store=False`, `thinking_level` (`medium` for recommendations, `minimal` with `low` compatibility fallback for classification), deprecated-model auto-substitution, flex tier retries/fallback, and CLI compatibility:

```bash
uv run pytest -v
```
**Expected outcome**: All tests pass with 0 failures and 0 references to legacy `generate_content` / `GenerateContentConfig` in `src/`.

### 2. Verify Legacy Interface Retirement
Confirm no calls to the legacy `generateContent` API remain in `src/`:

```bash
grep -rn "generate_content\|GenerateContentConfig" src/
```
**Expected outcome**: Command returns no matches (exit code `1`).

### 3. Playlist & Radio Recommendations (Standard & Deep Cuts)
```bash
uv run tde recommend --gemini --num-tidal-tracks 3 --num-similar-tracks 3 --playlist-name "TDE Interactions Test"
uv run tde recommend --gemini --shuffle --num-tidal-tracks 3 --num-similar-tracks 3 --playlist-name "TDE Deep Cuts Test"
uv run tde radio --artist "Burial" --track "Archangel" --gemini --num-tracks 10
```
**Expected outcome**:
- Interactions execute with `gemini-flash-latest` (when `GEMINI_MODEL` is unset), `store=False`, and `thinking_level="medium"`.
- Playlists are created on Tidal using artist + title catalog lookup only (no AI-generated ISRCs).

### 4. Library Genre Organization & Cache Continuity
```bash
uv run tde organize
```
**Expected outcome**:
- Existing rows in `data/genre_cache.db` are reused at zero Gemini token cost.
- Uncached tracks are classified via Interactions API (`store=False`, `thinking_level="minimal"` or `"low"` fallback if required by model) into 1 specific `primary_genre` and up to 3 `sub_genres`.

### 5. Deprecated Legacy Model Auto-Substitution
```bash
GEMINI_MODEL=gemini-2.0-flash uv run tde recommend --gemini --num-tidal-tracks 2 --num-similar-tracks 2
```
**Expected outcome**:
- Logs emit a `WARNING` noting that deprecated model `gemini-2.0-flash` was automatically substituted with `gemini-flash-latest`.
- Request completes cleanly without failing.

### 6. Flex Tier Cost Protection & Opt-In Standard Fallback
```bash
uv run tde recommend --gemini --flex --num-tidal-tracks 2 --num-similar-tracks 2
uv run tde recommend --gemini --flex --flex-fallback-standard --num-tidal-tracks 2 --num-similar-tracks 2
```
**Expected outcome**:
- Terminal displays the upfront flex latency notice and INFO logs confirm `tier='flex'`, source, and `timeout=900000ms`.
- Requests dispatch with `service_tier="flex"` and client timeout `900000` ms.
- Without `--flex-fallback-standard`, capacity exhaustion fails fast without standard billing; with `--flex-fallback-standard`, fallback logs a `WARNING` and completes on `standard`.
