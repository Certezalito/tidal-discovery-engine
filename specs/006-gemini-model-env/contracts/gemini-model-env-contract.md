# Contract: Gemini Model Environment Configuration

## Scope
Defines operator-facing environment variables and runtime behavior for Gemini model selection.

## Configuration Keys

| Variable | Required | Description | Example |
|---|---|---|---|
| GEMINI_MODEL | No | Primary Gemini model identifier. | gemini-2.5-pro |
| GEMINI_FALLBACK_MODEL | No | Fallback model used only when primary is unavailable/not found. | gemini-2.0-flash |

## Resolution Rules

1. Determine effective primary model using precedence:
   - Exported environment variable value.
   - .env-provided value.
   - Built-in default.
2. Normalize by trimming whitespace.
3. Treat empty normalized values as missing.
4. If primary is missing, emit one startup warning and use built-in default.

## Runtime Error and Fallback Rules

| Condition | Expected behavior |
|---|---|
| Primary model succeeds | Return recommendations from primary model. |
| Provider reports primary model unavailable/not found | Attempt one request with GEMINI_FALLBACK_MODEL if configured. |
| Auth error | Do not fallback; return actionable client error. |
| Quota/permission error | Do not fallback; return actionable client error. |
| Other server/unexpected error | Do not fallback unless explicitly mapped to unavailable/not found. |

## Acceptance Contract

- Recommendations path must reflect the configured model when a non-empty value is provided.
- Missing or empty GEMINI_MODEL must not crash startup.
- Startup warning for default usage occurs at most once per CLI invocation.
- Fallback can only occur for unavailable/not found model responses.
- Canonical variable names must be documented exactly as GEMINI_MODEL and GEMINI_FALLBACK_MODEL.
