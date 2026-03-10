# Data Model: Gemini Model Env Configuration

## Entities

### GeminiModelConfig
Represents operator-provided model configuration values resolved from runtime environment sources.

| Field | Type | Required | Description |
|---|---|---|---|
| primary_model_raw | string | No | Raw value from GEMINI_MODEL before normalization. |
| fallback_model_raw | string | No | Raw value from GEMINI_FALLBACK_MODEL before normalization. |
| primary_model | string | No | Normalized primary model after trimming; empty becomes null. |
| fallback_model | string | No | Normalized fallback model after trimming; empty becomes null. |
| source_primary | enum | Yes | Source of effective primary model: env, dotenv, default. |
| warning_emitted | boolean | Yes | Whether startup warning was emitted for missing primary model. |

Validation rules:
- Trim leading/trailing whitespace on model values.
- Empty normalized values are treated as null/missing.
- If primary_model is null, system must use default model and emit one startup warning.

### ModelResolutionResult
Represents effective model choice during recommendation request execution.

| Field | Type | Required | Description |
|---|---|---|---|
| selected_model | string | Yes | Model used for initial provider request. |
| selected_source | enum | Yes | Source of selected_model: env, dotenv, default. |
| fallback_attempted | boolean | Yes | Indicates whether fallback was attempted. |
| fallback_model | string | No | Fallback model attempted, if any. |
| fallback_reason | enum | No | Reason fallback activated; allowed value: model_unavailable. |
| terminal_status | enum | Yes | Outcome: success, unavailable_model_error, client_error, server_error, unexpected_error. |

Validation rules:
- fallback_reason can be set only if fallback_attempted is true.
- fallback_attempted is true only when provider reports model unavailable/not found for primary.
- Auth/quota/permission failures must not change selected_model to fallback.

## Relationships

- GeminiModelConfig is derived before request execution and used to produce ModelResolutionResult.
- ModelResolutionResult informs logging and error messages exposed to CLI workflow.

## State Transitions

1. Load config values from environment sources.
2. Normalize values (trim and empty-to-null).
3. Resolve effective primary model based on precedence.
4. Execute provider call with selected_model.
5. If model unavailable and fallback configured, execute one fallback attempt.
6. Emit final status and actionable message for non-success outcomes.
