# Feature Specification: Gemini Support for Single-Seed Mode

**Feature Branch**: `007-gemini-mode3-support`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description: "there is a mode 3 in this project (check readme) and I want to extend the gemini functionality to that option. please assist."

## Clarifications

### Session 2026-03-10

- Q: For Gemini Mode 3, how should recommendation count behave when the model cannot produce enough valid unique tracks? -> A: Best-effort count: return as many valid recommendations as found, even if fewer than requested.
- Q: How should Gemini Mode 3 handle ambiguous or unavailable catalog matching for the provided artist/track seed? -> A: Flexible seed handling: use artist+track text as seed context even if catalog matching is ambiguous or unavailable.
- Q: How should Gemini Mode 3 handle recommendations that cannot be resolved on Tidal during playlist creation? -> A: Warn and continue: skip unresolvable tracks, continue playlist creation, and report skipped count/details in output.
- Q: What skipped-track detail should CLI output include? -> A: Count + first 5 names.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate single-seed playlist with Gemini (Priority: P1)

As a user exploring music from one known track, I can use Gemini with artist and track inputs so I can get AI-generated recommendations centered on that seed.

**Why this priority**: This is the core feature request and the primary value delivery.

**Independent Test**: Run a Mode 3 command with `--artist`, `--track`, and `--gemini`, then verify that a playlist is created and recommendations come from Gemini behavior rather than Last.fm similarity flow.

**Acceptance Scenarios**:

1. **Given** a user provides a valid artist and track with `--gemini`, **When** the command runs, **Then** the system creates a playlist using Gemini-generated recommendations derived from that single seed track.
2. **Given** a user provides `--artist` and `--track` without `--gemini`, **When** the command runs, **Then** existing non-Gemini Mode 3 behavior remains unchanged.

---

### User Story 2 - Use deep-cuts Gemini behavior in single-seed mode (Priority: P2)

As a user who wants less mainstream recommendations from one seed song, I can combine `--gemini` and `--shuffle` in Mode 3 to receive deep-cut style suggestions.

**Why this priority**: Keeps behavior consistent with current Gemini mode semantics and expands discovery value.

**Independent Test**: Run Mode 3 with `--artist`, `--track`, `--gemini`, and `--shuffle`, then verify the recommendation set follows deep-cut/underground guidance.

**Acceptance Scenarios**:

1. **Given** a Mode 3 request includes `--gemini --shuffle`, **When** recommendations are generated, **Then** the system applies deep-cut Gemini behavior for the single-seed prompt.

---

### User Story 3 - Understand constraints and failures for Gemini single-seed runs (Priority: P3)

As a user running Gemini in single-seed mode, I get clear validation and failure feedback so I can quickly correct command inputs or configuration issues.

**Why this priority**: Prevents confusion and reduces failed run troubleshooting time.

**Independent Test**: Execute invalid and degraded scenarios (missing paired seed inputs, Gemini model/provider errors) and verify clear actionable output and consistent failure handling.

**Acceptance Scenarios**:

1. **Given** a user supplies `--gemini` with only `--artist` or only `--track`, **When** the command is parsed, **Then** the system rejects the run with a clear message that both fields are required together.
2. **Given** a Gemini request in Mode 3 fails due to model/provider issues, **When** the command exits, **Then** the user receives actionable Gemini error output consistent with existing Gemini modes.
3. **Given** all recommended tracks are unresolvable on Tidal, **When** insertion completes, **Then** the run exits with failure status and actionable output rather than reporting success.
4. **Given** a user provides `--shuffle` without `--gemini` in Mode 3, **When** the command runs, **Then** the system uses non-Gemini Mode 3 behavior and does not apply Gemini deep-cuts intent.

### Edge Cases

