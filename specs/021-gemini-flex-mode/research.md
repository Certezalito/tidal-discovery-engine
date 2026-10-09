# Technical Research & Decisions: Gemini Flex Mode Support

**Feature**: [Gemini Flex Mode Support](spec.md)  
**Branch**: `021-gemini-flex-mode`  
**Date**: 2026-10-07  
**Status**: Completed  

---

## 1. Upstream Client Library Currency & Native Capability Discovery

### Problem Context
The application utilizes Google Gemini for music recommendations and track genre classification. The specification requires routing Gemini API requests through the "flex" service tier to benefit from a 50% token cost reduction. In the existing environment, `pyproject.toml` pins `google-genai>=1.61.0`. In `google-genai` version 1.61.0, attempting to pass `service_tier` into `types.GenerateContentConfig` results in a Pydantic `ValidationError` (`Extra inputs are not permitted [type=extra_forbidden, input_value='flex']`).

### Decision
Update `pyproject.toml` dependency to `google-genai>=1.70.0` (or latest stable `>=2.28.0`), which natively introduces and supports the `service_tier` field on `types.GenerateContentConfig`. Configure Gemini calls with `service_tier="flex"` or `service_tier="standard"`.

### Rationale
- **Constitution Principle X (Critical Dependency Currency & Capability Discovery)**: Mandates inspecting upstream library releases for newly added native capabilities before implementing bespoke workarounds. Version 1.70.0+ natively models `service_tier` in `GenerateContentConfig`.
- Enforces explicit version constraints in `pyproject.toml`, preventing stale environment runtime failures.
- Preserves native Pydantic schema validation without monkey-patching or raw HTTP overrides.

### Alternatives Considered
- **Raw HTTP API calls via `requests`**: Rejected because it circumvents Pydantic response schema parsing (`response_schema=list[Song]`), client authentication, and official SDK retry utilities.
- **Monkey-patching Pydantic model schemas at runtime**: Rejected as brittle and prone to breakage across SDK patch releases.

---

## 2. Service Tier Configuration Resolution & Precedence

### Problem Context
Users need to activate flex mode via CLI flags (`--flex`), disable it via CLI flags (`--no-flex`), or configure it globally via environment variables (`GEMINI_SERVICE_TIER` in `.env` or system environment). Precedence must be deterministic, robust against whitespace/casing variations, and safe against invalid inputs.

### Decision
Implement a centralized resolution helper in `src/services/gemini_service.py`:
`_resolve_service_tier(cli_flex: bool | None, dotenv_config: dict) -> tuple[str, str]`

**Resolution Precedence Order**:
1. **Explicit CLI flag**:
   - `cli_flex is True` → `("flex", "cli")`
   - `cli_flex is False` → `("standard", "cli")`
2. **Environment Variable (`GEMINI_SERVICE_TIER`)**:
   - Inspect `os.environ.get("GEMINI_SERVICE_TIER")`, then `.env` via `dotenv_config`.
   - Clean and normalize (strip whitespace, convert to lowercase).
   - If `"flex"` → `("flex", "env")` or `("flex", "dotenv")`
   - If `"standard"` → `("standard", "env")` or `("standard", "dotenv")`
   - If invalid/unrecognized → emit a warning log and fall back safely to `("standard", "default")`.
3. **System Default**:
   - If unset or blank → `("standard", "default")`.

### Rationale
- Mirrors existing `_resolve_primary_model` and `_resolve_fallback_model` architecture in `gemini_service.py`.
- Prevents invalid values from crashing the application.
- Emits structured logging indicating the active tier and resolution source for auditability.

### Alternatives Considered
- **CLI flag only without environment variable**: Rejected because automated cron workflows (Constitution Principle II) benefit from persistent `.env` configuration without editing script definitions.
- **Boolean-only variable (`GEMINI_FLEX=true`)**: Rejected in favor of `GEMINI_SERVICE_TIER` to align with the official Gemini API nomenclature (`standard`, `flex`, `priority`).

---

## 3. CLI Ergonomics & Paired Flag Design

### Problem Context
Commands supporting Gemini (`recommend`, `radio`, `organize`) need an ergonomic, zero-friction interface to toggle flex mode. Furthermore, when `GEMINI_SERVICE_TIER=flex` is set in `.env`, users must be able to force standard tier execution without modifying `.env`.

### Decision
Adopt Click's paired boolean option pattern:
```python
@click.option(
    "--flex/--no-flex",
    default=None,
    help="Use Google Gemini flex service tier (50% cheaper token rates, variable latency).",
)
```

