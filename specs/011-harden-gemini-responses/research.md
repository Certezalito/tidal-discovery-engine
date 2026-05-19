# Research: Harden Gemini Responses

**Feature**: 011-harden-gemini-responses  
**Date**: 2026-05-19  
**Status**: Complete

## Decision 1: Treat structured response usability as the primary success gate

- Decision: Treat `response.parsed` as the primary contract result for Gemini-backed recommendation generation, and treat an empty/missing parsed payload as unusable even when the HTTP request succeeded.
- Rationale: The current code path in `src/services/gemini_service.py` returns an empty list when `response.parsed` is falsey, which hides weak provider replies and causes the downstream CLI to misclassify the failure as a zero-result recommendation run.
- Alternatives considered:
  - Accept an empty parsed payload as valid success: rejected because it preserves the observed bug.
  - Use only raw text parsing: rejected because the feature already relies on the SDK response schema for structured output.

## Decision 2: Classify weak Gemini replies using provider response fields and finish reasons

- Decision: Use `response.candidates`, `response.prompt_feedback.block_reason`, `response.prompt_feedback.block_reason_message`, and `Candidate.finish_reason` to distinguish usable responses from blocked or malformed ones.
- Rationale: The Gemini SDK exposes these fields on `GenerateContentResponse`, and the generated docs show `finish_reason` as the terminal indicator for candidate completion. This gives the CLI enough information to separate a usable structured reply from a response that succeeded at transport but is not safe or parseable to use.
- Alternatives considered:
  - Inspect only `response.text`: rejected because it does not reliably distinguish valid structured JSON from weak or blocked output.
  - Retry on every empty parsed response without inspection: rejected because it hides terminal provider failures and makes logs less actionable.

## Decision 3: Interpret Gemini status codes as retryability signals

- Decision: Treat SDK/API status codes from `APIError.code` as the retry boundary: retry transient `429` and `5xx` conditions, and fail closed on configuration/auth/model errors such as `400`, `401`, `403`, `404`, and `422`. For non-retryable status failures, preserve existing fallback-model behavior only when already configured; otherwise fail immediately.
- Rationale: The SDK documentation exposes `APIError.code`, and the error hierarchy splits transport/client failures from server failures. This gives a stable basis for deciding when the CLI should retry versus stop immediately while avoiding new fallback coupling in this feature.
- Alternatives considered:
  - Retry all API errors: rejected because it would waste time on invalid configuration and inaccessible models.
  - Never retry API errors: rejected because it would make transient rate limits and server outages look permanent.

## Decision 4: Keep response recovery separate from favorites filtering

- Decision: Trigger recovery before exclude-favorites filtering runs, and attribute failures to Gemini response handling rather than favorites exclusion when the provider returns no usable recommendations.
- Rationale: The reported regression only surfaced during the exclude-favorites flow, but the actual fault was upstream. Keeping these concerns separate preserves feature correctness and clearer troubleshooting.
- Alternatives considered:
  - Let exclude-favorites handle empty recommendations as a normal outcome: rejected because it misattributes provider failure as successful filtering.
  - Fold Gemini recovery into the favorites service: rejected because it violates module boundaries and obscures responsibility.

## Decision 5: Retry policy should be bounded and conservative

- Decision: Apply exactly one recovery retry after an unusable or valid-but-empty structured Gemini response, and retry retryable transport/server statuses within the same bounded policy. If still unusable after the single recovery retry, fail closed with a Gemini-specific error.
- Rationale: The spec clarifies that valid-but-empty structured responses should not be accepted silently, while a single retry limits latency and avoids masking persistent provider issues in unattended runs.
- Alternatives considered:
  - Infinite retries: rejected as unsafe for unattended CLI runs.
  - No retries: rejected because it fails to recover from transient provider behavior.

## Decision 6: No new storage is required

- Decision: Keep all retry state and response classification in memory for the active CLI invocation.
- Rationale: The feature does not need persisted recovery state and should remain simple and privacy-preserving.
- Alternatives considered:
  - Disk cache of provider responses: rejected because it adds statefulness without solving the core failure mode.

## Evidence Collected

- `src/services/gemini_service.py` currently returns `[]` when `response.parsed` is empty, which is the behavior the hardening work must replace.
- The Gemini SDK docs expose the response fields needed for classification: `GenerateContentResponse.parsed`, `GenerateContentResponse.candidates`, `GenerateContentResponse.prompt_feedback.block_reason`, `GenerateContentResponse.prompt_feedback.block_reason_message`, and `Candidate.finish_reason`.
- The SDK docs expose `APIError.code` and split client/server failure handling, with `ClientError` covering $4xx$ and `ServerError` covering $5xx$.