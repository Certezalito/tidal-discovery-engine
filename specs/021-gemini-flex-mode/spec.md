# Feature Specification: Gemini Flex Mode Support

**Feature Branch**: `021-gemini-flex-mode`

**Created**: 2026-10-07

**Updated**: 2026-10-09

**Status**: Draft

**Input**: User description: "need to revise the spec, flex tends to have alot of 503 errors, need to have a setting for fallback to standard when flex is unavaiable."

## Clarifications

### Session 2026-10-07

- Q: When Gemini flex tier requests fail due to capacity shedding or resource exhaustion, how should the application handle the failure? (FR-008) → A: Fail fast with actionable guidance (Option A: preserves strict cost protection; advises users to retry or rerun in standard mode without silently incurring standard tier charges).
- Q: How should the command-line interface allow users to force the standard tier when GEMINI_SERVICE_TIER=flex is configured in the environment? (FR-004) → A: Support `--flex / --no-flex` boolean flags (Option A: `--no-flex` explicitly forces the standard tier, overriding `GEMINI_SERVICE_TIER` in `.env`).
- Q: Should the library genre organization command (`tde organize`) support explicit `--flex / --no-flex` command-line flags alongside `recommend` and `radio`? (FR-009) → A: Add `--flex / --no-flex` to `tde organize` (Option A: full CLI flag consistency across all Gemini-enabled commands).
- Q: How should the application handle extended response times and variable latency inherent to the flex tier? (FR-011, FR-012, FR-013) → A: Configure a generous default HTTP client timeout (15 minutes / 900 seconds, configurable via `GEMINI_FLEX_TIMEOUT_SECONDS`), display an upfront informational notice setting user expectations for variable response times (typically 1–15 minutes), handle SIGINT (Ctrl+C) gracefully, and provide actionable timeout diagnostics if the limit is exceeded.

### Session 2026-10-08

- Q: How should the system confirm that flex mode is active during operations that involve flex mode? (FR-015, FR-016) → A: Explicit confirmation in application logs (at INFO level recording active service tier, source, and timeout for every Gemini request) and user-facing terminal notices/output confirming flex mode engagement and successful execution.

### Session 2026-10-09

- Q: When flex tier encounters persistent capacity constraints or 503/429 errors after retries, how should the fallback-to-standard setting behave? (FR-008, FR-017, FR-018, FR-019, FR-020, FR-021) → A: Support an opt-in configurable fallback setting via CLI (`--flex-fallback-standard / --no-flex-fallback-standard`) and environment variable (`GEMINI_FLEX_FALLBACK_STANDARD=true/false`). By default, fallback is disabled (`false`) to preserve strict cost protection (Principle VI); when enabled, the system automatically falls back to standard tier inference upon exhausting flex capacity, logging a clear warning so the user knows standard billing was used.
- Q: In multi-batch library organization (`tde organize`), how should fallback to standard tier apply to subsequent track batches once a batch exhausts flex capacity? (FR-017, FR-022) → A: Sticky for remainder of run (Option A: once a batch exhausts flex capacity and falls back to standard tier, all remaining batches in that execution run directly on standard tier without re-attempting flex, avoiding repeated multi-minute retry delays per batch).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cost-Optimized Playlist Generation with Flex Mode (Priority: P1)

As a music listener generating playlist recommendations using Gemini AI, I want to enable Flex mode via a command-line flag (`--flex`), so that I can significantly reduce AI token costs by utilizing the discounted, latency-tolerant service tier when real-time response speed is not critical.

**Why this priority**: Directly satisfies the core user requirement to retrieve recommendations from Gemini using flex mode, providing immediate cost savings for discovery runs.

**Independent Test**: Execute `tde recommend --gemini --flex` with valid credentials, verify that recommendation retrieval succeeds, that the request routes via the flex service tier, and that tracks are added to the created playlist.

**Acceptance Scenarios**:

