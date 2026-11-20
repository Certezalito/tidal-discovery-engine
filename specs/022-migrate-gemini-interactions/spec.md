# Feature Specification: Migrate to Current Gemini Interaction Method

**Feature Branch**: `023-migrate-gemini-interactions`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "i want a new feature that migrates this project to the current method for interacting with gemini"

## Clarifications

### Session 2026-11-19

- Q: Which current-generation Gemini model should be used as the built-in default when `GEMINI_MODEL` is not set? (FR-006) → A: Retain `gemini-flash-latest` as the built-in default across all commands (`recommend`, `radio`, and `organize`), keeping existing default model behavior unchanged.
- Q: How should the tool respond when a user's configuration specifies a deprecated legacy Gemini model (such as `gemini-1.5-*`, `gemini-2.0-*`, or `gemini-2.5-*`)? (FR-007) → A: Automatically substitute `gemini-flash-latest` and log a warning advising the user to update their configuration (Option A).
- Q: Should Gemini requests opt out of server-side interaction history storage (which Gemini enables by default for up to 55 days on paid tiers)? (FR-009) → A: Always disable server-side interaction storage on every request (strictly stateless and privacy-first) (Option A).
- Q: How should the tool control Gemini's internal reasoning effort (thinking tokens) on current-generation models? → A: Use higher reasoning effort (`medium`) for creative recommendations (`recommend` and `radio`) and `minimal` reasoning effort for high-volume batch genre classification (`organize`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamless Playlist & Radio Discovery with Current Gemini Interface (Priority: P1)

As a music listener using Gemini AI to generate personalized playlists or single-seed radio stations, I want song recommendations to be retrieved through Google's current Gemini interaction method, so that my music discovery workflows remain operational, accurate, and supported as older Gemini request methods and models are retired.

**Why this priority**: Playlist and radio recommendation generation are core discovery capabilities of Tidal Discovery Engine; if the underlying Gemini communication method becomes obsolete, AI-driven playlist creation stops working entirely.

**Independent Test**: Run `tde recommend --gemini` and `tde radio --artist "<artist>" --track "<track>" --gemini` (both standard and `--shuffle` deep-cuts modes) with valid credentials and verify that playlists are created on Tidal with valid, non-hallucinated tracks matching the requested count.

**Acceptance Scenarios**:

1. **Given** valid Tidal and Gemini credentials, **When** a user runs `tde recommend --gemini`, **Then** the system retrieves structured artist-and-title recommendations via the current Gemini interaction method, resolves them against the Tidal catalog, and creates the target playlist.
2. **Given** valid Tidal and Gemini credentials, **When** a user runs `tde recommend --gemini --shuffle`, **Then** the system requests lesser-known "deep cut" recommendations via the current Gemini interaction method and populates the playlist accordingly.
3. **Given** valid Tidal and Gemini credentials, **When** a user runs `tde radio --artist "<artist>" --track "<track>" --gemini`, **Then** the system places the seed track at position #1 and populates the remaining tracks using recommendations from the current Gemini interaction method.
4. **Given** a Gemini recommendation run, **When** recommendations are returned by the AI service, **Then** every recommendation contains human-readable artist and track title attributes only, without relying on AI-generated catalog or recording codes.

---

### User Story 2 - Uninterrupted Library Genre Organization (Priority: P2)

As a user organizing my Tidal favorites into genre playlists, I want batch track genre classification to use Google's current Gemini interaction method while preserving my existing local genre cache, so that newly added tracks continue to be categorized accurately without incurring redundant AI costs for already-classified songs.

**Why this priority**: Library genre organization processes entire music libraries in batches and is the highest-volume AI workflow in the tool; preserving both accuracy and existing cached classifications protects users from unexpected costs and playlist disruption.

**Independent Test**: Run `tde organize` against a library containing both previously cached tracks and uncached tracks, and verify that cached tracks are reused at zero AI token cost while uncached tracks are classified into one specific primary genre and up to three sub-genres using the current Gemini interaction method.

**Acceptance Scenarios**:

1. **Given** a user's Tidal library contains uncached tracks, **When** the user runs `tde organize`, **Then** the system classifies only the uncached tracks via the current Gemini interaction method, assigning each track one specific primary genre and up to three specific sub-genres, and syncs the resulting genre playlists.
2. **Given** a user has an existing local genre cache from prior runs, **When** the user runs `tde organize` after the migration without `--refresh-genres`, **Then** all previously valid cached classifications are reused without re-querying Gemini.
3. **Given** a user runs `tde organize --refresh-genres`, **When** full re-classification executes, **Then** all library tracks are re-classified through the current Gemini interaction method and updated in the local cache.

