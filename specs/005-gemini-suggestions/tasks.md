# Tasks: Gemini SDK Migration

**Feature**: Refactor Gemini Integration
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Phase 1: Setup
*Project initialization and dependencies.*

- [x] T001 Remove `google-generativeai` and add `google-genai` in [pyproject.toml](pyproject.toml)

## Phase 2: Foundational
*Blocking prerequisites.*

- [x] T002 Update inputs and `GeminiService` initialization with new `genai.Client` in [src/services/gemini_service.py](src/services/gemini_service.py)

## Phase 3: User Story 1 - AI-Powered Recommendations
*Goal: Restore standard suggestion functionality with new SDK.*

- [x] T003 [US1] Define `Song` pydantic model for structured output validation in [src/services/gemini_service.py](src/services/gemini_service.py)
- [x] T004 [US1] Refactor `get_recommendations` to use `client.models.generate_content` and `types.GenerateContentConfig` in [src/services/gemini_service.py](src/services/gemini_service.py)

## Phase 4: User Story 2 - Deep Cuts Discovery
*Goal: Ensure shuffle logic persists.*

- [x] T005 [US2] Verify and adjust shuffle prompt parameters compatibility in [src/services/gemini_service.py](src/services/gemini_service.py)

## Phase 5: Resolution Pivot
*Goal: Fix 0% match rate by using String Search.*

- [x] T008 Update `Song` schema in [src/services/gemini_service.py](src/services/gemini_service.py) to make `isrc` optional (default None).
- [x] T009 Update `get_recommendations` prompt in [src/services/gemini_service.py](src/services/gemini_service.py) to request Artist/Title only (remove strict ISRC demand).
- [x] T010 Implement fallback search logic (Artist+Title) in [src/cli/main.py](src/cli/main.py) when ISRC lookup fails.

## Phase 6: Polish & Cross-Cutting
*Error handling and docs.*

- [x] T006 Implement error handling for `genai.errors` in [src/services/gemini_service.py](src/services/gemini_service.py)
- [x] T007 Update [README.md](README.md) to reflect new SDK requirement version if needed

## Dependencies
- US1 requires Phase 1 & 2.
- US2 depends on US1 implementation.

## Parallel Execution Opportunities
- None. This is a linear refactor of a single file.

## Implementation Strategy
1. **T001**: Swap dependencies.
2. **Phase 2 & 3**: Rewrite `src/services/gemini_service.py` almost entirely. It's a small file, so T002-T004 will likely happen in one big edit or closely sequential edits.
3. **Verification**: Run the tool manually.
