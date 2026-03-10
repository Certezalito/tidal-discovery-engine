# Quickstart: Gemini Model Env Configuration

## Goal
Configure Gemini model selection via environment variables without modifying source code.

## Prerequisites
- Valid GEMINI_API_KEY configured for the runtime.
- Existing project setup completed (virtual environment, dependencies, and Tidal auth).
- Environment template available at .env.example.

## 1. Configure .env

Add or update values in your .env file:

```bash
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-pro
GEMINI_FALLBACK_MODEL=gemini-2.0-flash
```

Notes:
- GEMINI_MODEL is optional; if omitted or blank, the system logs one warning and uses default behavior.
- GEMINI_FALLBACK_MODEL is optional and only used when provider reports primary model unavailable/not found.

## 2. Optional override at runtime

Export GEMINI_MODEL in the shell to override .env for a specific run:

```bash
export GEMINI_MODEL=gemini-2.0-flash
uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini Test"
```

## 3. Verify behavior

Run a Gemini-backed playlist generation:

```bash
uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini Env"
```

Expected checks:
- The configured primary model is used when set.
- If GEMINI_MODEL is missing/blank, one startup warning appears and run continues with default model.
- If primary model is unavailable and GEMINI_FALLBACK_MODEL is set, one fallback attempt is made.
- Auth/quota/permission errors do not trigger fallback.

## 4. Troubleshooting

- Invalid model name:
  - Symptom: provider rejects configured model.
  - Action: correct GEMINI_MODEL to a valid model ID available to your account.
- Missing GEMINI_API_KEY:
  - Symptom: Gemini mode fails before recommendations.
  - Action: set GEMINI_API_KEY in environment.
- Unexpected fallback behavior:
  - Confirm failure type is model unavailable/not found; other errors should fail directly.

## 5. Verification Evidence Template

Use this table for T022 and T023.

| Scenario ID | Command | Env Setup | Expected Result | Actual Result | Pass/Fail | Evidence |
|---|---|---|---|---|---|---|
| EV-001 | `uv run python - <<'PY' ... _resolve_primary_model ... PY` | `GEMINI_MODEL='  gemini-test-model  '` | Primary model resolves from env with trimming | `gemini-test-model`, source `env` | Pass | `EV-001-primary gemini-test-model env` |
| EV-002 | `uv run python - <<'PY' ... _resolve_primary_model ... PY` | `GEMINI_MODEL` unset | Default model selected and one warning emitted | `gemini-2.0-flash`, source `default`, warning logged | Pass | `EV-002-primary gemini-2.0-flash default` |
| EV-003 | Runtime integration (provider unavailable/not-found simulation) | Invalid primary + configured fallback | One fallback attempt | Not executed in local automation (requires provider-level unavailable response) | Deferred | Covered by implementation path in `src/services/gemini_service.py` |
| EV-004 | `uv run python - <<'PY' ... _classify_client_error ... PY` | Synthetic auth/quota/permission failures | No fallback categories for auth/quota/permission | `permission False`, `quota False`, `auth False` | Pass | Classification output from helper verification run |
| EV-005 | `grep -n "DEFAULT_GEMINI_MODEL" src/services/gemini_service.py` | `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL` unset | Baseline default model parity preserved | Default remains `gemini-2.0-flash` | Pass | `DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"` |

Minimum required scenarios:
- EV-001: GEMINI_MODEL set to valid model (configured model is used).
- EV-002: GEMINI_MODEL missing/blank (one warning per CLI invocation plus default path).
- EV-003: Invalid primary model with unavailable/not-found response (fallback attempted if configured).
- EV-004: Auth/quota/permission failure (no fallback and actionable error content).
- EV-005: GEMINI_MODEL and GEMINI_FALLBACK_MODEL unset baseline parity check.

## 6. User Story Verification Procedures

### US1 - Configure model without code edits
1. Set `GEMINI_MODEL` in `.env` or exported environment variable.
2. Run `uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini Env"`.
3. Change `GEMINI_MODEL` value and rerun the command.
4. Confirm logs show the new selected model and source.

### US2 - Missing or blank model configuration
1. Remove `GEMINI_MODEL` or set it to blank/whitespace.
2. Run `uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini Default"`.
3. Confirm one warning per CLI invocation and default-model continuation.

### US3 - Invalid model and fallback boundaries
1. Set invalid `GEMINI_MODEL` and optional valid `GEMINI_FALLBACK_MODEL`.
2. Run Gemini workflow and verify fallback is attempted only for unavailable/not-found responses.
3. Validate auth/quota/permission failures do not trigger fallback and include actionable error content.

## 7. End-to-End Walkthrough Notes (T021)

- Completed command sanity walkthrough with `uv run python -m src.cli.main --help`.
- CLI options and Gemini flags rendered correctly.
- Full provider-backed execution remains environment-dependent (credentials, Tidal/Gemini availability).

## 8. Quality Check Outcomes (T022)

- `uv run --with pytest pytest -q`: failed during collection because `pytest` could not import `src` in this environment (`ModuleNotFoundError: No module named 'src'`).
- `uv run --with ruff ruff check .`: failed due to pre-existing lint issues in `src/services/tidal_service.py` and `tests/test_tidal_service.py` unrelated to this feature scope.
- These checks were recorded for visibility; no additional feature-specific lint/test failures were introduced by the Gemini model env changes.