1. **Given** a user invokes `tde recommend --gemini --flex`, **When** the system retrieves recommendations, **Then** the request is dispatched using the flex service tier and valid track recommendations are returned.
2. **Given** a user invokes `tde recommend --gemini` without `--flex` and without `GEMINI_SERVICE_TIER=flex`, **When** the system retrieves recommendations, **Then** the request is dispatched using the default standard tier.
3. **Given** a user passes `--flex` or `--no-flex` to `tde recommend` without `--gemini`, **When** the command arguments are validated, **Then** the system rejects execution with a clear, actionable error stating that `--flex` and `--no-flex` require `--gemini`.
4. **Given** a user invokes `tde recommend --gemini --flex`, **When** the operation executes, **Then** application logs explicitly confirm that the Gemini operation is executing in flex tier (recording tier name, source, and timeout), and terminal output provides visible confirmation that flex mode is active.

---

### User Story 2 - Single-Seed Radio Generation with Flex Mode (Priority: P2)

As a user curating a radio playlist from an artist and track seed with Gemini AI, I want to provide the `--flex` flag on the radio command, so that single-seed track discovery also benefits from lower token pricing.

**Why this priority**: Maintains feature parity across all recommendation generation commands in the CLI, ensuring users have consistent access to flex mode regardless of which command they use.

**Independent Test**: Execute `tde radio --artist "<artist>" --track "<track>" --gemini --flex`, verify the playlist is created with recommendations retrieved under the flex service tier.

**Acceptance Scenarios**:

1. **Given** a user invokes `tde radio` with `--artist`, `--track`, `--gemini`, and `--flex`, **When** the command executes, **Then** the system queries Gemini using the flex tier and generates the single-seed radio playlist.
2. **Given** a user invokes `tde radio` with `--flex` or `--no-flex` but omits `--gemini`, **When** argument validation executes, **Then** the command exits with an actionable error indicating that `--flex` and `--no-flex` require `--gemini`.
3. **Given** a user invokes `tde radio` in flex mode, **When** recommendations are retrieved, **Then** application logs explicitly confirm that the Gemini operation is executing in flex tier (recording tier name, source, and timeout), and terminal output provides visible confirmation that flex mode is active.

---

### User Story 3 - Cost-Effective Library Genre Organization with Flex Mode (Priority: P3)

As a user organizing a large Tidal library into genre playlists, I want to pass `--flex` to `tde organize`, so that high-volume batch track classifications run at half the standard token cost.

**Why this priority**: Library genre organization processes large volumes of tracks in batches, representing the highest potential token usage in the application.

**Independent Test**: Execute `tde organize --flex --limit 10`, verify that batch genre classification queries route through the flex service tier.

**Acceptance Scenarios**:

1. **Given** a user invokes `tde organize --flex`, **When** Gemini classifies unclassified track batches, **Then** each classification request is dispatched using the flex service tier.
2. **Given** `GEMINI_SERVICE_TIER=flex` is set in `.env`, **When** a user runs `tde organize --no-flex`, **Then** the system overrides the environment setting and classifies tracks using the standard tier.
3. **Given** a user invokes `tde organize --flex`, **When** unclassified track batches are processed, **Then** application logs confirm each batch query is routed through flex tier, and terminal output confirms flex tier execution.

---

### User Story 4 - Global Flex Mode Configuration & CLI Override (Priority: P4)

As an automated user or administrator running scheduled background jobs (e.g., cron workflows), I want to configure the default Gemini service tier via an environment variable (`GEMINI_SERVICE_TIER=flex`) and selectively override it using `--no-flex`, so that batch tasks save costs automatically while urgent interactive runs can force standard tier execution.

**Why this priority**: Enables unattended cost savings for automated workflows without requiring modifications to existing command scripts, while preserving CLI control for ad-hoc runs.

**Independent Test**: Set `GEMINI_SERVICE_TIER=flex` in `.env`, run `tde recommend --gemini` without flags to confirm flex mode is used, then run `tde recommend --gemini --no-flex` to confirm standard tier is forced.

**Acceptance Scenarios**:

