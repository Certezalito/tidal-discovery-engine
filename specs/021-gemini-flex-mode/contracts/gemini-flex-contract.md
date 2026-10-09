# Interface Contract: Gemini Flex Mode Support

**Feature**: [Gemini Flex Mode Support](../spec.md)  
**Branch**: `021-gemini-flex-mode`  
**Date**: 2026-10-07  
**Status**: Completed  

---

## 1. CLI Commands & Options Contract

### 1.1 `tde recommend`

```bash
uv run tde recommend [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--flex / --no-flex` | Boolean toggle | `None` | Route Gemini recommendations through the flex service tier (50% cheaper token rates, 1–15 min variable turnaround). `--no-flex` forces standard tier. |
| `--flex-fallback-standard / --no-flex-fallback-standard` | Boolean toggle | `None` | Automatically fallback to standard tier inference if flex capacity is exhausted (HTTP 503 / 429) or times out. |
| `--gemini` | Flag | `False` | Use Google Gemini AI for recommendations instead of Last.fm. |

**Validation Rules**:
- If `--flex` or `--no-flex` is passed without `--gemini`:
  - **Exit Code**: `1`
  - **Console Message**: `Error: --flex and --no-flex flags require --gemini.`
- If `--flex-fallback-standard` or `--no-flex-fallback-standard` is passed without `--gemini`:
  - **Exit Code**: `1`
  - **Console Message**: `Error: --flex-fallback-standard and --no-flex-fallback-standard flags require --gemini.`

---

### 1.2 `tde radio`

```bash
uv run tde radio --artist <ARTIST> --track <TRACK> [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--flex / --no-flex` | Boolean toggle | `None` | Route Gemini single-seed recommendations through the flex service tier. `--no-flex` forces standard tier. |
| `--flex-fallback-standard / --no-flex-fallback-standard` | Boolean toggle | `None` | Automatically fallback to standard tier inference if flex capacity is exhausted or times out. |
| `--gemini` | Flag | `False` | Use Google Gemini AI for single-seed recommendations instead of Last.fm. |

**Validation Rules**:
- If `--flex` or `--no-flex` is passed without `--gemini`:
  - **Exit Code**: `1`
  - **Console Message**: `Error: --flex and --no-flex flags require --gemini.`
- If `--flex-fallback-standard` or `--no-flex-fallback-standard` is passed without `--gemini`:
  - **Exit Code**: `1`
  - **Console Message**: `Error: --flex-fallback-standard and --no-flex-fallback-standard flags require --gemini.`

---

### 1.3 `tde organize` (and alias `genre-organizer`)

```bash
uv run tde organize [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--flex / --no-flex` | Boolean toggle | `None` | Route Gemini batch track classification requests through the flex service tier. `--no-flex` forces standard tier. |
| `--flex-fallback-standard / --no-flex-fallback-standard` | Boolean toggle | `None` | Automatically fallback to standard tier inference if flex capacity is exhausted or times out. |

---

## 2. Upfront User Liveness Notice Contract

When an API call is initiated under `service_tier == "flex"`:
- The system MUST output an informational message before blocking on network I/O:
  ```text
  Connecting to Gemini via Flex tier (50% cost savings).
  Flex tier uses opportunistic capacity; response turnaround is typically 1–15 minutes. Please wait...
  ```
- If the user presses `Ctrl+C` (SIGINT) while waiting:
  - **Console Message**: `Operation canceled by user.`
  - **Exit Code**: `130`
  - Stack traces MUST NOT be displayed.

---

## 3. Environment Configuration Contract

### 3.1 Variable Specifications

| Variable Name | Permitted Values | Default Value | Description / Normalization Rule |
|---|---|---|---|
| `GEMINI_SERVICE_TIER` | `"standard"`, `"flex"` | `"standard"` | Whitespace trimmed, converted to lowercase (`"  FLEX  "` → `"flex"`). |
| `GEMINI_FLEX_TIMEOUT_SECONDS` | Positive integer | `900` | HTTP client timeout in seconds applied to flex tier requests. |
| `GEMINI_FLEX_FALLBACK_STANDARD` | `"true"`, `"false"`, `"1"`, `"0"`, `"yes"`, `"no"` | `"false"` | Whether to automatically fallback to standard tier inference upon flex capacity exhaustion or timeout. |
| `GEMINI_FLEX_MAX_RETRIES` | Positive integer | `5` | Maximum number of progressive backoff retries for flex capacity spikes. |

### 3.2 Warning & Degradation Behavior

- If `GEMINI_SERVICE_TIER` contains an unrecognized value:
  - **Log Level**: `WARNING`
  - **Log Message**: `Unrecognized GEMINI_SERVICE_TIER '%s'; defaulting to 'standard'.`
  - **Runtime Result**: Request proceeds in `"standard"` tier.
- If `GEMINI_FLEX_TIMEOUT_SECONDS` is invalid (non-integer or <= 0):
  - **Log Level**: `WARNING`
  - **Log Message**: `Invalid GEMINI_FLEX_TIMEOUT_SECONDS '%s'; defaulting to 900 seconds.`
  - **Runtime Result**: Timeout defaults to 900 seconds.
- If `GEMINI_FLEX_FALLBACK_STANDARD` is invalid:
  - **Log Level**: `WARNING`
  - **Log Message**: `Invalid GEMINI_FLEX_FALLBACK_STANDARD '%s'; defaulting to false.`
  - **Runtime Result**: Fallback setting defaults to `false`.