**Validation Rules**:
- On `recommend` and `radio`: If `flex is not None` and `--gemini` is false, abort with `click.ClickException("--flex and --no-flex flags require --gemini.")`.
- On `organize` (and `genre-organizer`): Pass `flex` to the genre organizer service to route Gemini track classification requests.

### Rationale
- Using `default=None` cleanly differentiates between:
  - User passed `--flex` (`flex == True`)
  - User passed `--no-flex` (`flex == False`)
  - User passed neither flag (`flex is None` → fall back to environment variable or default)
- Aligns directly with Constitution Principle IX (CLI Ergonomics & Friction Reduction).

### Alternatives Considered
- **`--flex` flag only without `--no-flex`**: Rejected during clarification session because users with `GEMINI_SERVICE_TIER=flex` in `.env` would have no way to execute an interactive, urgent command in standard mode.
- **`--tier [standard|flex]` argument**: Rejected as verbose; boolean toggles are faster to type and discover.

---

## 4. Capacity Shedding Failure Handling & Cost Protection

### Problem Context
Flex mode utilizes preemptible, best-effort capacity. During high-demand periods, the Gemini API may reject or shed flex requests (returning HTTP 429 Resource Exhausted or HTTP 503). If the system automatically retried at the standard tier, users would unknowingly incur 2x token costs.

### Decision
Implement strict cost protection:
1. Allow existing `RECOVERY_RETRY_LIMIT = 1` retry for transient errors.
2. If flex requests fail after retries due to quota, rate limits, or capacity shedding, fail fast with a dedicated `category="flex-capacity"` error.
3. Emit actionable guidance:
   `"Gemini flex tier capacity is temporarily unavailable due to demand. Retry later or run with --no-flex (or without --flex) to use the standard tier."`
4. **Strictly prohibit silent automatic fallback to the standard tier**.

### Rationale
- **Constitution Principle VI (AI Cost & Token Efficiency)**: Guarantees users are never billed standard rates without explicit intent.
- Provides immediate transparency and actionable resolution steps without guessing.

### Alternatives Considered
- **Automatic fallback to standard tier**: Evaluated and explicitly rejected during the clarification session (2026-10-07) to prevent unexpected billing.
- **Infinite backoff / long polling**: Inappropriate for CLI tools; users prefer quick, clear feedback.

---

## 5. Scope Coverage Across Services & Subcommands

### Problem Context
Gemini is used in two places in the repository:
1. `get_recommendations()` in `src/services/gemini_service.py` (called by `tde recommend` and `tde radio`).
2. `classify_tracks_genres()` in `src/services/gemini_service.py` (called by `tde organize`).

### Decision
Extend both `get_recommendations` and `classify_tracks_genres` to accept an optional `flex: bool | None = None` parameter. Pass the resolved service tier to `GenerateContentConfig(service_tier=resolved_tier, ...)`.

### Rationale
- Genre organization processes large batches of library tracks, where a 50% token reduction yields the highest monetary savings in the application.
- Ensures consistent behavior and parameter design across the entire codebase.

### Alternatives Considered
- **Limiting flex mode to recommendations only**: Rejected because batch library organization is the most token-intensive feature in the system.

---

## 6. Extended Latency Profile & Timeout Architecture

### Problem Context
Official Google Gemini documentation states that while standard tier targets near-instant interactive responses, the Flex tier targets a turnaround latency of **1 to 15 minutes** because it leverages opportunistic off-peak capacity. Without explicit architectural handling:
1. Standard HTTP client timeouts (typically 30–60s in `httpx` / SDK defaults) cause premature `ReadTimeout` exceptions before Gemini responds.
2. Users running CLI commands experience a silent, frozen terminal and may kill the process with Ctrl+C, assuming the app is hung.
3. If users do cancel with Ctrl+C, an unhandled `KeyboardInterrupt` dumps a messy Python traceback.

### Decision
1. **Extended Client HTTP Timeout**:
   - For `service_tier == "flex"`, set the client HTTP timeout to **900 seconds (15 minutes / 900,000 ms)** via `types.HttpOptions(timeout=...)`.
   - Make the timeout configurable via `GEMINI_FLEX_TIMEOUT_SECONDS` (default: 900) in environment / `.env`.
   - Standard requests retain the default interactive timeout (120 seconds / 120,000 ms).
2. **Upfront Informational Notice**:
   - Before dispatching a flex API request, emit a prominent CLI notice:
     `"Connecting to Gemini via Flex tier (50% cost savings). Flex tier uses opportunistic capacity; response turnaround is typically 1–15 minutes. Please wait..."`
