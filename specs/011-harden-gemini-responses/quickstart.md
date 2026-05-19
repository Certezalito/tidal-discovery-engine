# Quickstart: Harden Gemini Responses

## What Changed

Gemini-backed playlist generation now treats empty or unusable structured responses as a provider problem instead of silently accepting them as a normal zero-recommendation result. Weak responses receive exactly one recovery retry, and repeated failures surface an actionable Gemini-specific error.

## Basic Usage

Run Gemini mode as usual:

```bash
uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini"
```

Run Gemini mode with favorite-track exclusion:

```bash
uv run python -m src.cli.main --gemini --exclude-favorites --playlist-name "TDE Gemini No Favorites"
```

## How to Read Gemini Failures

- `APIError.code = 400, 401, 403, 404, 422`: configuration, auth, model, or request problems. Preserve existing fallback-model behavior only if configured; otherwise fail immediately and fix the input or environment.
- `APIError.code = 429` or any `5xx`: transient provider failure. The CLI may retry according to the bounded recovery policy.
- Empty parsed response with no usable candidates: the provider answered, but the result was not usable. The CLI retries exactly once, then fails with a Gemini response-handling error if the problem persists.
- `prompt_feedback.block_reason` or terminal `finish_reason` values such as `SAFETY`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `MALFORMED_FUNCTION_CALL`, or `UNEXPECTED_TOOL_CALL`: the response is not usable for playlist generation and should be treated as a provider-side failure path.

## Example Failure Message

When recovery is exhausted, users should expect a message in the shape of:

```text
Gemini request failed. model='gemini-3.1-pro-preview', category='client', details='...'. Next step: Review request configuration and model identifiers.
```

If the issue was a weak but successful response, the message should clearly identify Gemini response handling rather than exclude-favorites filtering.

## Troubleshooting

1. If the error mentions a model name and a not-found or unavailable condition, verify `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL`.
2. If the error mentions auth or permission issues, verify `GEMINI_API_KEY` and account access.
3. If the error mentions `429` or a `5xx` code, wait and retry the same command.
4. If `--exclude-favorites` is enabled and the run still fails before filtering starts, the root cause is Gemini response handling, not favorites exclusion.