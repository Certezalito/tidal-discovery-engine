# Research: Gemini SDK Migration

**Feature**: Gemini Suggestions Refactor
**Status**: Complete
**Date**: 2026-02-02

## Decision Log

### SDK Selection
**Decision**: Use `google-genai` (v1.0+) instead of `google-generativeai`.
**Rationale**: 
1. The `google-generativeai` package is deprecated.
2. The user explicitly requested the new package.
3. The new SDK offers better structured output support via Pydantic integration, which aligns with our requirement for strict JSON responses (ISRC/Artist/Title).

### Migration Strategy
**Decision**: Direct swap of the service layer.
**Rationale**: The `gemini_service.py` is an internal implementation detail. The format of the data returned to the CLI (`Song` objects) remains unchanged. Therefore, `main.py` requires no changes other than potentially updated error handling if exceptions differ.

### Implementation Details
- **Package**: `google-genai`
- **Import**: `from google import genai`
- **Client**: `client = genai.Client(api_key=...)`
- **Call**: `client.models.generate_content(...)`
- **Config**: `types.GenerateContentConfig(response_mime_type='application/json', response_schema=...)`

## Unknowns & Clarifications
- **Status**: All Resolved.
- **ISRC Resolution**: Remains unchanged (using `tidal_service`).