---

### User Story 3 - Preserved Default Model & Smooth Configuration Upgrade (Priority: P2)

As an interactive user or administrator running scheduled discovery jobs, I want the tool to keep `gemini-flash-latest` as the built-in default when `GEMINI_MODEL` is unset and gracefully handle legacy deprecated model names in existing configuration files, so that automated jobs continue running without manual intervention while automatically tracking Google's latest Flash model.

**Why this priority**: Retaining `gemini-flash-latest` avoids forcing users to update model pins as newer Flash releases ship, while safeguarding existing configurations that reference retired model generations (`1.5`, `2.0`, `2.5`) prevents silent breakage in unattended cron or Task Scheduler setups.

**Independent Test**: Run a Gemini-enabled command with `GEMINI_MODEL` unset (verifying `gemini-flash-latest` is selected), with `GEMINI_MODEL` set to a deprecated legacy identifier (verifying documented legacy-model handling), and with an unavailable custom model plus `GEMINI_FALLBACK_MODEL` set (verifying automatic fallback).

**Acceptance Scenarios**:

1. **Given** `GEMINI_MODEL` is unset, blank, or set to a generic alias (`latest`, `auto`, or `flash-latest`), **When** a Gemini-enabled command executes, **Then** the system selects `gemini-flash-latest` as the target model.
2. **Given** `GEMINI_MODEL` (or `GEMINI_FALLBACK_MODEL`) is set to a deprecated legacy Gemini model (`gemini-1.5-*`, `gemini-2.0-*`, or `gemini-2.5-*`), **When** a Gemini-enabled command executes, **Then** the system automatically substitutes `gemini-flash-latest` and emits a clear warning advising the user to update their model configuration.
3. **Given** `GEMINI_MODEL` is set to a custom model identifier that is unavailable or not found and `GEMINI_FALLBACK_MODEL` is configured to an available model, **When** the primary request fails due to model unavailability, **Then** the system logs a warning and completes the operation using `GEMINI_FALLBACK_MODEL`.
4. **Given** `tde radio --gemini` is invoked and the configured Gemini model (and any configured Gemini fallback model) is unavailable, **When** Gemini retrieval fails due to model unavailability, **Then** the command logs a warning and gracefully falls back to Last.fm recommendations.

---

### User Story 4 - Preserved Cost Controls, Flex Mode & Actionable Diagnostics (Priority: P3)

As a cost-conscious or unattended automation user, I want all existing CLI flags, service-tier cost controls (`--flex` / `--no-flex`, `GEMINI_SERVICE_TIER`), opt-in standard fallback (`--flex-fallback-standard`), timeout settings, cancellation handling, and actionable error messages to work identically after the migration, so that I do not have to rewrite scripts or risk unexpected billing.

**Why this priority**: Users rely on established CLI ergonomics, cron schedules, and strict Flex-tier cost protection; a migration must modernize how the tool communicates with Gemini without regressing operational guarantees.

**Independent Test**: Execute Gemini-backed commands with `--flex`, `--no-flex`, and `--flex-fallback-standard`, simulate transient capacity or authentication errors, and confirm that waiting notices, timeouts, sticky batch fallback, and categorized error messages match documented behavior.

**Acceptance Scenarios**:

1. **Given** a user invokes `recommend`, `radio`, or `organize` with `--flex` (or `GEMINI_SERVICE_TIER=flex`), **When** the Gemini interaction is dispatched, **Then** the system displays the upfront latency notice, applies the extended flex timeout, logs periodic progress notices while waiting, and routes the request under the flex service tier.
2. **Given** flex mode is active with standard fallback disabled (default) and flex capacity is exhausted after progressive retries, **When** the request fails, **Then** the system aborts with actionable guidance without incurring standard-tier charges.
3. **Given** flex mode is active with standard fallback enabled (`--flex-fallback-standard` or `GEMINI_FLEX_FALLBACK_STANDARD=true`) and flex capacity is exhausted after retries, **When** fallback triggers, **Then** the system logs a clear warning, completes the request on the standard tier, and keeps standard tier active for any remaining batches in that run.
4. **Given** a user interrupts an active Gemini wait with `Ctrl+C`, **When** the cancellation signal is received, **Then** the CLI exits cleanly with a concise cancellation message and exit code `130` without raw error tracebacks.

---

### Edge Cases

