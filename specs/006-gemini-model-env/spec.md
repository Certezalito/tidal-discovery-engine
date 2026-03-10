# Feature Specification: Gemini Model Env Configuration

**Feature Branch**: `006-gemini-model-env`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description: "I want the gemini model to be specified in the .env file instead of being inherent in the code."

## Clarifications

### Session 2026-03-09

- Q: Which configuration precedence should apply when shell environment and .env values differ? -> A: Exported environment variable takes precedence, then .env value, then built-in default.
- Q: When should fallback model selection be attempted? -> A: Attempt fallback only when provider indicates the configured primary model is unavailable or not found.
- Q: What should happen when GEMINI_MODEL is missing? -> A: Log a warning once at startup, then use the default model.
- Q: How should empty or whitespace GEMINI_MODEL values be handled? -> A: Treat as missing, log startup warning once, then use default model.
- Q: What are the canonical environment variable names for model selection? -> A: GEMINI_MODEL and GEMINI_FALLBACK_MODEL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure model without code edits (Priority: P1)

As an operator running the playlist suggestion workflow, I can set the Gemini model name in environment configuration so I can change models without editing source code.

**Why this priority**: This is the primary user value and directly removes hardcoded model dependency.

**Independent Test**: Set a model value in environment configuration, run a Gemini-backed command, and verify the configured value is used without changing code files.

**Acceptance Scenarios**:

1. **Given** a valid Gemini model is set in environment configuration, **When** a Gemini-backed workflow runs, **Then** the workflow uses that configured model.
2. **Given** the configured model is changed between two runs, **When** the workflow is run again, **Then** the new model setting is applied on the next run.

---

### User Story 2 - Safe fallback when config is missing (Priority: P2)

As an operator, I can still run the workflow if no model is explicitly configured, so the feature remains backward compatible for existing setups.

**Why this priority**: Prevents regressions for users who have not yet updated their environment file.

**Independent Test**: Remove model setting from environment configuration and verify the workflow still runs using the documented default behavior.

**Acceptance Scenarios**:

1. **Given** no model value is configured in environment settings, **When** a Gemini-backed workflow runs, **Then** it uses the default model behavior and does not fail due to missing configuration.

---

### User Story 3 - Understand configuration errors quickly (Priority: P3)

As an operator, I receive clear feedback when a configured model is invalid so I can fix configuration quickly.

**Why this priority**: Improves recovery time and reduces troubleshooting effort.

**Independent Test**: Configure an invalid model value and verify the run output communicates the failure and corrective action.

**Acceptance Scenarios**:

1. **Given** an invalid model value is configured, **When** a Gemini-backed workflow runs, **Then** the user sees an actionable error indicating the configured model is not available.

### Edge Cases

- Environment file contains the model setting key with an empty value.
- Environment file contains leading or trailing whitespace in the model value.
- Environment variable is set in the shell and differs from the environment file value.
- Configured primary model is unavailable and fallback model behavior is enabled.
- A typo in the model name causes provider rejection.
- Authentication, quota, or permission errors must not trigger fallback.
- Empty or whitespace-only model values are treated as missing configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow operators to define the primary Gemini model through environment configuration.
- **FR-002**: System MUST resolve the effective primary model with precedence order: exported environment variable value first, then .env value, then built-in default.
- **FR-003**: System MUST maintain backward-compatible behavior when no explicit model is configured.
- **FR-003a**: System MUST emit at most one warning per CLI invocation when no explicit primary model is configured and default behavior is used.
- **FR-003b**: System MUST normalize model values by trimming whitespace and treating empty results as missing configuration.
- **FR-004**: System MUST support optional fallback model configuration through environment settings and attempt fallback only when provider response indicates the configured primary model is unavailable or not found.
- **FR-005**: System MUST validate configured model values at runtime by handling provider rejection and returning an actionable error message that includes failing model identifier, failure category (for example unavailable/not-found, auth, quota, permission), and corrective guidance (for example verify model ID or account access).
- **FR-006**: System MUST document canonical variable names as GEMINI_MODEL (primary) and GEMINI_FALLBACK_MODEL (optional fallback) in operator-facing documentation.
- **FR-007**: System MUST preserve existing Gemini workflow outputs when model configuration is unchanged from current defaults.

### Key Entities *(include if feature involves data)*

- **Gemini Model Configuration**: Operator-provided settings that define primary and optional fallback model names used for Gemini-backed requests.
- **Model Resolution Result**: The effective model selection outcome for a request, including resolved source (exported environment variable, .env, or default) and whether primary or fallback configuration was used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Gemini-backed runs in test scenarios use the model value provided through environment configuration when present.
- **SC-002**: 100% of existing runs without explicit model configuration continue to execute successfully using default behavior.
- **SC-003**: In invalid-model test scenarios, operators receive a clear corrective error message in the same run where failure occurs.
- **SC-004**: Operators can switch the configured model for a subsequent run in under 2 minutes without modifying source code.
- **SC-005**: With GEMINI_MODEL and GEMINI_FALLBACK_MODEL unset, recommendation output behavior and error-path behavior remain consistent with baseline behavior from before this feature.
- **SC-006**: In 100% of invalid-model and non-fallback error scenarios, output contains failing model ID, failure category, and a corrective next step.

## Assumptions

- Operators manage environment configuration before running CLI workflows.
- Existing default model behavior remains the baseline when no model environment values are provided.
- The external Gemini provider remains the source of truth for model availability and validity.

## Dependencies

- Access to valid Gemini service credentials and account permissions.
- Operator ability to set and load environment variables used by the CLI runtime.
