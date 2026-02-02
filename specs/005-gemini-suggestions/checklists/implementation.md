# Implementation Checklist: Gemini API Integration

**Feature**: Gemini Suggestions
**Spec**: [spec.md](../spec.md)
**Plan**: [plan.md](../plan.md)

## Configuration
- [ ] Add `google-generativeai` to `pyproject.toml`
- [ ] Run `uv sync` or equivalent to update lockfile (if applicable)

## Services
### Gemini Service
- [ ] Create `src/services/gemini_service.py`
- [ ] Implement `get_recommendations` signature
- [ ] Implement prompt construction logic (Shuffle vs Standard)
- [ ] Implement strict JSON schema prompt (Keys: artist, title, isrc)
- [ ] Implement Gemini API call
- [ ] Implement JSON parsing and error handling

### Tidal Service
- [ ] Add `get_track_by_isrc` to `src/services/tidal_service.py`
- [ ] Implement ISRC search logic

## CLI Integration
- [ ] Update `src/cli/main.py` arguments
- [ ] Add `GEMINI_API_KEY` validation
- [ ] Implement conditional flow for `--gemini`
- [ ] Integrate ISRC resolution loop
- [ ] Ensure logging covers Gemini activity

## Verification
- [ ] Verify Standard Run (Popular)
- [ ] Verify Shuffle Run (Deep Cuts)
- [ ] Verify Error Handling (Missing Key / API limits)