- **Deprecated Legacy Model Configured**: If an existing `.env` or environment variable specifies a retired or deprecated `gemini-1.5-*`, `gemini-2.0-*`, or `gemini-2.5-*` model, the system substitutes `gemini-flash-latest` and logs a visible warning so scheduled jobs do not break unexpectedly.
- **Empty, Incomplete, or Safety-Blocked AI Output**: If Gemini returns an empty interaction output, missing artist/title fields, or a blocked/incomplete completion status, the system performs one automatic recovery retry and, if still unusable, exits with a categorized `response-handling` diagnostic message rather than creating an empty playlist.
- **Unsupported Legacy Sampling Controls on Current Models**: Requests to current-generation Gemini models must not send retired generation tuning parameters that cause validation errors or degraded output quality.
- **Sticky Tier Fallback Across Multi-Batch Organization**: During `tde organize`, if one batch exhausts flex capacity and falls back to standard tier (when opt-in fallback is enabled), all subsequent batches in the same execution run directly on standard tier without repeating multi-minute flex retry cycles.
- **Missing or Invalid Credentials**: When `GEMINI_API_KEY` is missing, empty, or rejected for authentication/permission reasons, the system fails immediately without retrying or triggering fallback models, outputting actionable credential guidance.
- **Non-Gemini Workflows Unaffected**: Running `tde recommend` or `tde radio` without `--gemini` (using default Last.fm discovery) or running `tde organize --wipe-only` executes without requiring or invoking Gemini.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST execute all Gemini AI requests across `recommend`, `radio`, and `organize` (including alias `genre-organizer`) using Google's current Gemini interaction method, completely retiring calls to the legacy content-generation interface.
- **FR-002**: System MUST preserve 100% backward compatibility for all existing CLI command names, aliases, options, flags, and environment variable names (`--gemini`, `--shuffle`, `--exclude-favorites`, `--flex` / `--no-flex`, `--flex-fallback-standard` / `--no-flex-fallback-standard`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `GEMINI_SERVICE_TIER`, `GEMINI_FLEX_TIMEOUT_SECONDS`, `GEMINI_FLEX_MAX_RETRIES`, `GEMINI_FLEX_FALLBACK_STANDARD`, and `GEMINI_SERVICE_TIER_FALLBACK`).
- **FR-003**: System MUST enforce structured output definitions on all Gemini interactions so that recommendation requests return only minimal artist-and-title song records and genre-classification requests return structured track genre records without extraneous conversational text.
- **FR-004**: System MUST NOT prompt for, request, or accept AI-generated International Standard Recording Codes (ISRCs) or synthetic catalog identifiers during recommendation generation; all recommended tracks MUST be resolved against Tidal exclusively via human-readable artist and title attributes.
- **FR-005**: For library organization (`organize`), the system MUST continue classifying each uncached track into exactly one specific primary genre (avoiding broad umbrella labels when a specific genre applies) and up to three specific sub-genres, maintaining full read/write compatibility with existing local genre cache records.
- **FR-006**: When `GEMINI_MODEL` is unset, blank, or set to a generic latest alias (`latest`, `auto`, or `flash-latest`), the system MUST resolve the primary model to `gemini-flash-latest`.
- **FR-007**: When `GEMINI_MODEL` or `GEMINI_FALLBACK_MODEL` specifies a deprecated legacy Gemini model family (`gemini-1.5-*`, `gemini-2.0-*`, or `gemini-2.5-*`), the system MUST automatically substitute `gemini-flash-latest` and emit a warning log noting the deprecated model and substitution.
- **FR-008**: System MUST send only generation configuration controls supported by current-generation Gemini models, omitting retired legacy sampling controls so requests succeed without parameter-compatibility errors.
- **FR-009**: System MUST execute all recommendation and batch classification requests as stateless, single-turn interactions and MUST explicitly disable server-side interaction storage on every Gemini request to protect user listening-history privacy.
- **FR-010**: System MUST preserve primary-to-fallback model recovery (`GEMINI_FALLBACK_MODEL`) when the primary model fails due to model unavailability or not-found errors, as well as automatic fallback to Last.fm in `radio --gemini` mode when no configured Gemini model is available.
- **FR-011**: System MUST preserve single-retry recovery for empty, malformed, or blocked AI responses and fail with an actionable `response-handling` diagnostic message if the retry also yields unusable output.
- **FR-012**: System MUST preserve full standard and flex service-tier behavior, including CLI override precedence over environment settings, upfront flex latency notices, periodic waiting heartbeats, configurable flex timeouts (default 900 seconds), progressive capacity retries, strict fail-fast cost protection by default, opt-in standard fallback (`--flex-fallback-standard`), and sticky standard fallback across remaining batches in `organize`.
- **FR-013**: System MUST preserve clean user cancellation handling (`Ctrl+C`) during in-flight Gemini interactions, printing a concise cancellation message and exiting with status code `130` without displaying raw stack traces.
- **FR-014**: System MUST classify Gemini interaction failures into clear, actionable user categories (`auth`, `permission`, `quota`, `unavailable/not-found`, `flex-capacity`, `flex-timeout`, `timeout`, `response-handling`, `server`, and `client`) with next-step remediation guidance.
- **FR-015**: Project documentation (`README.md` and `.env.example`) MUST be updated to reflect the current Gemini interaction method, the retained `gemini-flash-latest` default model, deprecated-model handling, and troubleshooting guidance while keeping setup and command examples accurate.
- **FR-016**: System MUST apply task-appropriate reasoning effort on current-generation Gemini models: `medium` reasoning effort for creative track recommendations (`recommend` and `radio`) and `minimal` reasoning effort for high-volume batch library genre classification (`organize`) to balance curation quality with token efficiency.

