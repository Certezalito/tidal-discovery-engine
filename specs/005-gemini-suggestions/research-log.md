# Research: ISRC Hallucination & Resolution

**Date**: 2026-02-03
**Status**: Pivot Decision Required

## Problem
The Gemini AI is providing hallucinations for ISRC codes.
- **Example**: Suggested "Wait and Bleed" by Slipknot with ISRC `USUR19900130`.
- **Reality**: That ISRC does not exist or does not match that song in Tidal's catalog.
- **Root Cause**: LLMs are probabilistic, not databases. They generate valid-looking strings that are often factually incorrect.

## Options

### 1. Enable Google Search Grounding (`tools`)
- **Pros**: Might find real ISRCs by verifying via Google Search.
- **Cons**: Still relies on LLM parsing search results. ISRC data is often hidden in API databases, not open web pages.
- **Complexity**: Low (Config change).

### 2. Pivot to String Search Resolution (Recommended)
- **Change**: Modification of `GeminiService` to ask only for `Artist` and `Title` (remove ISRC constraint).
- **Resolver**: Use `tidal_service.search_for_track` (which already exists) instead of `get_track_by_isrc`.
- **Pros**: Match rate will jump from ~0% to ~95%.
- **Cons**: Might match "Remastered" or "Live" versions if not specified.
- **Mitigation**: Tidal's search is generally good at surfacing the "Best Match".

## Recommendation
**Option 2 (String Search)**.
Tidal's own search engine is the best tool for finding a Tidal ID given an Artist/Title. Using the LLM to generate the *idea* and the Service to *locate* it is the correct separation of concerns.

## Plan
1. Update `Song` schema in `gemini_service.py` to make `isrc` optional or remove it.
2. Update Prompt in `gemini_service.py` to stop demanding ISRCs (which causes checking overhead).
3. Update `main.py` loop:
    - If `isrc` is present (and valid), try it.
    - If logic fails or `isrc` missing, fallback to `tidal_service.search_for_track(artist, title)`.
