# Documentation Update Checklist: README Overhaul

**Purpose**: Ensure future feature work keeps README documentation coherent and understandable.
**Created**: 2026-03-30
**Feature**: [spec.md](../spec.md)

## README Section Coverage

- [ ] DOC-001 Setup section contains accurate prerequisites: all credentials, session files, and install commands are verified runnable [Spec §FR-001]
- [ ] DOC-002 Modes section covers Mode 1, Mode 2, and Mode 3 — each with distinct intent description and at least one command example [Spec §FR-002]
- [ ] DOC-003 All Parameters section is the single location documenting every option — no option is defined or constrained elsewhere in the README [Spec §FR-005]
- [ ] DOC-004 Troubleshooting section contains at least two failure entries; each entry has all three components: observed symptoms, behavioral explanation, and corrective action [Spec §FR-004, §SC-002]
- [ ] DOC-005 Scheduling section preserves unattended execution guidance and includes at least one scheduler command example [Spec §FR-001]
- [ ] DOC-006 README top-level sections appear in this exact order: Setup → Modes → All Parameters → Troubleshooting → Scheduling [Spec §FR-001]
- [ ] DOC-007 No top-level section duplicates normative guidance owned by another section (e.g. option defaults appear only in All Parameters) [Spec §FR-001]

## Behavior Consistency

- [ ] DOC-008 Canonical terms for modes (Mode 1/2/3), flags (--gemini, --shuffle, etc.), and outcomes (deep cuts, fallback) are used identically across every README section [Spec §FR-007]
- [ ] DOC-009 Mode 3 documents the required `--artist` + `--track` pair with an explicit statement that both flags must be provided together [Spec §FR-003]
- [ ] DOC-010 `--shuffle` modifier behavior is documented for each applicable mode (Mode 1 pool expansion; Mode 2/3 deep-cuts intent) [Spec §FR-002]
- [ ] DOC-011 Fallback behavior for Gemini model-unavailable errors is documented with explicit statement of whether fallback occurs and what the corrective action is [Spec §FR-004]
- [ ] DOC-012 Fallback/non-fallback boundary (unavailable/not-found vs auth/quota errors) matches current CLI behavior — verified without reading source code [Spec §FR-004]
- [ ] DOC-013 README includes a quick-start summary for the most common use case and a detailed reference section for advanced configuration — these are two distinct areas with no duplicated content [Spec §FR-006]

## Example Quality

- [ ] DOC-014 At least one syntactically correct, runnable command example exists for each of Mode 1, Mode 2, and Mode 3 [Spec §FR-002]
- [ ] DOC-015 Each command example is followed by a plain-language statement of its expected outcome [Spec §DR-002]
- [ ] DOC-016 Zero contradictory command guidance exists across README sections (e.g., no conflicting option names, defaults, or mode descriptions) [Spec §SC-003]

## Review Gate

- [ ] DOC-017 Reviewed and approved by maintainer reviewer #1 — confirms command-path clarity for all modes
- [ ] DOC-018 Reviewed and approved by maintainer reviewer #2 — confirms absence of contradictory guidance and troubleshooting completeness