1. **Given** `GEMINI_SERVICE_TIER` is configured to `flex`, **When** a user runs a Gemini-backed command without tier flags, **Then** the system automatically applies the flex service tier.
2. **Given** `GEMINI_SERVICE_TIER=flex` is set, **When** a user passes `--no-flex` with `--gemini`, **Then** the system overrides the environment setting and dispatches the request using the standard tier.
3. **Given** `GEMINI_SERVICE_TIER` is set to an unsupported value, **When** a Gemini request is initiated, **Then** the system logs a warning and falls back safely to the standard tier without crashing.
4. **Given** `GEMINI_SERVICE_TIER` is set to `flex` with surrounding whitespace or uppercase letters, **When** parsed, **Then** the system normalizes the value cleanly.

---

### User Story 5 - Transparent Liveness Feedback & Extended Timeout for Flex Latency (Priority: P5)

As an interactive or automated user running commands in flex mode, I want upfront notice of expected latency, an extended client-side timeout (15 minutes), and clean cancellation handling (Ctrl+C), so that I know the CLI is actively waiting rather than hung, requests do not abort prematurely, and I can cancel cleanly if needed.

**Why this priority**: Flex tier operates on opportunistic off-peak capacity with variable turnaround times (1 to 15 minutes). Without clear feedback and adjusted timeouts, users perceive the CLI as hung or suffer unexpected connection drops.

**Independent Test**: Trigger a flex mode retrieval and verify that an upfront informational notice appears, the client HTTP timeout is configured to 900 seconds, pressing Ctrl+C exits cleanly without a traceback, and exceeding the timeout produces an actionable diagnostic message.

**Acceptance Scenarios**:

1. **Given** a command runs with flex mode active, **When** the Gemini API call is prepared, **Then** the system outputs a clear informational notice explaining that flex mode uses opportunistic capacity and may take 1 to 15 minutes to complete.
2. **Given** a flex request takes several minutes, **When** waiting for Gemini's response, **Then** the client connection remains open and does not terminate before the configured flex timeout (default 900 seconds).
3. **Given** a user cancels an in-flight flex request via SIGINT (Ctrl+C), **When** interrupted, **Then** the system terminates gracefully with a concise cancellation message and standard exit status (130).
4. **Given** a flex request exceeds the configured timeout duration, **When** the timeout triggers, **Then** the system outputs an actionable error explaining that the flex tier is experiencing extended queueing and advises retrying or using standard mode.
5. **Given** any operation executing in flex mode completes, **When** recommendations or classifications are received, **Then** application logs confirm successful completion under flex tier turnaround.

---

### User Story 6 - Graceful Feedback on Flex Tier Capacity Constraints (Priority: P6)

As a user running commands in flex mode with fallback disabled, I want clear diagnostic feedback if Gemini flex capacity is temporarily exhausted or preempted, so that I understand why the request failed and receive actionable guidance on how to proceed without incurring unprompted standard billing.

**Why this priority**: Flex tier operates on best-effort availability and is subject to capacity preemption. Informative feedback prevents confusion and empowers users to switch to standard mode when immediate completion is required.

**Independent Test**: Simulate a capacity shedding error on a flex tier request after retries with fallback disabled, and verify that the CLI outputs an informative message suggesting a retry or running without `--flex`.

**Acceptance Scenarios**:

1. **Given** a flex mode request encounters capacity shedding or rate limit errors and standard fallback is disabled, **When** recovery retries are exhausted, **Then** the system reports an actionable error explaining that flex capacity is constrained, advises retrying or running in standard mode, and strictly avoids unprompted standard billing.
2. **Given** a flex mode request experiences a transient error, **When** an automatic recovery retry succeeds, **Then** execution continues uninterrupted.

---

### User Story 7 - Configurable Fallback to Standard Tier on Flex Unavailable (Priority: P2)

As an automated user running scheduled tasks or an interactive user organizing large libraries, I want to configure an explicit fallback setting (`--flex-fallback-standard` or `GEMINI_FLEX_FALLBACK_STANDARD=true`), so that when opportunistic flex capacity experiences persistent demand spikes (HTTP 503) or rate-limit shedding (HTTP 429) after recovery retries, the operation automatically completes using standard tier capacity instead of aborting the run.

