# Quickstart & Verification Guide: CLI Shortcut Entrypoint

**Feature Branch**: `020-cli-shortcut`  
**Date**: 2026-09-21  
**Spec**: [spec.md](spec.md)  
**Contract**: [contracts/cli-contract.md](contracts/cli-contract.md)  

## Prerequisites

- Python 3.12+
- `uv` package manager installed
- Virtual environment created (`uv venv`)

---

## Setup & Installation

Install the package in editable mode to register the console script entrypoints:

```bash
uv pip install -e .
```

---

## Verification Scenarios

### Scenario 1: Top-Level Help via Primary Shortcut (`tde`)

Verify that `tde --help` launches cleanly and displays available subcommands:

```bash
uv run tde --help
```

**Expected Outcome**:
- Exit code: `0`
- Output includes:
  ```text
  Usage: tde [OPTIONS] COMMAND [ARGS]...

    Tidal Discovery Engine CLI

  Commands:
    organize  (alias: genre-organizer)
    radio     Dedicated track radio generator...
    recommend Generate playlists using recommendations...
  ```

---

### Scenario 2: Top-Level Help via Descriptive Alias (`tidal-discovery-engine`)

Verify that the full alias functions identically:

```bash
uv run tidal-discovery-engine --help
```

**Expected Outcome**:
- Exit code: `0`
- Output is identical to `uv run tde --help` (except executable name).

---

### Scenario 3: Subcommand Help Parity

Verify that subcommands accept arguments and display help matching the direct module invocation:

```bash
uv run tde recommend --help
uv run tde radio --help
uv run tde organize --help
```

**Expected Outcome**:
- Exit code: `0`
- Help messages and available flags match direct execution (`uv run python -m src.cli.main ...`).

---

### Scenario 4: Backward Compatibility Verification

Verify that direct module execution still functions without error or deprecation:

```bash
uv run python -m src.cli.main --help
```

**Expected Outcome**:
- Exit code: `0`
- Same top-level help text is displayed.

---

### Scenario 5: Automated Test Suite

Run the targeted automated tests verifying entrypoint resolution, console script execution, and exit codes:

```bash
uv run pytest tests/unit/test_cli_entrypoint.py
```

**Expected Outcome**:
- All tests pass with exit code `0`.
