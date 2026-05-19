# Gemini Response Recovery Contract

## Purpose

Define how the CLI interprets Gemini response status signals when generating playlist recommendations.

## Contract

### Usable Response

A Gemini response is usable only when the structured payload can be parsed into recommendation records and the response does not report a blocking or terminal failure condition.

### Retryable Conditions

- `APIError.code = 429`
- `APIError.code >= 500`
- Transport timeouts or transient server failures reported by the SDK
- Empty parsed response when the provider call otherwise succeeded; exactly one recovery retry is allowed

### Non-Retryable Conditions

- `APIError.code = 400`
- `APIError.code = 401`
- `APIError.code = 403`
- `APIError.code = 404`
- `APIError.code = 422`
- Prompt or candidate terminal states indicating blocked, prohibited, malformed, or unsupported output

### Fallback Rule

- For non-retryable status failures, preserve existing fallback-model behavior only when a fallback model is already configured.
- If no fallback model is configured, fail immediately.

### Failure Behavior

If the single recovery retry is exhausted for weak/empty responses, or the response is non-retryable with no configured fallback path, the CLI must stop playlist generation, surface a Gemini-specific error, and avoid attributing the failure to exclude-favorites filtering.

### Example CLI Outcome

```text
Gemini request failed. model='gemini-3.1-pro-preview', category='quota', details='...'. Next step: Check Gemini quota/rate limits and retry later.
```

or, for a weak structured response:

```text
Gemini returned empty parsed response for model 'gemini-3.1-pro-preview'. Retrying...
```