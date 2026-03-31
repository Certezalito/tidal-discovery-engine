# Quickstart: Documentation Overhaul Validation

## Goal
Validate that README documentation has been overhauled for clarity, consistency, and maintainability without changing runtime behavior.

## Prerequisites
- Feature branch `008-overhaul-feature-docs` checked out.
- Baseline understanding of current CLI modes/options.
- Local shell available for command example verification.

## 1. Verify required top-level README structure

Confirm `README.md` sections appear in this exact order:
1. Setup
2. Modes
3. All Parameters
4. Troubleshooting
5. Scheduling

Expected result:
- Top-level ordering matches exactly with no duplicated section purpose.

## 2. Verify per-mode example coverage

Check that README includes at least one runnable command example for:
- Mode 1 (Last.fm-based flow)
- Mode 2 (Gemini flow)
- Mode 3 (single-seed flow)

Expected result:
- Every mode has a concrete command and plain-language expected outcome.

## 3. Verify option dependency clarity

Check README guidance for:
- Required option pairs (for example, `--artist` with `--track`)
- Invalid combinations or constraints where applicable

Expected result:
- Dependency rules are explicit and consistent with CLI behavior.

## 4. Verify troubleshooting entry format

Inspect troubleshooting section and confirm each failure entry includes:
- Symptoms
- Explanation
- Corrective action

Expected result:
- At least two failure/fallback scenarios are documented in structured prose.

## 5. Validate maintainability checklist

Open `specs/008-overhaul-feature-docs/checklists/docs-update.md` and verify all required README sections are represented.

Expected result:
- Checklist can be used by maintainers for future documentation updates.

## 6. Peer review completion gate

Have at least two maintainers review README and checklist outputs.

Expected result:
- Review confirms command-path clarity, consistency, and absence of contradictory guidance.
