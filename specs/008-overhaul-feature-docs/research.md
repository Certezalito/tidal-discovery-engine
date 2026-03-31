# Research: Documentation Overhaul

**Feature**: 008-overhaul-feature-docs  
**Date**: 2026-03-30  
**Status**: Complete

## Decision 1: Restrict scope to README-only updates

- Decision: Update `README.md` only for user-facing documentation changes, while leaving quickstart files untouched.
- Rationale: The feature request and clarifications explicitly constrain scope to README overhaul, reducing risk and delivery time.
- Alternatives considered:
  - Update README + quickstart: rejected due to scope decision (clarification Q2 Option A).
  - Full docs overhaul across specs: rejected as out-of-scope for current feature.

## Decision 2: Define a fixed information architecture for README

- Decision: Enforce top-level order: Setup -> Modes -> All Parameters -> Troubleshooting -> Scheduling.
- Rationale: Stable ordering improves scanability and reduces cognitive switching for first-time users.
- Alternatives considered:
  - Parameter-first ordering: rejected; users need intent/mode guidance before exhaustive option references.
  - Modes-first before setup: rejected; prerequisite setup should remain first for successful execution.

## Decision 3: Use structured prose for troubleshooting entries

- Decision: Every troubleshooting entry must include symptoms, explanation, and corrective action.
- Rationale: This format supports rapid diagnosis and actionable recovery without source-code reading.
- Alternatives considered:
  - One-line bullet fixes: rejected as too terse for nuanced fallback behavior.
  - Large decision trees: rejected as over-complex for README context.

## Decision 4: Validation method uses peer review rather than user-study sampling

- Decision: Validate understandability via documentation peer review by at least two maintainers.
- Rationale: Clarified acceptance criteria selected maintainers-only evaluation (clarification Q1 Option D).
- Alternatives considered:
  - 5- or 10-user usability sample: rejected by clarification decision.

## Decision 5: Maintainability via checklist artifact in feature checklists directory

- Decision: Create `specs/008-overhaul-feature-docs/checklists/docs-update.md` as the canonical maintainer update checklist.
- Rationale: Keeps governance and feature artifacts co-located and versioned for future features.
- Alternatives considered:
  - Embed checklist directly in README: rejected to avoid user-facing clutter.
  - Repo-root checklist file: rejected as less feature-scoped and less discoverable in spec workflow.
