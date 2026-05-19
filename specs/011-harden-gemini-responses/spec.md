# Feature Specification: Harden Gemini Responses

**Feature Branch**: `011-harden-gemini-responses`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "We need an update to the spec; there is a bug with gemini handling or the handling is weak with gemini responses which is causing the new exclude favorites parameter to fail when the response isn't good."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover From Weak Gemini Replies (Priority: P1)

A user runs playlist generation in Gemini-backed recommendation mode, including runs where favorite tracks are excluded. When Gemini returns a weak, empty, or malformed response, the system should recover when possible and avoid misreporting the situation as a valid zero-result recommendation set.

**Why this priority**: This directly addresses the observed production bug where recommendation runs fail even though the downstream exclusion logic is working correctly.

**Independent Test**: Can be fully tested by simulating a Gemini-backed recommendation response that succeeds at the transport level but arrives empty, malformed, or not parseable into recommendations, then verifying the system retries or classifies the failure clearly instead of proceeding with an empty recommendation list.

**Acceptance Scenarios**:

1. **Given** a Gemini-backed recommendation request returns a successful provider response with no usable recommendations, **When** the system detects that the response cannot be used, **Then** it retries according to the defined recovery policy before failing the run.
2. **Given** a retry receives a usable recommendation payload, **When** playlist generation continues, **Then** the run completes normally and downstream filtering such as exclude-favorites operates on the recovered recommendations.
3. **Given** the initial response and the single recovery retry both fail to produce usable recommendations, **When** the run ends, **Then** the system reports a Gemini response-handling failure with corrective guidance instead of reporting a valid zero-suggestion outcome.

### Clarifications

### Session 2026-05-19

- Q: If Gemini returns a valid but empty recommendation list, should the CLI retry, fail, or accept it as a normal empty result? -> A: Retry exactly once after the initial response; if still empty, fail with a Gemini response-handling error.
- Q: How should model fallback behave for non-retryable Gemini status failures? -> A: Preserve existing configured fallback behavior if present; otherwise fail immediately.

---

### User Story 2 - Keep Exclude-Favorites Behavior Correct (Priority: P2)

A user enables exclude-favorites while using Gemini-backed recommendations. The favorites filter should only run against real recommendation candidates and should not be blamed for failures that originate from unusable Gemini responses.

**Why this priority**: The recent bug was surfaced through the new exclude-favorites option, so the spec must preserve correct behavior and isolate fault reporting.

**Independent Test**: Can be fully tested by running the CLI with exclude-favorites enabled while injecting unusable Gemini responses, then verifying that favorites retrieval and filtering are not reported as the root cause when recommendation generation fails first.

**Acceptance Scenarios**:

1. **Given** exclude-favorites is enabled and favorites retrieval succeeds, **When** Gemini produces no usable recommendations, **Then** the system reports the recommendation-provider failure and does not imply that favorites exclusion removed all candidates.
2. **Given** exclude-favorites is enabled and Gemini returns usable recommendations after recovery, **When** favorites filtering runs, **Then** the final playlist excludes favorites exactly as specified in the existing feature.

---

### User Story 3 - Preserve Stable Behavior Without Regressions (Priority: P3)

A user runs existing recommendation flows in Gemini-backed mode without hitting weak-response conditions. The hardened handling should not change normal successful results or degrade the user experience with unnecessary failures.

**Why this priority**: The fix must be narrow and safe because the normal path already works in successful runs.

**Independent Test**: Can be fully tested by running existing Gemini-backed flows with valid recommendation payloads and confirming that output, logging, and playlist creation remain consistent with the current successful behavior.

**Acceptance Scenarios**:

1. **Given** Gemini returns a usable recommendation payload on the first attempt, **When** the system processes the response, **Then** it does not apply additional failure handling that changes the successful outcome.
2. **Given** a non-Gemini recommendation mode is used, **When** playlist generation runs, **Then** behavior remains unchanged.

### Edge Cases

