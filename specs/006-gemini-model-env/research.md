# Research: Gemini Model Env Configuration

**Feature**: 006-gemini-model-env  
**Date**: 2026-03-09  
**Status**: Complete

## Decision 1: Configuration precedence

- Decision: Resolve model value in this order: exported environment variable -> .env value -> built-in default.
- Rationale: This follows common operational expectations where deploy-time environment overrides file-based defaults while preserving backward-compatible defaults.
- Alternatives considered:
  - .env before exported env: rejected because it blocks standard deployment override patterns.
  - Require configuration with no default: rejected due to backward-compatibility risk.

## Decision 2: Missing and empty primary model handling

- Decision: Treat missing, empty, or whitespace-only GEMINI_MODEL as missing configuration; log one startup warning and use default.
- Rationale: Prevents brittle failures from formatting mistakes while still providing operator visibility.
- Alternatives considered:
  - Fail startup on missing/empty: rejected because this is a behavior-breaking change.
  - Silent fallback with no warning: rejected because it hides misconfiguration.

## Decision 3: Fallback trigger policy

- Decision: Attempt GEMINI_FALLBACK_MODEL only when the provider indicates the primary model is unavailable or not found.
- Rationale: Restricting fallback avoids masking unrelated errors (auth, quota, permissions), improving diagnosability and reliability.
- Alternatives considered:
  - Fallback on any error: rejected due to risk of hiding root causes.
  - Never fallback: rejected because optional resilience for unavailable models is a stated requirement.

## Decision 4: Canonical variable names

- Decision: Use GEMINI_MODEL as primary and GEMINI_FALLBACK_MODEL as optional fallback.
- Rationale: Aligns with current code conventions and existing repository memory, reducing migration risk.
- Alternatives considered:
  - Rename variables to new prefixes: rejected because it introduces avoidable migration complexity.

## Decision 5: Documentation and validation scope

- Decision: Update operator guidance in feature quickstart and define explicit env contract for plan/tasks implementation.
- Rationale: Constitution requires end-user documentation updates for behavior changes; contract-first planning reduces implementation ambiguity.
- Alternatives considered:
  - Document only in code comments: rejected because operators configure behavior outside code.
  - Delay docs until after implementation: rejected due to constitution quality gate.