**Why this priority**: Flex tier frequently encounters 503 high-demand errors during busy inference hours. Users who prioritize run completion and reliability over absolute cost savings need an automated fallback to standard capacity without manual intervention, while cost-sensitive users remain protected by keeping fallback disabled by default.

**Independent Test**: Enable `--flex-fallback-standard` (or `GEMINI_FLEX_FALLBACK_STANDARD=true`), simulate flex capacity exhaustion after retries, and verify that the system issues a warning log and transparently completes using the standard tier.

**Acceptance Scenarios**:

1. **Given** flex mode is active and the fallback setting is enabled (`--flex-fallback-standard` or `GEMINI_FLEX_FALLBACK_STANDARD=true`), **When** flex capacity is exhausted after recovery retries (due to HTTP 503 demand spikes, HTTP 429 capacity shedding, or flex timeout), **Then** the system automatically transitions the request to standard tier inference, logs a clear warning explaining the fallback, and completes the operation.
2. **Given** flex mode is active and the fallback setting is disabled (the default `false`), **When** flex capacity is exhausted after recovery retries, **Then** the system terminates with actionable guidance without querying standard tier, strictly preventing unprompted standard billing.
3. **Given** flex fallback is enabled and flex capacity is available, **When** the operation executes, **Then** the request completes at flex pricing and standard tier inference is not invoked.
4. **Given** `GEMINI_FLEX_FALLBACK_STANDARD=true` is set in the environment, **When** a user passes `--no-flex-fallback-standard` via the CLI, **Then** the CLI flag overrides the environment setting, disabling fallback to standard tier for that run.
5. **Given** a batch organization command (`tde organize`) is running with flex and fallback enabled, **When** an individual track batch encounters exhausted flex capacity, **Then** the system falls back to standard tier for that batch, records the fallback transition in logs, and executes all subsequent batches in that run directly on standard tier (sticky fallback) to complete the library synchronization without repeated multi-minute delays.

---

### Edge Cases

