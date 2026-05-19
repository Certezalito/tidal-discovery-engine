# Data Model: Harden Gemini Responses

## GeminiRecommendationResponse

Represents the provider response returned by `google-genai` for a recommendation request.

### Fields

- `parsed`: Parsed structured output from the SDK, expected to be a list of recommendation records when usable.
- `candidates`: Candidate list returned by Gemini.
- `prompt_feedback.block_reason`: Optional reason the prompt or response was blocked.
- `prompt_feedback.block_reason_message`: Human-readable explanation of the block condition.
- `candidates[].finish_reason`: Terminal reason each candidate completed.

### State

- `usable`: Parsed payload exists and contains recommendation data that can be consumed.
- `unusable-empty`: Transport succeeded, but parsed output is empty.
- `unusable-blocked`: Prompt feedback or finish reason indicates a blocked or terminal non-usable outcome.
- `unusable-malformed`: The response cannot be parsed into the expected recommendation shape.
- `retryable-transient`: The call failed with a retryable status such as `429` or `5xx`.
- `fatal-config`: The call failed with a non-retryable configuration/auth/model status such as `400`, `401`, `403`, `404`, or `422`.

## RecommendationRecoveryAttempt

Represents one bounded retry attempt to recover a usable Gemini recommendation response.

### Fields

- `attempt_index`: 1-based retry counter.
- `model_name`: Gemini model used for the attempt.
- `status_code`: API error code, if the attempt failed at the transport/API layer.
- `finish_reason`: Candidate finish reason, if the attempt returned a response but it was unusable.
- `result_state`: One of `usable`, `retryable-transient`, `unusable-empty`, `unusable-blocked`, or `fatal-config`.

### Transitions

- `retryable-transient` -> retry once according to the single-recovery policy.
- `unusable-empty` -> retry once.
- `unusable-blocked` -> fail closed after the bounded policy is exhausted.
- `usable` -> continue playlist generation.
- `fatal-config` -> preserve existing configured fallback behavior if present; otherwise fail immediately.

## RecommendationFailureOutcome

Represents the final user-visible failure when Gemini cannot produce a usable recommendation response.

### Fields

- `cause`: `gemini-response-handling` or `gemini-api-status`.
- `attempt_count`: Number of Gemini attempts made before failure.
- `user_message`: Actionable message displayed to the user.
- `remediation`: Suggested next step, such as checking the model name, API key, quota, or retrying later.

### Notes

- Failure outcomes must be created before exclude-favorites filtering runs so the CLI does not blame favorites exclusion for a provider failure.
- The outcome should remain distinct from the existing `ZERO_TRACKS_INSERTED` path used when valid recommendations cannot be resolved into playable tracks.