# Implementation Plan - Gemini SDK Migration

## Technical Context

**Feature**: Refactor Gemini Integration to use `google-genai` SDK
**Status**: Approved
**System**:
- **Language**: Python 3.11+
- **Frameworks**: `google-genai` (New SDK), `pydantic` (for schema validation)
- **Architecture**: Service Repository Pattern (`GeminiService` encapsulates API calls)
- **Dependencies**: Remove `google-generativeai`, Add `google-genai`

**Unknowns**:
- None. API syntax for v1 SDK is researched.

## Constitution Check

| Principle | Status | Notes |
| :--- | :--- | :--- |
| **User-Centricity** | ✅ | No change to CLI UX. |
| **Automation** | ✅ | Continues to support unattended suggestions. |
| **Personalization** | ✅ | Logic for "popular" vs "deep cuts" is preserved. |
| **Extensibility** | ✅ | New SDK is more robust for future model updates. |
| **Reliability** | ✅ | New SDK type checking improves stability. |

## Feature Gates

| Gate | Status | Notes |
| :--- | :--- | :--- |
| **UX Design** | ✅ | Existing CLI flags (`--gemini`) remain. |
| **Security** | ✅ | API Key handling via Env Vars confirmed. |
| **Test Plan** | ✅ | Existing verification script should pass after refactor. |

## Phases

### Phase 1: Dependency Management
*Swap the libraries.*

1. **Remove Old SDK**: `uv remove google-generativeai`
2. **Add New SDK**: `uv add google-genai`

### Phase 2: Service Refactoring
*Update the code to match the new API.*

1. **Update `src/services/gemini_service.py`**:
   - Change imports to `from google import genai`.
   - Update `__init__` to instantiate `client = genai.Client()`.
   - Refactor `get_recommendations`:
     - Use `client.models.generate_content`.
     - Use `types.GenerateContentConfig` for JSON enforcement via a new `Song` Pydantic model (Schema: Artist, Title, ISRC).
     - **Error Handling**:
       - Capture `genai.errors.ClientError` (e.g., Auth failures) -> Raise `ValueError` for CLI to handle.
       - Capture `genai.errors.ServerError` / `ServiceUnavailable` -> Log and raise friendly SystemError.
       - Capture Pydantic `ValidationError` (malformed AI response) -> Log error and return empty list (or retry if logic permits).
     - **Sync Execution**: Use standard synchronous `generate_content` (no async/await) to match existing architecture.

### Phase 3: Verification
*Ensure no regressions.*

1. **Run Verification Script**: Execute the existing manual test/script to verify suggestions are still generated and parsed correctly.
2. **Check Error Handling**: Verify invalid API key behavior.

### Phase 4: Resolution Reliability (Pivot)
*Switch from Hallucinating ISRCs to String Search.*

1. **Update `src/services/gemini_service.py`**:
    - Remove ISRC requirement from Prompt.
    - Make `isrc` optional in `Song` schema.
2. **Update `src/cli/main.py`**:
    - Add fallback: If ISRC is missing or lookup fails, call `tidal_service.search_for_track(artist, title)`.
    - Retain logging to compare methods (Hybrid approach).