- User supplies `--gemini` with Mode 3 seed inputs that include extra whitespace or unusual punctuation.
- User passes `--gemini --shuffle` with very small `--num-similar-tracks` values and still expects valid output.
- Seed track is valid input format but produces weak/limited AI recommendations.
- Gemini is requested in Mode 3 while model configuration is missing, blank, or fallback is required.
- The selected seed track has ambiguous naming that could map to multiple songs.
- One or more Gemini-recommended tracks cannot be resolved to Tidal catalog entries during playlist insertion.
- All Gemini-recommended tracks are unresolvable on Tidal, resulting in zero inserted tracks.
- `--num-similar-tracks` is provided as zero or a negative value.
- One or more skipped track names are unusually long or include special characters that could produce noisy warning output.
- Gemini provider or Tidal provider is temporarily unavailable during Mode 3 execution.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow `--gemini` to be used with Mode 3 single-seed input (`--artist` + `--track`).
- **FR-002**: System MUST preserve existing Mode 3 behavior when `--gemini` is not provided.
- **FR-003**: System MUST generate recommendations for Gemini Mode 3 runs using the single seed track context supplied by the user.
- **FR-004**: System MUST support `--shuffle` when used with Gemini in Mode 3 and apply deep-cut recommendation intent consistent with current Gemini shuffle behavior.
- **FR-005**: System MUST enforce that `--artist` and `--track` remain a required pair for Mode 3, including Gemini Mode 3 invocations.
- **FR-006**: System MUST create playlists for successful Gemini Mode 3 runs using the requested playlist naming and optional folder placement behavior.
- **FR-007**: System MUST reuse existing Gemini configuration and fallback rules for Mode 3, including handling of missing primary model configuration and fallback-eligible failures.
- **FR-008**: System MUST surface actionable error output for Gemini Mode 3 failures that includes failing model identifier, failure category, and one corrective next step, consistent with existing Gemini modes.
- **FR-009**: System MUST document Gemini usage examples for Mode 3, including both standard and `--shuffle` variants.
- **FR-010**: System MUST treat `--num-similar-tracks` as an upper target for Gemini Mode 3 and return best-effort valid recommendations when fewer than requested can be produced.
- **FR-011**: System MUST allow Gemini Mode 3 generation to proceed using user-provided artist and track text context when strict catalog matching is ambiguous or unavailable.
- **FR-012**: System MUST skip Gemini-recommended tracks that cannot be resolved on Tidal, continue playlist creation with remaining resolvable tracks, and emit a warning that includes skipped count and skipped track details.
- **FR-013**: System MUST limit skipped-track warning details to the skipped count and up to the first 5 skipped track names.
- **FR-014**: System MUST classify run outcome as success only when at least one recommended track is successfully inserted into the destination Tidal playlist.
- **FR-015**: System MUST classify run outcome as failure when zero recommended tracks are inserted after resolution attempts, and MUST emit actionable output explaining the cause and next step.
- **FR-016**: System MUST validate `--num-similar-tracks` as a positive integer and reject non-positive values with a corrective validation message before recommendation generation.
- **FR-017**: System MUST preserve fallback boundaries from existing Gemini behavior in Mode 3: fallback is allowed only for primary-model unavailable or not-found failures, and is prohibited for auth, quota, and permission failures.
- **FR-018**: System MUST treat `--shuffle` without `--gemini` in Mode 3 as non-Gemini behavior and MUST NOT apply Gemini deep-cuts intent in that invocation.
- **FR-019**: System MUST truncate skipped-track warning name previews to a display-safe maximum length and preserve a valid warning format even when track names are unusually long or contain special characters.
- **FR-020**: System MUST emit unattended-run observability output with stable warning/error prefixes and consistent log level usage for validation failures, partial-success warnings, and terminal failures.
- **FR-021**: System MUST emit user-facing warning/error summary lines in a parse-stable format suitable for automation scripts, including stable field order for count/category/model metadata when present.
- **FR-022**: System MUST define dependency-degradation behavior for Gemini and Tidal unavailability, including terminal status, user-facing actionable output, and whether playlist insertion is attempted or skipped.

### Key Entities *(include if feature involves data)*

- **Single-Seed Request**: A user-provided request containing artist name, track name, desired recommendation count, and playlist metadata.
- **Gemini Recommendation Intent**: The recommendation style instruction set used for Gemini generation (standard relevance vs deep cuts when shuffle is enabled).
- **Playlist Creation Outcome**: The resulting artifact status for a run, including success metadata or actionable failure details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of valid Mode 3 runs with `--gemini` complete with a created playlist containing at least one inserted track.
- **SC-002**: In acceptance testing, 100% of Mode 3 runs without `--gemini` continue to behave consistently with pre-feature baseline behavior.
- **SC-003**: In acceptance testing, 100% of Mode 3 runs using `--gemini --shuffle` produce recommendations that satisfy deep-cut intent guidelines defined for Gemini shuffle behavior.
- **SC-004**: In invalid input tests where `--artist`/`--track` pairing is broken, users receive a corrective validation message before recommendation generation in 100% of cases.
- **SC-005**: Documentation users can execute a Mode 3 Gemini example command from README successfully without additional undocumented flags.
- **SC-006**: In constrained recommendation scenarios, 100% of successful Gemini Mode 3 runs insert at least one track and never exceed the requested `--num-similar-tracks` count.
- **SC-007**: In seed-ambiguity test scenarios, 100% of Gemini Mode 3 runs continue with text-based seed context and provide either recommendations or actionable Gemini failure output.
- **SC-008**: In tests containing some unresolvable recommendations, 100% of runs with at least one resolvable recommendation complete playlist creation and report skipped count plus skipped track details.
- **SC-009**: In skipped-track reporting tests, 100% of warnings include skipped count and no more than 5 skipped track names.
- **SC-010**: In all-unresolvable tests, 100% of runs end in failure status with actionable output and no false success signal.
- **SC-011**: In boundary tests for `--num-similar-tracks`, 100% of non-positive values fail fast with corrective validation, and 100% of accepted values produce no more than the requested count.
- **SC-012**: In baseline comparison runs for the same seed inputs, median Mode 3 Gemini end-to-end runtime does not regress by more than 20% versus pre-feature Mode 3 Gemini behavior.
- **SC-013**: In mixed-flag tests (`--shuffle` without `--gemini`), 100% of runs execute non-Gemini Mode 3 behavior with no Gemini deep-cuts intent applied.
- **SC-014**: In skipped-warning formatting tests with long/special-character names, 100% of warnings remain parseable and include count plus bounded preview names.
- **SC-015**: In dependency outage tests (Gemini unavailable or Tidal unavailable), 100% of runs emit defined actionable output and terminal status according to dependency-degradation requirements.

## Assumptions

- Existing Gemini recommendation quality and fallback expectations from current Gemini mode remain the baseline for Mode 3 extension.
- Users running Mode 3 Gemini flows already have valid Tidal authentication and Gemini credentials configured.
- Single-seed Gemini recommendations are expected to use the provided artist and track as the primary context even when exact catalog mapping is ambiguous.

## Dependencies

- Availability of Gemini service access and model configuration used by existing Gemini modes.
- Existing Mode 3 command parsing and playlist creation workflows.
- Documentation updates in user-facing usage guidance.
