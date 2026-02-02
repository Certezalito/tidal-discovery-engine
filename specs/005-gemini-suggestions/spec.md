# Feature Specification: Gemini API Integration for Song Suggestions

**Feature Branch**: `005-gemini-suggestions`
**Created**: 2026-02-02
**Status**: Draft
**Input**: User description: "Add Gemini API integration for song suggestions with --gemini flag and --shuffle modifier support."

## Clarifications

### Session 2026-02-02
- Q: How do we map the AI's text-based suggestions to Tidal Track IDs? → A: Use ISRC code mechanism.
- Q: How to handle cases where the provided ISRC is not found in Tidal? → A: Log the error and skip the track (no text search fallback).
- Q: How many seed tracks should be included in the AI prompt? → A: Use the existing `--num-tidal-tracks` value as the limit.
- Q: What is the required response format from the AI to ensure reliable parsing? → A: Strict Structured JSON Schema (Artist, Title, ISRC).
- Q: How many suggestions should be requested from the AI? → A: Calculated Total (`seeds * num_similar_tracks`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI-Powered Recommendations (Priority: P1)

As a music enthusiast, I want to generate song recommendations using Google's Gemini AI so that I can get suggestions based on its broad musical knowledge base, serving as an alternative to the standard algorithmic suggestions.

**Why this priority**: Core functionality of the feature.

**Independent Test**: Can be tested by running the CLI with `--gemini` and a set of input tracks, verifying that the output contains a list of valid songs.

**Acceptance Scenarios**:

1. **Given** the user has a valid `GEMINI_API_KEY` environment variable set, **When** they run the CLI with valid input (e.g., a source playlist) and the `--gemini` flag, **Then** the application should query the Gemini API and output a list of suggested songs appearing to be popular or highly relevant matches.
2. **Given** the user does NOT have `GEMINI_API_KEY` set, **When** they run successfully with `--gemini`, **Then** the application should exit with a clear error message stating the API key is missing.

---

### User Story 2 - Deep Cuts Discovery (Priority: P2)

As a "crate digger", I want to specifically ask the AI for obscure or underground tracks similar to my input, so that I can discover music I haven't heard before.

**Why this priority**: Adds significant value by leveraging the "shuffle" flag for a distinct behavior, differentiating it from standard suggestions.

**Independent Test**: Can be tested by running with `--gemini --shuffle` and manually verifying the returned tracks are generally less mainstream than the standard result.

**Acceptance Scenarios**:

1. **Given** valid configuration and input, **When** the user runs with `--gemini --shuffle`, **Then** the application should send a specific prompt to Gemini requesting "lesser-known", "underground", or "deep cut" tracks, and output the results.

### Edge Cases

- **Missing API Key**: Application must fail fast if `--gemini` is requested but no key is present.
- **API Failure**: Network errors or API errors (e.g., invalid key, quota exceeded) should be handled gracefully with an error message to the user.
- **Malformed AI Response**: If Gemini returns text that cannot be parsed into the expected song format, the application should log the error and likely fail the batch (or retry/skip if applicable).
- **Empty Results**: If Gemini returns no songs, the application should handle this case without crashing (e.g., return empty list or usage warning).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a new CLI parameter `--gemini`.
- **FR-002**: System MUST read `GEMINI_API_KEY` from the environment variables when `--gemini` is active.
- **FR-003**: System MUST validation that `GEMINI_API_KEY` exists before attempting API calls; if missing, fail with a user-friendly error.
- **FR-004**: System MUST construct a prompt for the Gemini API that includes the input songs/context and explicitly requests the International Standard Recording Code (ISRC) for each suggested track.
- **FR-004.1**: The number of seed tracks included in the prompt MUST be determined by the existing `--num-tidal-tracks` parameter (default: 10).
- **FR-004.2**: The prompt MUST request a total number of recommendations equal to `len(seed_tracks) * num_similar_tracks`.
- **FR-005**: If `--gemini` is used WITHOUT `--shuffle`, the prompt MUST explicitly request "popular" or "highly relevant" songs similar to the input.
- **FR-006**: If `--gemini` is used WITH `--shuffle`, the prompt MUST explicitly request "lesser-known," "underground," or "deep cut" songs similar to the input.
- **FR-007**: System MUST parse the response from Gemini and map it to the application's internal "Song" structure, including the ISRC.
- **FR-007.1**: The prompt MUST instruct Gemini to return data in a strict JSON array format with keys: "artist", "title", "isrc".
- **FR-008**: System MUST output the resulting song list in the exact same format as the existing suggestion engine to ensure compatibility with downstream processing (e.g., playlist creation).
- **FR-009**: System MUST handle API exceptions (network, auth, rate limit) and display a readable error message to the CLI.
- **FR-010**: System MUST use the suggested track's ISRC to query the Tidal API for the exact matching track ID.
- **FR-011**: If an ISRC lookup fails (returns 404 or no match), the System MUST log the failure and skip that track. It MUST NOT fall back to text-based search.

### Success Criteria

- **Integration**: The `--gemini` flag successfully triggers an API call to Google Gemini.
- **Differentiation**: The `--shuffle` flag demonstrably changes the prompt sent to the API.
- **Compatibility**: The output from the Gemini integration is indistinguishable in structure from the standard suggestion output, allowing existing save/display functions to work unchanged.
- **Reliability**: Missing keys or API errors do not cause unhandled stack traces.

### Assumptions

- The users have access to a Google Cloud project with Gemini API enabled and a valid API key.
- The existing application has a mechanism to ingest input songs for suggestions (e.g., command line args or a file), which `--gemini` will also use.
- The Gemini model used (e.g., `gemini-pro`) supports the prompt structure we will design.
