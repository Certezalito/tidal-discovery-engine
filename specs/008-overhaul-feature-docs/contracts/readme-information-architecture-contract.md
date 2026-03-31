# Contract: README Information Architecture

## Purpose
Define mandatory structure and content rules for the README overhaul so implementation and review remain consistent.

## Contract Scope
- In scope: `README.md`
- Out of scope: quickstart files, runtime code, CLI behavior changes

## Required Top-Level Order
1. Setup
2. Modes
3. All Parameters
4. Troubleshooting
5. Scheduling

## Section Contracts

### Setup
- MUST include environment and dependency setup steps.
- MUST include any required authentication/session prerequisites.

### Modes
- MUST describe Mode 1, Mode 2, and Mode 3.
- MUST include at least one runnable command example for each mode.
- MUST explain mode intent in plain language.

### All Parameters
- MUST provide a single authoritative option reference.
- MUST include option purpose, default behavior, and mode applicability.
- MUST define required option pairings and relevant constraints.

### Troubleshooting
- MUST include at least two failure categories.
- Each category MUST be structured as: symptoms -> explanation -> corrective action.
- MUST clarify fallback or non-fallback behavior where applicable.

### Scheduling
- MUST preserve unattended execution guidance and include at least one scheduler example.

## Consistency Rules
- Terminology for modes, flags, and outcomes MUST remain consistent across sections.
- Contradictory or duplicate normative guidance across sections is forbidden.

## Verification Criteria
- Two maintainer peer reviews confirm contract compliance.
- Documentation audit finds zero contradictions for mode/option/fallback guidance.
