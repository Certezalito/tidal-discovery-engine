# Implementation Plan: Gemini Model Env Configuration

**Branch**: `006-gemini-model-env` | **Date**: 2026-03-09 | **Spec**: `/specs/006-gemini-model-env/spec.md`
**Input**: Feature specification from `/specs/006-gemini-model-env/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Externalize Gemini model selection to environment configuration so operators can switch models without source-code edits. The implementation will define a deterministic model resolution order (exported env var, then .env, then default), preserve backward compatibility, and constrain fallback behavior to model-unavailable errors only.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12+  
**Primary Dependencies**: click, python-dotenv, google-genai, pydantic  
**Storage**: N/A (runtime env-based configuration only)  
**Testing**: pytest/unittest test suite (`tests/`), plus manual CLI verification  
**Target Platform**: Linux CLI runtime (also compatible with other OS where Python CLI runs)
**Project Type**: single-project CLI application  
**Performance Goals**: no measurable regression in playlist generation runtime versus current Gemini path  
**Constraints**: preserve existing Gemini defaults and output semantics; no breaking CLI flag changes  
**Scale/Scope**: narrow feature scope, touching Gemini configuration resolution and operator documentation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate Check

| Principle / Gate | Status | Notes |
|---|---|---|
| I. User-Centricity | PASS | Moves model choice into env config, reducing code-edit burden for operators. |
| II. Automation | PASS | Env-based config preserves unattended scheduled runs. |
| III. Personalization | PASS | Recommendation behavior stays user-seed driven; only model source changes. |
| IV. Extensibility | PASS | Centralized model resolution supports future provider/model changes. |
| V. Reliability | PASS | Explicit precedence, warning behavior, and constrained fallback improve predictability. |
| Quality Gate: Error handling for unattended execution | PASS | Spec requires actionable errors and non-maskable auth/quota failures. |
| Quality Gate: Modular design | PASS | Change is localized to Gemini service/config resolution path. |
| Quality Gate: Dependency management via uv | PASS | No new dependency required. |
| Quality Gate: Documentation updates required | PASS | Plan includes README/quickstart updates as deliverables. |

No constitutional violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/006-gemini-model-env/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── gemini-model-env-contract.md
└── tasks.md
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── cli/
│   └── main.py
├── services/
│   └── gemini_service.py
└── lib/
  └── logging.py

tests/
├── test_cli.py
└── test_tidal_service.py

README.md
.env.example
```

**Structure Decision**: Use the existing single-project CLI structure. The feature is implemented as a targeted change in service-layer configuration resolution with associated tests and docs updates.

## Phase 0 Research Output

- `research.md` will resolve configuration precedence, fallback trigger policy, missing/empty value handling, and documentation strategy.

## Phase 1 Design Output

- `data-model.md` defines Gemini model configuration and resolution result entities.
- `contracts/gemini-model-env-contract.md` defines the environment variable contract and runtime behavior matrix.
- `quickstart.md` provides operator setup and verification flow for model selection via .env.

## Post-Design Constitution Check

| Principle / Gate | Status | Notes |
|---|---|---|
| I. User-Centricity | PASS | Quickstart and contract make operator workflow explicit and low-friction. |
| II. Automation | PASS | Env-driven behavior remains scheduler-friendly and non-interactive. |
| III. Personalization | PASS | Feature does not alter seed-driven personalization logic. |
| IV. Extensibility | PASS | Formalized config contract allows future model additions without CLI API change. |
| V. Reliability | PASS | Explicit failure boundaries prevent inappropriate fallback masking. |
| Quality Gate: Error handling for unattended execution | PASS | Startup warning + actionable runtime errors documented. |
| Quality Gate: Modular design | PASS | Scope remains concentrated in Gemini service/config resolution. |
| Quality Gate: Dependency management via uv | PASS | No new packages introduced. |
| Quality Gate: Documentation updates required | PASS | README/quickstart updates included in deliverables. |

No violations or exceptions require complexity justification.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