- **Flex Mode with Deep Cuts**: User supplies both `--flex` and `--shuffle` with `--gemini`. The system combines deep-cut prompt instructions with flex tier request routing without conflict.
- **Environment Variable with Non-Gemini Commands**: `GEMINI_SERVICE_TIER=flex` or `GEMINI_FLEX_FALLBACK_STANDARD=true` is present in `.env`, but user runs `tde recommend` with default Last.fm provider. The environment variables are ignored without error.
- **Explicit Override Precedence for Service Tier**: User sets `GEMINI_SERVICE_TIER=standard` in `.env` but passes `--flex` on CLI: `--flex` wins and flex tier is used. Conversely, user sets `GEMINI_SERVICE_TIER=flex` but passes `--no-flex`: `--no-flex` wins and standard tier is used.
- **Explicit Override Precedence for Fallback Setting**: User sets `GEMINI_FLEX_FALLBACK_STANDARD=true` in `.env` but passes `--no-flex-fallback-standard` on CLI: `--no-flex-fallback-standard` wins and fallback is disabled. Conversely, user sets `GEMINI_FLEX_FALLBACK_STANDARD=false` in `.env` but passes `--flex-fallback-standard` on CLI: `--flex-fallback-standard` wins and fallback is enabled.
- **Sticky Fallback across Batches in Single Run**: In `tde organize`, once any batch triggers standard tier fallback, all subsequent batches within that execution run directly on standard tier without attempting flex tier again. Future separate command runs still start on flex tier as configured.
- **Fallback Setting Combined with Non-Flex Invocation**: User passes `--flex-fallback-standard` without flex mode active (e.g. standard tier default): Fallback setting is ignored since the request already runs on standard tier.
- **Custom Timeout and Retry Configuration**: User sets `GEMINI_FLEX_TIMEOUT_SECONDS=600` or `GEMINI_FLEX_MAX_RETRIES=8`: System honors custom timeouts and retry counts before evaluating fallback or terminal failure.
- **API Key Missing with Flex Mode**: User provides `--flex` and `--gemini` but `GEMINI_API_KEY` is not set. System fails immediately with standard guidance indicating that `GEMINI_API_KEY` is required.
- **Model Fallback Combined with Tier Fallback**: If a primary model fails with flex capacity exhaustion and tier fallback is enabled, the request retries under standard tier with the primary model first before considering model fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `--flex / --no-flex` flags on the `recommend` command to control Gemini recommendation request routing through the flex service tier.
- **FR-002**: System MUST provide `--flex / --no-flex` flags on the `radio` command to control Gemini single-seed recommendation request routing through the flex service tier.
- **FR-003**: System MUST support configuring the Gemini service tier via a `GEMINI_SERVICE_TIER` environment variable and `.env` file entry, recognizing `flex` and `standard`.
- **FR-004**: Explicit command-line flags (`--flex` or `--no-flex`) MUST override environment variable configuration (`--flex` forces flex tier; `--no-flex` forces standard tier even if `GEMINI_SERVICE_TIER=flex` is set).
- **FR-005**: If neither CLI tier flags nor `GEMINI_SERVICE_TIER` is provided, the system MUST default to the `standard` tier to preserve existing performance and behavior.
- **FR-006**: The system MUST reject invocations containing `--flex`, `--no-flex`, `--flex-fallback-standard`, or `--no-flex-fallback-standard` without `--gemini` on commands where Gemini is optional (`recommend`, `radio`), outputting a clear, flag-specific error stating that the flag requires `--gemini`.
- **FR-007**: When flex mode is active, the system MUST configure Gemini API calls with the flex tier routing parameter.
- **FR-008**: If a flex mode request fails due to capacity preemption, resource exhaustion, rate limiting (HTTP 503 / 429), or timeout after recovery retries:
  - If fallback to standard tier is enabled (`--flex-fallback-standard` or `GEMINI_FLEX_FALLBACK_STANDARD=true`), the system MUST automatically transition the request to standard tier inference, log a warning detailing the fallback, and continue execution.
  - If fallback to standard tier is disabled (default), the system MUST fail fast with actionable guidance advising the user to retry later or execute in standard mode, strictly prohibiting unprompted standard billing.
- **FR-009**: System MUST provide `--flex / --no-flex` flags on the `organize` (and alias `genre-organizer`) command to control Gemini service tier routing during batch track genre classification, with identical override precedence over `GEMINI_SERVICE_TIER`.
- **FR-010**: All new CLI flags, environment variables, default behaviors, and usage examples for flex mode and fallback to standard tier MUST be documented in `README.md`.
- **FR-011**: When flex mode is active, the system MUST configure an extended HTTP client timeout of at least 15 minutes (900 seconds) by default, configurable via the `GEMINI_FLEX_TIMEOUT_SECONDS` environment variable, to accommodate opportunistic capacity turnaround.
- **FR-012**: The system MUST output an informational notice before initiating flex tier requests, informing the user that flex mode operates on opportunistic capacity with variable latency (typically 1 to 15 minutes).
- **FR-013**: The system MUST cleanly handle user interruption (SIGINT / Ctrl+C) during long-running flex requests without printing Python stack traces, outputting a clear cancellation message and exiting with standard interrupt status code 130.
- **FR-014**: If a flex mode request times out and fallback to standard tier is disabled, the system MUST catch the timeout and output an actionable diagnostic message explaining the extended latency and advising the user to retry later or use standard mode.
- **FR-015**: The system MUST emit structured informational log messages confirming the active Gemini service tier (`tier=flex` or `tier=standard`), configuration source (`cli`, `env`, `dotenv`, or `default`), and configured timeout whenever a Gemini operation is initiated.
- **FR-016**: For all operations executing under flex mode (`recommend`, `radio`, `organize`), the system MUST provide explicit confirmation in logs and terminal notices that flex mode was utilized during the run.
- **FR-017**: System MUST provide a configurable setting to allow automatic fallback to the standard tier when flex tier capacity is unavailable due to demand spikes (HTTP 503), capacity shedding (HTTP 429), or timeout after recovery retries.
- **FR-018**: System MUST provide `--flex-fallback-standard / --no-flex-fallback-standard` boolean flags across all Gemini-enabled commands (`recommend`, `radio`, and `organize` / `genre-organizer`).
- **FR-019**: System MUST support configuring the flex fallback setting via a `GEMINI_FLEX_FALLBACK_STANDARD` environment variable and `.env` entry, recognizing boolean representations (`true`, `false`, `1`, `0`, `yes`, `no`).
- **FR-020**: The default value for the flex fallback setting MUST be disabled (`false`) to guarantee cost protection against unexpected standard tier charges unless explicitly enabled by the user.
- **FR-021**: Whenever a request falls back from flex tier to standard tier, the system MUST emit a clear warning log message indicating that flex capacity was unavailable and standard tier inference is being used.
- **FR-022**: In multi-batch operations (`tde organize`), once flex capacity is exhausted and fallback to standard tier is triggered for a batch, the system MUST keep standard tier active for all subsequent batches within that run ("sticky fallback") to prevent repeated retry delays.