### Key Entities

- **AI Interaction**: A single-turn, stateless request-and-response exchange with Gemini carrying prompt instructions, structured output constraints, resolved model identifier, service tier setting, and timeout limit.
- **Track Recommendation**: A structured song suggestion produced by Gemini containing human-readable `artist` and `title` fields used for verified Tidal catalog matching.
- **Track Genre Classification**: A structured categorization record containing track identity metadata, one specific `primary_genre`, and up to three specific `sub_genres`, persisted in the local genre cache.
- **Resolved Model Configuration**: The effective primary and optional fallback Gemini model identifiers determined from environment variables, `.env` settings, deprecated-model handling rules, or the built-in `gemini-flash-latest` default.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Gemini-powered workflows (`recommend --gemini`, `radio --gemini`, and `organize` / `genre-organizer`) complete end-to-end using Google's current Gemini interaction method with zero invocations of the legacy content-generation interface.
- **SC-002**: 100% of existing documented CLI commands, flags, aliases, and `.env` configuration variables continue to function without requiring users to modify existing command invocations or scheduled job scripts.
- **SC-003**: 100% of existing valid local genre cache entries created prior to the migration are reused during `tde organize` runs without triggering redundant Gemini classification requests.
- **SC-004**: When `GEMINI_MODEL` is unset, blank, or configured to a deprecated `1.5`, `2.0`, or `2.5` Gemini model, 100% of runs automatically resolve to `gemini-flash-latest` (emitting a clear substitution warning for deprecated models) without failing due to retired model names.
- **SC-005**: 100% of AI-generated song recommendations contain non-empty artist and title values and 0% rely on AI-generated ISRC codes for catalog lookup.
- **SC-006**: When flex mode is active with fallback disabled (default), 0% of capacity-exhausted or timed-out flex requests silently execute on standard-tier billing; when fallback is explicitly enabled, 100% of capacity-exhausted requests log a warning and recover on standard tier.
- **SC-007**: User-facing documentation (`README.md` and `.env.example`) accurately documents the current Gemini interaction method, `gemini-flash-latest` default model, model configuration behavior, and troubleshooting guidance with zero stale references.

## Assumptions

- Scope covers the entire Tidal Discovery Engine project—specifically all Gemini-backed capabilities (`recommend`, `radio`, and `organize`), automated validation suites, configuration templates, and user documentation.
- Existing `GEMINI_API_KEY` credentials issued through Google AI Studio continue to authenticate against the current Gemini interaction method without requiring users to provision new keys or change authentication workflows.
- `gemini-flash-latest` remains the built-in default model so users automatically track Google's latest Flash model without updating `.env` on each release; users preferring an explicit versioned model (such as `gemini-3.8-flash` or `gemini-3.5-flash-lite`) can configure it via `GEMINI_MODEL`. During planning, vendor compatibility of the `gemini-flash-latest` alias with Google's current Gemini interaction method will be verified from authoritative documentation per Constitution Principle I and Principle X.
- All Tidal Discovery Engine AI operations are stateless single-turn tasks (generating a recommendation list from seeds or classifying a batch of tracks), so server-side multi-turn conversation history is unnecessary.
- Google's current Gemini interaction method supports structured schema enforcement, configurable request timeouts, and service-tier selection (`standard` and `flex`) needed to maintain parity with existing cost and reliability features; if any upstream capability constraint differs between tiers, planning research will verify exact parameter support from official vendor documentation per Constitution Principle I and Principle X.
