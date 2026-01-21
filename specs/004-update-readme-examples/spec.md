# Feature Specification: Update README Examples

**Feature Branch**: `004-update-readme-examples`
**Created**: 2026-01-21
**Status**: Draft
**Input**: User description: "update the readme, examples provided need to cover the use of all parameters"

## Clarifications

### Session 2026-01-21

- Q: How should the new folder example be presented? → A: Create a new "Organization" section with a dedicated example titled "### Organizing Playlists".

## User Scenarios & Testing

### User Story 1 - Comprehensive Documentation (Priority: P1)

As a new or existing user, I want to see usage examples in the README that demonstrate all available parameters, including the new folder organization feature, so that I can easily utilize the tool's full potential without reading the source code.

**Why this priority**: Documentation is the primary interface for the user. Incomplete documentation leads to underutilized features (like the new folder support).

**Independent Test**: Review the README.md file and verify that every parameter listed in the options table is also used in at least one example command.

**Acceptance Scenarios**:

1.  **Given** the README file, **When** I read the new "Organizing Playlists" section, **Then** I see an example command that uses the `--folder` argument.
2.  **Given** the "All Parameters" table, **When** I check the examples, **Then** all parameters listed in the table (including `--shuffle`, `--artist`, `--track`, `--num-tidal-tracks`, `--num-similar-tracks`, `--playlist-name`, `--folder`) are demonstrated in the example commands.

## Requirements

### Functional Requirements

1.  **FR-001**: The `README.md` file MUST be updated to include a new section "Organizing Playlists" with an example command that demonstrates the use of the `--folder` parameter.
2.  **FR-002**: The `README.md` MUST include or update an example to clearly show how to combine `--shuffle` with other parameters if not already clear.
3.  **FR-003**: The examples MUST use valid syntax that can be copy-pasted (with placeholder replacement) by the user.

## Success Criteria

-   **Quantitative**: 100% of CLI parameters listed in the "All Parameters" table are present in at least one example code block in the README.
-   **Qualitative**: Users can copy an example command that uses the `--folder` feature and run it successfully (assuming they have the feature code).

## Assumptions & Dependencies

-   **Assumption**: The `--folder` feature is already implemented (it is, in branch `003`, and presumably this documentation update follows that work or is part of the same release train).
-   **Dependency**: None.

## Constraints

-   Keep the README concise; do not add unnecessary prose, just effective examples.
