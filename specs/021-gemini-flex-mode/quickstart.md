# Quickstart & Verification Guide: Gemini Flex Mode Support

**Feature**: [Gemini Flex Mode Support](spec.md)  
**Branch**: `021-gemini-flex-mode`  
**Date**: 2026-10-07  
**Status**: Completed  

---

## 1. Prerequisites & Setup

1. Ensure Python 3.12+ and `uv` are installed.
2. Synchronize dependencies:
   ```bash
   uv sync
   ```
3. Set your Gemini API key:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

---

## 2. Validation Scenarios

### Scenario 1: Generate Recommendations Using Flex Tier
Validate that passing `--flex` retrieves recommendations via the cost-optimized flex tier, displaying the upfront notice.

```bash
uv run tde recommend --gemini --flex --num-tidal-tracks 5 --num-similar-tracks 10
```

**Expected Outcome**:
- Console prints notice: `Connecting to Gemini via Flex tier (50% cost savings). Flex tier uses opportunistic capacity; response turnaround is typically 1–15 minutes. Please wait...`
- Structured application log confirms tier resolution: `Gemini service tier resolution: tier='flex' source='cli' timeout=900000ms` at `INFO` level.
- Recommendation retrieval completes within client timeout (up to 900 seconds).
- Destination playlist is created with generated tracks, confirming successful flex mode execution.

---

### Scenario 2: Generate Track Radio Using Flex Tier
Validate that `--flex` works with single-seed radio generation.

```bash
uv run tde radio --artist "Daft Punk" --track "One More Time" --gemini --flex --num-tracks 10
```

**Expected Outcome**:
- Command succeeds and creates radio playlist.
- Recommendations are retrieved via Gemini using the flex service tier.

---

### Scenario 3: Reject `--flex` and `--no-flex` Without `--gemini`
Validate input validation and error feedback.

```bash
uv run tde recommend --flex
uv run tde radio --artist "Radiohead" --track "Karma Police" --no-flex
```

**Expected Outcome**:
- Both commands fail immediately with exit code `1`.
- Output: `Error: --flex and --no-flex flags require --gemini.`

---

### Scenario 4: Global Flex Configuration via Environment Variable
Validate that `GEMINI_SERVICE_TIER=flex` enables flex mode by default without adding flags.

```bash
GEMINI_SERVICE_TIER=flex uv run tde recommend --gemini --num-tidal-tracks 5
```

**Expected Outcome**:
- Command completes successfully using flex tier.
- Log output confirms: `Gemini service tier: 'flex' (source=env)`

---

### Scenario 5: Force Standard Tier with `--no-flex`
Validate that `--no-flex` overrides global environment configuration.

```bash
GEMINI_SERVICE_TIER=flex uv run tde recommend --gemini --no-flex --num-tidal-tracks 5
```

**Expected Outcome**:
- Command completes quickly using standard tier.
- Log output confirms: `Gemini service tier: 'standard' (source=cli)`

---

### Scenario 6: Custom Flex Timeout Configuration
Validate that `GEMINI_FLEX_TIMEOUT_SECONDS` customizes the client timeout.

```bash
GEMINI_FLEX_TIMEOUT_SECONDS=600 uv run tde recommend --gemini --flex --num-tidal-tracks 5
```

**Expected Outcome**:
- Timeout is configured to 600,000 ms (10 minutes) instead of the 900-second default.

---

### Scenario 7: Graceful Interruption Handling (Ctrl+C)
Validate that canceling a long-running flex request exits cleanly.

```bash
uv run tde recommend --gemini --flex
# Press Ctrl+C while the turnaround notice is displayed
```

**Expected Outcome**:
- Output: `Operation canceled by user.`
- Clean exit code `130` without Python stack traces.

---

### Scenario 8: Batch Library Genre Organization in Flex Mode
Validate that `tde organize` accepts `--flex` for batch genre categorization.

```bash
uv run tde organize --flex
```

**Expected Outcome**:
- Gemini API classification requests route through `service_tier='flex'`.
- Progressive backoff retries wait out brief capacity spikes.

---

### Scenario 9: Automatic Standard Tier Fallback via CLI Flag
Validate that passing `--flex-fallback-standard` automatically completes requests on standard tier when flex capacity is unavailable.

```bash
uv run tde recommend --gemini --flex --flex-fallback-standard
```

**Expected Outcome**:
- If flex capacity is unavailable (HTTP 503 / 429) after recovery retries, system logs warning:
  `[WARNING] Gemini flex capacity unavailable... Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).`
- Request transitions to standard tier and completes successfully without aborting.

---

### Scenario 10: Global Fallback Configuration & CLI Override
Validate that `GEMINI_FLEX_FALLBACK_STANDARD=true` enables fallback globally, and `--no-flex-fallback-standard` disables it.

```bash
# Enable globally via env
GEMINI_SERVICE_TIER=flex GEMINI_FLEX_FALLBACK_STANDARD=true uv run tde recommend --gemini

# Override per command to force fail-fast cost protection
GEMINI_SERVICE_TIER=flex GEMINI_FLEX_FALLBACK_STANDARD=true uv run tde recommend --gemini --no-flex-fallback-standard
```

**Expected Outcome**:
- First command falls back to standard tier if flex is constrained.
- Second command fails fast with actionable `flex-capacity` guidance if flex is constrained, strictly preserving cost protection.

---

### Scenario 11: Sticky Standard Fallback in Multi-Batch Organization
Validate that in `tde organize`, once a batch triggers standard fallback, remaining batches execute directly on standard tier.

```bash
uv run tde organize --flex --flex-fallback-standard
```

**Expected Outcome**:
- If a batch exhausts flex capacity and falls back to standard tier, all subsequent batches within that execution run directly on standard tier without repeated flex retry delays.

---

## 3. Automated Test Verification

Run targeted and complete test suites:

```bash
# Run targeted Gemini service and CLI tests
uv run pytest tests/test_gemini_service.py tests/test_cli.py tests/test_cli_genre_organizer.py

# Run complete repository test suite
uv run pytest
```
