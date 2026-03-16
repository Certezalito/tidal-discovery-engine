# Research: Gemini Support for Single-Seed Mode

**Feature**: 007-gemini-mode3-support  
**Date**: 2026-03-10  
**Status**: Complete

## Decision 1: Mode 3 Gemini routing behavior

- Decision: Route Mode 3 requests (`--artist` + `--track`) through Gemini recommendation generation when `--gemini` is provided; retain existing non-Gemini behavior when `--gemini` is absent.
- Rationale: Delivers requested capability without breaking current Mode 3 workflows.
- Alternatives considered:
  - Replace non-Gemini Mode 3 entirely: rejected due to regression risk and unnecessary behavior change.
  - Add a new dedicated mode flag: rejected because it complicates CLI UX for an existing mode.

## Decision 2: Seed ambiguity handling

- Decision: Use flexible seed handling for Gemini Mode 3 by using artist+track text context even when strict catalog matching is ambiguous or unavailable.
- Rationale: Prevents avoidable hard failures while preserving user intent.
- Alternatives considered:
  - Strict catalog-match required: rejected because benign ambiguity would fail useful runs.
  - Strict-first then fallback mode: rejected to avoid extra complexity at this scope.

## Decision 3: Recommendation count semantics

- Decision: Treat `--num-similar-tracks` as an upper target in Gemini Mode 3 and return best-effort valid recommendations when fewer than requested are available.
- Rationale: LLM and downstream catalog resolution can naturally produce fewer valid unique tracks.
- Alternatives considered:
  - Hard-fail if target count not met: rejected as brittle and less user-friendly.
  - Backfill with non-Gemini recommendations: rejected due to mixed-behavior opacity.

## Decision 4: Unresolvable insertion handling

- Decision: Skip recommendations that cannot be resolved on Tidal, continue playlist creation, and emit a warning.
- Rationale: Maintains successful playlist generation in partially degraded scenarios.
- Alternatives considered:
  - Fail full run on first unresolved track: rejected because it sacrifices usable output.
  - Silent skipping: rejected because it hides quality/diagnostic signals.

## Decision 5: Skipped-track reporting format

- Decision: Report skipped track count plus up to the first 5 skipped track names.
- Rationale: Balances concise CLI output with actionable diagnostics.
- Alternatives considered:
  - Full list always: rejected due to noisy output for large skip sets.
  - Count only: rejected because it lacks enough troubleshooting context.

## Decision 6: Shuffle semantics in Gemini Mode 3

- Decision: Preserve existing Gemini shuffle meaning (deep cuts / underground intent) for Mode 3 when `--shuffle` is combined with `--gemini`.
- Rationale: Keeps behavior consistent across Gemini-enabled modes and reduces user surprise.
- Alternatives considered:
  - Give `--shuffle` a mode-specific meaning in Mode 3: rejected due to inconsistency.
  - Ignore `--shuffle` in Mode 3 Gemini: rejected because it discards expected user control.

## Baseline Audit Notes (Setup Phase)

- Quickstart baseline (`specs/007-gemini-mode3-support/quickstart.md`) initially defined Mode 3 Gemini execution and verification scenarios, but lacked explicit parse-stable warning/error token expectations and fallback-boundary checks.
- README baseline (`README.md`) initially documented Mode 3 non-Gemini examples and Gemini Mode 2 usage, but lacked explicit Mode 3 Gemini examples and single-seed fallback/zero-insert outcome guidance.

## Requirement-to-Task Traceability (FR-001 to FR-017)

- FR-001 -> T004, T008
- FR-002 -> T011
- FR-003 -> T009
- FR-004 -> T015, T016, T018
- FR-005 -> T019
- FR-006 -> T008, T010
- FR-007 -> T023, T024, T025
- FR-008 -> T023, T025
- FR-009 -> T013, T014
- FR-010 -> T020
- FR-011 -> T005, T009, T010
- FR-012 -> T021, T022
- FR-013 -> T006, T022
- FR-014 -> T026
- FR-015 -> T026
- FR-016 -> T027
- FR-017 -> T024, T025