- What happens when Gemini returns a transport-success response that contains structured data the system cannot interpret? The run is treated as a recommendation-provider handling failure, not as a legitimate empty recommendation result.
- What happens when Gemini returns free-form text, partial JSON, or mixed valid and invalid recommendation items? The system uses only validated recommendation items if recovery rules allow it; otherwise it fails with a clear provider-handling error.
- What happens when a retry succeeds after an unusable first response? The run continues normally and later stages operate on the recovered recommendations.
- What happens when all retries fail and exclude-favorites is enabled? The user receives a Gemini-specific failure message, and favorites exclusion summary output does not misrepresent the cause as all candidates being filtered out.
- What happens when a valid Gemini response contains an actual empty recommendation set? For this feature, empty structured recommendation output is treated as unusable: the system performs one recovery retry and then fails closed with a Gemini response-handling error if the retry is still empty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect when a Gemini-backed recommendation response is unusable even if the provider request completed successfully.
- **FR-002**: The system MUST distinguish between a valid empty recommendation result and an unusable Gemini response that failed parsing, validation, or extraction.
- **FR-003**: When a Gemini response is unusable, the system MUST perform exactly one recovery retry before surfacing a final failure.
- **FR-004**: When a Gemini response is valid but empty, the system MUST treat it as unusable and apply FR-003.
- **FR-005**: When a later retry yields usable recommendations, the system MUST continue playlist generation without requiring user intervention.
- **FR-006**: When the initial response and the single recovery retry fail to produce usable recommendations, the system MUST stop playlist generation and present a user-facing error that identifies the Gemini response as the cause.
- **FR-007**: When failure occurs before any usable recommendations exist, the system MUST NOT report exclude-favorites filtering as the reason the playlist could not be built.
- **FR-008**: When exclude-favorites is enabled and favorites retrieval succeeds, the system MUST only emit exclusion summary counts based on actual recommendation candidates that reached the filtering stage.
- **FR-009**: The system MUST preserve existing successful behavior for Gemini-backed runs that already return usable recommendations on the first attempt.
- **FR-010**: The system MUST preserve existing behavior for non-Gemini recommendation modes.
- **FR-011**: User-facing failure messaging for unusable Gemini responses MUST include corrective guidance that distinguishes transient provider issues from favorites-retrieval problems.
- **FR-012**: For non-retryable Gemini status failures, the system MUST preserve existing model-fallback behavior only when a fallback model is already configured; if no fallback is configured, the system MUST fail immediately.

### Documentation & Understandability Requirements *(mandatory)*

- **DR-001**: User-facing documentation MUST explain how the system behaves when Gemini returns an unusable response during playlist generation.
- **DR-002**: Troubleshooting guidance MUST differentiate recommendation-provider failures from exclude-favorites filtering outcomes.
- **DR-003**: At least one concrete example MUST show the expected user-visible message for a Gemini response-handling failure.
- **DR-004**: Terminology for "usable recommendation response," "retry," and "provider failure" MUST remain consistent across the spec, quickstart, and README updates.

### Validation Requirements *(mandatory)*

- **VR-001**: An automated test MUST verify that an unusable Gemini response that succeeds at the transport level triggers the defined recovery behavior rather than returning zero recommendations immediately.
- **VR-002**: An automated test MUST verify that a later successful retry allows playlist generation to continue and still supports exclude-favorites filtering.
- **VR-003**: An automated test MUST verify that repeated unusable Gemini responses produce a Gemini-specific user-facing failure instead of a misleading exclusion shortfall or zero-suggestions path.
- **VR-004**: An automated test MUST verify that a valid first-attempt Gemini response preserves current successful behavior.
- **VR-005**: An automated test MUST verify that non-Gemini recommendation modes remain unchanged.
- **VR-006**: Documentation validation MUST confirm that troubleshooting text distinguishes Gemini provider failures from exclude-favorites failures.
- **VR-007**: An automated test MUST verify that a valid-but-empty Gemini response receives exactly one recovery retry before final failure.

### Evidence & Unknowns Requirements *(mandatory)*

- **ER-001**: The available Gemini SDK response fields for unusable-but-successful responses MUST be confirmed from the current service implementation and provider documentation before implementation details are chosen.
- **ER-002**: The system's current successful-run logs and failure logs MUST be used as evidence when defining the boundary between valid empty output and provider-handling failure.
- **ER-003**: It is assumed that the provider may return successful responses that do not populate the structured recommendation payload consistently; this assumption must be validated during implementation.

### Key Entities *(include if feature involves data)*

- **GeminiRecommendationResponse**: The provider response received for a recommendation request, including whether it contains usable recommendation content.
- **RecommendationRecoveryAttempt**: A single attempt to obtain a usable set of recommendations after an unusable Gemini response is detected.
- **RecommendationFailureOutcome**: The user-visible result produced when no usable recommendations can be obtained after bounded recovery.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of tested unusable-response scenarios, the system classifies the issue as a Gemini response-handling failure or recovery event rather than a legitimate zero-recommendation success.
- **SC-002**: In 100% of tested retry-success scenarios, playlist generation completes without requiring the user to rerun the command manually.
- **SC-003**: Existing successful Gemini-backed runs show no user-visible regression in playlist creation behavior in the defined regression test coverage.
- **SC-004**: In 100% of tested exclude-favorites failure-path scenarios triggered by unusable Gemini responses, user-facing messages correctly attribute the failure to Gemini response handling rather than favorites filtering.
- **SC-005**: Support and troubleshooting guidance contains at least one clear remediation path for users who encounter repeated unusable Gemini responses.

## Assumptions

- The observed intermittent failure is caused by weak Gemini response handling rather than by favorites retrieval, because favorites loading completed successfully in the reported failing run.
- Gemini-backed recommendation mode remains an existing supported user flow and should continue to be available after hardening.
- A single recovery retry is acceptable because repeated unusable responses are more likely to be transient provider behavior than intentional valid empty results, while avoiding excessive delay in unattended runs.
- Existing model fallback behavior (if configured) remains unchanged; this feature does not introduce a new mandatory fallback step for non-retryable statuses.
- The existing exclude-favorites specification remains the source of truth for favorites retrieval and filtering behavior; this feature only adjusts recommendation-response handling and related user messaging.
- Documentation updates are limited to existing user-facing artifacts for CLI behavior and troubleshooting.
