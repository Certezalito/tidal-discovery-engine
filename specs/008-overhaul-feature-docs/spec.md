# Feature Specification: Documentation Overhaul

**Feature Branch**: `008-overhaul-feature-docs`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "lets buildla new spec, documentation needs to be overhauled after multiple features have been added and the readme is clunky."

## Clarifications

### Session 2026-03-30

- Q: What validation method should be used for success criteria originally based on user percentages? → A: Option D - Skip user testing and use documentation peer review only.
- Q: Which documentation artifacts are in scope for this overhaul? → A: Option A - Overhaul README only; leave quickstart unchanged.
- Q: What structure should troubleshooting/failure guidance entries follow? → A: Structured prose per entry: symptoms, explanation, corrective action.
- Q: Where should the maintainer-facing documentation update checklist live? → A: Option B - Separate file in `specs/008-overhaul-feature-docs/checklists/`.
- Q: What top-level section order should the overhauled README follow? → A: Option B - Setup → Modes → All Parameters → Troubleshooting → Scheduling.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Find The Right Command Fast (Priority: P1)

As a user running the CLI, I want a clear README structure with mode-by-mode usage,
so I can choose the correct command and options quickly without trial and error.

**Why this priority**: The README is the first touchpoint for users; poor structure
directly blocks feature adoption and increases misconfiguration.

**Independent Test**: Give the updated README to a user unfamiliar with recent
features and ask them to run one command for each mode without external help.

**Acceptance Scenarios**:

1. **Given** a user who wants recommendations from favorites, **When** they read the
  mode overview, **Then** they can identify Mode 1 and execute a valid command.
2. **Given** a user who wants single-seed generation, **When** they read Mode 3
  guidance, **Then** they can identify required option combinations and avoid
  invalid input.

---

### User Story 2 - Understand Failure And Recovery (Priority: P2)

As a user running unattended jobs, I want clear documentation for common failures,
fallback behavior, and recovery steps, so I can resolve issues quickly.

**Why this priority**: Reliability depends on users understanding failures,
especially for scheduled execution where immediate debugging is harder.

**Independent Test**: Ask a user to locate remediation steps for a model-unavailable
error and a missing-required-options error using docs only.

**Acceptance Scenarios**:

1. **Given** a user sees a Gemini model availability error, **When** they consult
  docs, **Then** they find explicit fallback behavior and corrective action.
2. **Given** a user provides incomplete Mode 3 inputs, **When** they consult docs,
  **Then** they find required option pairs and a corrected command example.

---

### User Story 3 - Keep Documentation Consistent Over Time (Priority: P3)

As a maintainer, I want a consistent documentation structure and update checklist,
so future feature additions keep docs coherent rather than becoming clunky again.

**Why this priority**: Long-term quality prevents repeated documentation drift as
new modes and flags are introduced.

**Independent Test**: For a hypothetical new feature, a maintainer can follow the
defined update checklist, produce aligned README updates, and verify the updated
README does not contradict existing quickstart guidance.

**Acceptance Scenarios**:

1. **Given** a new feature with changed CLI behavior, **When** docs are updated,
   **Then** all required documentation sections are updated using consistent terms.

---

### Edge Cases

- User follows an outdated command from a previous section that conflicts with
  current option rules.
- User cannot distinguish default behavior from optional modifiers due to mixed
  terminology.
- User encounters failure categories with different fallback behavior and needs a
  clear decision path.
- User needs a quick-start path and a detailed reference path without duplicated,
  contradictory guidance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The README MUST follow this top-level section order: Setup → Modes →
  All Parameters → Troubleshooting → Scheduling. Each section MUST have a distinct
  purpose with no duplicated guidance across sections.
- **FR-002**: Documentation MUST include updated usage examples for each supported
  mode and these major modifier combinations: Mode 1 with and without
  `--shuffle`, Mode 2 with `--gemini` and with/without `--shuffle` where
  applicable, and Mode 3 with the required `--artist` plus `--track` pair.
- **FR-003**: Documentation MUST explicitly state required option dependencies and
  invalid option combinations where relevant.
- **FR-004**: Documentation MUST describe user-visible failure categories using
  structured prose entries, each containing: observed symptoms, an explanation of
  the behavior, and at least one corrective action the user can take.
- **FR-005**: A single authoritative parameter reference MUST define option purpose,
  defaults, and applicability by mode.
- **FR-006**: The README MUST include both a quick-start summary section for common
  usage and a detailed reference section for advanced configuration. Quickstart
  documents are explicitly out of scope for this overhaul.
- **FR-007**: Updated content MUST use consistent terminology for modes,
  recommendation behavior, and fallback behavior.

### Documentation & Understandability Requirements *(mandatory)*

- **DR-001**: This feature MUST update the README only. Quickstart documents are
  explicitly out of scope and MUST NOT be modified as part of this feature.
- **DR-002**: Every changed behavior description MUST include plain-language intent,
  expected outcome, and one concrete command example.
- **DR-003**: User-facing failure and fallback documentation MUST include corrective
  guidance users can apply without reading source code.
- **DR-004**: Terminology for modes, flags, and outcomes MUST be consistent across
  all updated artifacts.
- **DR-005**: Documentation MUST include a maintainer-facing update checklist
  delivered as a separate file at
  `specs/008-overhaul-feature-docs/checklists/docs-update.md`, defining which
  README sections must be reviewed when adding future features.

### Key Entities *(include if feature involves data)*

- **Documentation Section**: A user-facing content unit (for example, Setup, Mode
  Guide, Parameter Reference, Troubleshooting) with clear purpose and ownership.
- **Usage Example**: A runnable command example tied to one mode/use case, with
  expected behavior notes.
- **Failure Guidance Entry**: A documented failure category written as structured
  prose with three mandatory components: observed symptoms, behavioral explanation,
  and at least one corrective action.
- **Documentation Update Checklist**: A maintainer-facing checklist file at
  `specs/008-overhaul-feature-docs/checklists/docs-update.md` that ensures all
  required README sections are evaluated during feature work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Documentation peer review by at least 2 maintainers confirms each
  primary use case maps to one correct command path without contradictory steps.
- **SC-002**: Documentation peer review confirms troubleshooting guidance covers at
  least two failure/fallback scenarios with actionable corrective steps.
- **SC-003**: Documentation audit reports zero contradictory statements between
  quickstart and README for modes, options, and fallback behavior.
- **SC-004**: For one subsequent feature addition, maintainers complete the
  documentation update checklist with all required sections updated before release.

## Assumptions

- Primary consumers are CLI users with varying familiarity levels, including users
  who have not tracked recent feature additions.
- This feature focuses on documentation structure and clarity, not on adding new
  runtime capabilities.
- Existing behavior is treated as source-of-truth and documentation must align to
  currently supported user-visible outcomes.
- The README is the sole canonical user-facing artifact being updated; quickstart
  documents are explicitly out of scope for this overhaul.
