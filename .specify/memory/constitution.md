<!--
Sync Impact Report:
- **Version Change**: 1.3.0 → 1.4.0
- **Modified Principles**:
  - I. User-Centricity & Understandability: Added explicit no-guessing rule for unknown facts and source-driven clarification requirements.
  - Technical Standards & Workflow / Quality Gates: Added evidence requirements for unresolved facts and external information.
- **Added Sections**: None
- **Removed Sections**: None
- **Templates requiring updates**:
  - .specify/templates/plan-template.md (✅ updated)
  - .specify/templates/spec-template.md (✅ updated)
  - .specify/templates/tasks-template.md (✅ updated)
  - .specify/templates/commands/*.md (✅ no directory present; no command templates to update)
- **Follow-up TODOs**: None
-->
# Tidal Discovery Engine Constitution

## Core Principles

### I. User-Centricity & Understandability
The project MUST prioritize a simple and intuitive command-line interface (CLI) and
supporting documentation that is easy to understand for end-users. Configuration
MUST remain minimal, usage MUST be straightforward, and every feature change MUST
include clear usage examples and behavior notes in end-user documentation. Unknown
facts MUST NOT be guessed. They MUST be marked explicitly and resolved from the
best available authoritative source, preferring repository documentation first and
then official vendor or API documentation when the repo does not contain the answer.

Rationale: Users can only benefit from automation when behavior is discoverable and
explainable without source-code inspection.

### II. Automation
The core value lies in automating the process of finding new music and creating
playlists, saving the user time and effort. Workflows MUST be designed to run
without manual intervention once configured (for example, scheduler/cron usage).

### III. Personalization
By starting with the user's favorite tracks, generated playlists MUST be tailored to
specific musical tastes. Algorithms and integrations MUST respect and leverage user
data to maximize relevance.

### IV. Extensibility
The project MUST use a modular design so other music services or recommendation
engines can be accommodated in the future. Code MUST remain loosely coupled and
interfaces MUST be clearly defined.

### V. Reliability & Verifiability
The application MUST include robust error handling and logging to ensure consistent,
predictable behavior, especially when running as a scheduled task. Failures MUST be
handled gracefully and logged for diagnosis. Every behavior-changing code path MUST
have targeted automated validation that can fail if the behavior regresses.

## Mission
To create a personalized music discovery tool that seamlessly integrates with a
user's Tidal library, leverages Last.fm's recommendation engine, and automates
the creation of new playlists to enrich the user's listening experience.

## Technical Standards & Workflow

**Technology Stack:**
- **Language**: Python 3.12+
- **Dependency Management**: `uv`
- **CLI Framework**: `click`
- **Configuration**: `.env` for secrets/config
- **Logging**: Python `logging` module (stdout + file)

**Quality Gates:**
- All features MUST include error handling suitable for unattended execution.
- Code MUST adhere to modular design principles to support the Extensibility
  principle.
- All dependencies MUST be managed via `uv`.
- **Validation**: Behavior changes MUST include targeted automated checks covering
  the affected CLI flow, service behavior, or error handling. Pure documentation-only
  changes may satisfy this gate with linting or direct content validation.
- **Documentation**: Every feature MUST include end-user documentation updates in
  README and/or feature quickstart content when behaviors, flags, constraints,
  or failure modes are added or changed.
- **Understandability**: Documentation MUST explain what changed, how to use it,
  expected outcomes, and failure handling in clear language with at least one
  concrete command example.
- **Evidence**: When requirements, defaults, API capabilities, or operational
  facts are unknown, contributors MUST record the uncertainty and resolve it from
  the best available authoritative source before merge rather than inventing an
  answer.

## Governance
This Constitution supersedes all other practices.

Amendment Procedure:
- Proposed constitutional changes MUST include rationale, impacted templates, and
  migration notes where applicable.
- Amendments MUST be approved through project review before merge.
- Ratification date is immutable after first adoption; last amended date MUST be
  updated on every approved change.

Versioning Policy:
- MAJOR: Backward-incompatible governance changes or principle removals/redefinitions.
- MINOR: New principles/sections or materially expanded mandatory guidance.
- PATCH: Clarifications, wording improvements, and typo fixes with no governance
  behavior change.

Compliance Review Expectations:
- All PRs and reviews MUST verify compliance with Core Principles and Quality
  Gates.
- Reviewers MUST reject feature changes that lack documentation updates, skip
  required targeted validation, fail understandability checks, or invent unknown
  facts without authoritative verification.

**Version**: 1.4.0 | **Ratified**: 2026-01-15 | **Last Amended**: 2026-05-06