---

## 4. Python Service Layer Contract

### 4.1 `gemini_service.py`

```python
def get_recommendations(
    api_key: str,
    seed_tracks: list,
    count: int,
    shuffle: bool = False,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
) -> list[dict]:
    """Generates song recommendations using Google Gemini.

    Args:
        api_key: The Google Gemini API key.
        seed_tracks: Seed track objects for recommendation context.
        count: Desired number of recommendations.
        shuffle: Whether to apply deep-cut prompt styling.
        flex: Explicit flex toggle. True forces flex tier, False forces standard tier,
              None defers to GEMINI_SERVICE_TIER environment configuration.
        flex_fallback_standard: Explicit fallback toggle. True enables fallback to standard tier
                                on capacity exhaustion, False disables it, None defers to environment.

    Returns:
        list[dict]: Recommendations with keys 'artist', 'title', 'isrc'.
    """
```

```python
def classify_tracks_genres(
    api_key: str,
    tracks: list,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
) -> list[dict]:
    """Classifies a list of tracks into primary and sub-genres using Gemini.

    Args:
        api_key: The Google Gemini API key.
        tracks: Track dictionaries with artist, title, isrc.
        flex: Explicit flex toggle. True forces flex tier, False forces standard tier,
              None defers to GEMINI_SERVICE_TIER environment configuration.
        flex_fallback_standard: Explicit fallback toggle. True enables fallback to standard tier
                                on capacity exhaustion, False disables it, None defers to environment.

    Returns:
        list[dict]: Classification results with keys 'artist', 'title', 'isrc', 'primary_genre', 'sub_genres'.
    """
```

```python
def _resolve_service_tier(
    cli_flex: bool | None,
    dotenv_config: dict,
) -> tuple[str, str, int]:
    """Resolves target Gemini inference tier, source, and timeout in milliseconds.

    Returns:
        tuple[str, str, int]: (tier_name, source_identifier, timeout_ms)
                              e.g. ('flex', 'cli', 900000) or ('standard', 'default', 120000).
    """
```

```python
def _resolve_flex_fallback_standard(
    cli_fallback: bool | None,
    dotenv_config: dict,
) -> tuple[bool, str]:
    """Resolves whether to automatically fallback to standard tier on flex capacity exhaustion.

    Returns:
        tuple[bool, str]: (fallback_enabled, source_identifier)
                          e.g. (True, 'cli'), (True, 'env'), or (False, 'default').
    """
```

### 4.2 `genre_organizer_service.py`

```python
def run_genre_organizer_sync(
    session,
    folder_name: str = "Genres",
    ...,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
) -> GenreOrganizerSummary:
    """Executes full library scan, track classification, and playlist sync.
    
    Maintains sticky standard fallback across batches: if any batch encounters
    flex capacity exhaustion and falls back to standard tier, all subsequent batches
    within this execution continue on standard tier directly.
    """
```

---

## 5. Google GenAI API Payload Contract

When invoking `client.models.generate_content`:

```python
config = types.GenerateContentConfig(
    temperature=...,
    service_tier=resolved_tier,  # "flex" or "standard"
    http_options=types.HttpOptions(timeout=resolved_timeout_ms),
    response_mime_type="application/json",
    response_schema=...,
    max_output_tokens=...,
)
```

---

## 6. Diagnostic Failure Contracts

### 6.1 Capacity Shedding
```text
Gemini request failed. model='gemini-flash-latest', category='flex-capacity', details='...'.
Next step: Gemini flex tier capacity is temporarily unavailable due to demand. Retry later, or run with --no-flex (or without --flex) to use the standard tier.
```

### 6.2 Latency Timeout
```text
Gemini request failed. model='gemini-flash-latest', category='flex-timeout', details='Request timed out after X seconds'.
Next step: Gemini flex tier request timed out after X seconds due to extended capacity queueing. Retry later, or run with --no-flex to use the standard tier.
```

---

## 7. Operational Logging & Terminal Confirmation Contract

### 7.1 Structured Service Tier Resolution Log
Whenever Gemini operations are prepared in `gemini_service.py` (`get_recommendations`, `classify_tracks_genres`), the system MUST emit a structured informational log at `INFO` level:
```text
Gemini service tier resolution: tier='<tier>' source='<source>' timeout=<timeout_ms>ms
```
- `<tier>`: `"flex"` or `"standard"`
- `<source>`: `"cli"`, `"env"`, `"dotenv"`, or `"default"`
- `<timeout_ms>`: Configured HTTP client timeout in milliseconds

### 7.2 Terminal Notice & Completion Confirmation
- For commands executing under flex mode (`recommend`, `radio`, `organize`):
  - **Before dispatch**: Output upfront turnaround notice (`FLEX_UPFRONT_NOTICE`).
  - **Upon completion**: Provide explicit confirmation in terminal output and application logs that flex mode was utilized and execution finished successfully.

### 7.3 Standard Tier Fallback Transition Warning Log
Whenever an operation falls back from flex tier to standard tier due to capacity exhaustion or timeout:
- The system MUST emit a warning log at `WARNING` level:
  ```text
  Gemini flex capacity unavailable (HTTP <status_code> / timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).
  ```
- For multi-batch organization runs, the log MUST record that subsequent batches will continue directly on standard tier.