### Key Entities

- **Service Tier Setting**: The configured operational tier for Gemini API requests (`standard` or `flex`), controlling request priority, billing tier, and latency characteristics.
- **Flex Fallback Setting**: A boolean configuration determining whether the system automatically falls back to standard tier inference when flex tier capacity is exhausted.
- **Gemini Request Configuration**: The comprehensive request payload comprising model selection, prompt instructions, structured response schema, tier routing parameters, and timeout settings.
- **Diagnostic Result**: Actionable error categorizations and next-step recommendations returned when API requests encounter authentication, capacity, timeout, or configuration errors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can activate or deactivate flex mode for Gemini recommendation retrieval using a single CLI flag (`--flex` or `--no-flex`).
- **SC-002**: 100% of Gemini API requests initiated with flex mode enabled include the flex tier routing configuration across `recommend`, `radio`, and `organize` commands.
- **SC-003**: 100% backward compatibility for all existing commands and workflows when flex mode is not activated.
- **SC-004**: Input validation failure for `--flex` or `--no-flex` without `--gemini` terminates execution and displays actionable syntax guidance in under 1 second.
- **SC-005**: User-facing documentation in `README.md` includes clear examples of CLI usage, latency characteristics, environment variable configuration, and the standard fallback setting for flex mode.
- **SC-006**: 100% of flex tier requests configure an HTTP client timeout of at least 900 seconds (or the value set by `GEMINI_FLEX_TIMEOUT_SECONDS`), eliminating premature client-side disconnects.
- **SC-007**: When flex mode is active, the CLI outputs an informational waiting notice within 1 second of command dispatch.
- **SC-008**: 100% of operations invoked in flex mode log explicit confirmation of flex tier usage, source, and timeout at INFO level, enabling immediate operational auditability.
- **SC-009**: When flex fallback to standard is enabled (`--flex-fallback-standard` or `GEMINI_FLEX_FALLBACK_STANDARD=true`) and flex capacity is exhausted, 100% of failed requests seamlessly recover on standard tier without terminating execution.
- **SC-010**: When flex fallback to standard is disabled (default), 0% of failed flex requests silently execute on standard tier, maintaining 100% adherence to default cost protection.
- **SC-011**: 100% of fallback transitions emit a visible warning log message detailing the shift from opportunistic flex to standard tier billing.

## Assumptions

- The Gemini API and model configured in the application support the flex service tier.
- Flex mode requests are latency-tolerant and may experience turnaround times between 1 and 15 minutes in exchange for reduced token costs.
- Users who activate flex mode prioritize cost efficiency over immediate response time.
- Flex tier requests execute progressive recovery retries (up to 5 retries by default, configurable via `GEMINI_FLEX_MAX_RETRIES`) before triggering capacity exhaustion or standard fallback.
- By default, strict fail-fast cost protection applies to flex requests before reporting capacity exhaustion. Users may opt into automatic standard tier fallback via configuration or CLI flags.
- Default behavior remains standard tier so existing workflows experience no change in latency or availability unless explicitly configured.