3. **Graceful User Interruption (SIGINT / Ctrl+C)**:
   - Catch `KeyboardInterrupt` cleanly in CLI handlers and long-running loops.
   - Display: `"Operation canceled by user."`
   - Exit cleanly with standard interrupt exit code `130`.
4. **Timeout Diagnostics**:
   - If a request times out after the configured duration, catch the exception and categorize it as `category="flex-timeout"`.
   - Actionable message: `"Gemini flex tier request timed out after X seconds due to high capacity queueing. Retry later or run in standard mode using --no-flex."`

### Rationale
- **Constitution Principle I (User-Centricity & Understandability)**: Clearly explains why the request takes minutes and prevents user panic.
- **Constitution Principle IX (CLI Ergonomics & Friction Reduction)**: Eliminates Python tracebacks on Ctrl+C and provides immediate recovery guidance.
- Eliminates premature network socket drops during normal flex queueing.

### Alternatives Considered
- **Relying on SDK default timeout**: Rejected because SDK default will disconnect after 30-60s, causing almost all non-instant flex requests to fail.
- **Asynchronous polling / webhooks**: Over-engineered for a CLI application; synchronous blocking with a 15-minute timeout and clear status feedback matches the CLI architecture cleanly.

---

## 7. Configurable Fallback to Standard Tier on Flex Capacity Exhaustion

### Problem Context
Flex tier relies on opportunistic spare capacity and frequently encounters acute demand spikes resulting in HTTP 503 Service Unavailable ("This model is currently experiencing high demand...") or HTTP 429 Resource Exhausted. While progressive backoff retries help wait out brief spikes, unattended workflows (cron/schedulers) and long batch operations need an automated way to complete successfully when flex capacity remains unavailable. However, automatically switching to standard tier by default would violate Constitution Principle VI (AI Cost & Token Efficiency) by billing users at full price without their explicit consent.

### Decision
Provide an explicit, opt-in fallback setting:
- **CLI Flags**: `--flex-fallback-standard / --no-flex-fallback-standard` across `recommend`, `radio`, and `organize`.
- **Environment Variable**: `GEMINI_FLEX_FALLBACK_STANDARD=true/false` in `.env` / environment.
- **Default**: `False` (maintains strict cost protection by default).
- **Execution Mechanism**:
  1. Requests run on `flex` tier with progressive backoff retries (up to 5 retries by default).
  2. If flex capacity remains unavailable (503, 429, or timeout) and the fallback setting is `False`, the system fails fast with actionable guidance.
  3. If the fallback setting is `True`, the system catches the capacity exhaustion, logs a prominent warning:
     `[WARNING] Gemini flex capacity unavailable (HTTP 503 demand spike). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).`
  4. The request re-dispatches under `service_tier="standard"` with standard interactive timeout (120s) and succeeds.

### Rationale
- Balances automation reliability (Constitution Principle II) with cost protection (Constitution Principle VI).
- Users who need high availability can opt in globally or per command, while cost-conscious users remain protected against accidental charges.
- Clear warning logs preserve complete billing transparency.

### Alternatives Considered
- **Always fallback automatically without a setting**: Rejected because users choosing flex specifically to save 50% on large operations would be charged full standard pricing without consent.
- **Interactive prompt during execution**: Infeasible for unattended batch and cron workflows (Constitution Principle II).

---

## 8. Multi-Batch Sticky Fallback Semantics (`tde organize`)

### Problem Context
In `tde organize`, large libraries with dozens of unclassified tracks are processed in batches (e.g. 50 tracks per batch). If flex capacity is unavailable, forcing every subsequent batch to attempt flex first and wait through progressive retries (~2+ minutes per batch) would result in immense latency (e.g., 20 batches × 2 min = 40+ minutes of waiting before finishing on standard tier).

### Decision
Implement "sticky fallback" for multi-batch operations:
- When a batch exhausts flex capacity and triggers fallback to standard tier, all subsequent batches within that single command execution run directly on standard tier without attempting flex tier again.
- Future separate command runs still start on flex tier as configured.

### Rationale
- Drastically reduces execution latency during provider capacity outages while ensuring library sync runs to completion.
- Aligns with user expectation that once flex tier is recognized as unavailable, the ongoing job should finish promptly.

### Alternatives Considered
- **Re-attempt flex on every batch**: Rejected because it causes massive repetitive retry delays across every single batch during prolonged demand spikes.

