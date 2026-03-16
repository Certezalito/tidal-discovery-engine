# Implementation Plan: Gemini Support for Single-Seed Mode

**Branch**: `007-gemini-mode3-support` | **Date**: 2026-03-10 | **Spec**: `/specs/007-gemini-mode3-support/spec.md`
**Input**: Feature specification from `/specs/007-gemini-mode3-support/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend Gemini recommendation functionality to Mode 3 (single-seed artist/track flow) while preserving existing non-Gemini behavior. The implementation will route Mode 3 requests through Gemini when `--gemini` is present, preserve deep-cuts intent for `--shuffle`, apply best-effort recommendation counts, continue playlist creation when some recommended tracks are unresolvable on Tidal, and emit concise skipped-track warnings (count + first 5 names).

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: click, tidalapi, pylast, python-dotenv, google-genai  
**Storage**: N/A (runtime CLI orchestration with external APIs)  
**Testing**: pytest test suite (`tests/`), targeted CLI behavior checks  
**Target Platform**: Linux CLI runtime (portable to other OS where Python CLI executes)
**Project Type**: single-project CLI application  
**Performance Goals**: median Mode 3 Gemini end-to-end runtime regression should stay within 20% of pre-feature baseline for equivalent seed inputs (see SC-012)  
**Constraints**: maintain backward-compatible CLI flag semantics; preserve unattended execution reliability and actionable logs  
**Scale/Scope**: narrow feature scope, primarily `src/cli/main.py`, Gemini/Tidal integration services, tests, and docs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate Check

| Principle / Gate | Status | Notes |
|---|---|---|
| I. User-Centricity | PASS | Adds requested capability directly to existing Mode 3 UX without introducing new required flags. |
| II. Automation | PASS | Behavior remains scheduler-safe with deterministic error/warning output. |
| III. Personalization | PASS | Recommendations remain seeded from user-provided artist/track context. |
| IV. Extensibility | PASS | Keeps modular routing between recommendation providers and modes. |
| V. Reliability | PASS | Explicit best-effort, fallback boundaries, and skipped-track reporting reduce failure ambiguity. |
| Quality Gate: Error handling for unattended execution | PASS | Feature specifies validation, fallback constraints, and concise warning output. |
| Quality Gate: Modular design | PASS | Changes are localized to CLI orchestration and service interfaces. |
| Quality Gate: Dependency management via uv | PASS | No new dependency required. |
| Quality Gate: Documentation updates required | PASS | README and quickstart updates are part of deliverables. |

No constitutional violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/007-gemini-mode3-support/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── gemini-mode3-contract.md
└── tasks.md
```

### Source Code (repository root)
```text
src/
├── cli/
│   └── main.py
├── services/
│   ├── gemini_service.py
│   ├── tidal_service.py
│   └── lastfm_service.py
└── lib/
  ├── auth.py
  └── logging.py

tests/
├── test_cli.py
└── test_tidal_service.py

README.md
```

**Structure Decision**: Use the existing single-project CLI structure. This feature extends existing command orchestration and service collaboration paths rather than introducing new subsystems.

## Phase 0 Research Output

- `research.md` will resolve Mode 3 Gemini routing behavior, seed ambiguity handling, best-effort count semantics, and unresolved-track insertion/reporting policy.

## Phase 1 Design Output

- `data-model.md` defines single-seed Gemini request/processing/outcome entities and validation rules.
- `contracts/gemini-mode3-contract.md` defines CLI behavior contract for Mode 3 + Gemini interactions and output expectations.
- `quickstart.md` documents usage examples and manual verification steps for standard and deep-cuts Mode 3 Gemini runs.

## Post-Design Constitution Check

| Principle / Gate | Status | Notes |
|---|---|---|
| I. User-Centricity | PASS | Quickstart and contract keep user-facing semantics explicit and minimal. |
| II. Automation | PASS | Warnings and best-effort behavior support unattended scheduled execution. |
| III. Personalization | PASS | Single-seed context remains primary recommendation driver. |
| IV. Extensibility | PASS | Contract formalizes provider behavior boundaries for future extensions. |
| V. Reliability | PASS | Skip-and-report strategy avoids brittle hard-fail insertion paths. |
| Quality Gate: Error handling for unattended execution | PASS | Validation and warning outputs are deterministic and actionable. |
| Quality Gate: Modular design | PASS | Design remains within existing CLI/service interfaces. |
| Quality Gate: Dependency management via uv | PASS | No additional dependencies introduced. |
| Quality Gate: Documentation updates required | PASS | Quickstart/contract and README update requirement are explicit. |

No violations or exceptions require complexity justification.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
