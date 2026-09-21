# Implementation Plan: CLI Shortcut Entrypoint

**Branch**: `020-cli-shortcut` | **Date**: 2026-09-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/020-cli-shortcut/spec.md`

## Summary

Enable concise and ergonomic command-line invocation for Tidal Discovery Engine by configuring standard console script entrypoints (`tde` and `tidal-discovery-engine`) in `pyproject.toml` pointing to `src.cli.main:cli`. Support packaging discovery via `setuptools>=61.0` with `tool.setuptools.packages.find` for `src*` and `src/__init__.py`. Update user documentation (`README.md`) to showcase `uv run tde <command>` across all quickstart guides, and implement automated tests verifying entrypoint functionality, exit codes, and backward compatibility with `python -m src.cli.main`.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: `click` (CLI framework), `uv` (environment and dependency management), `setuptools>=61.0` (build backend)  
**Storage**: N/A (packaging and CLI entrypoints only)  
**Testing**: `pytest` (targeted unit test suite for CLI entrypoints and backward compatibility)  
**Target Platform**: Cross-platform (Linux, macOS, Windows) via standard Python console scripts  
**Project Type**: Command-Line Interface (CLI) application  
**Performance Goals**: Sub-second execution and help text rendering (<1s)  
**Constraints**: Zero regression on direct module execution (`python -m src.cli.main`), 100% parameter and subcommand parity  
**Scale/Scope**: 1 package configuration file (`pyproject.toml`), 1 package init file (`src/__init__.py`), 1 documentation guide (`README.md`), 1 test module (`tests/unit/test_cli_entrypoint.py`)  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (User-Centricity & Understandability)**: PASS. Simplifies everyday command invocation, replaces verbose module paths, and comprehensively updates `README.md` examples.
- **Principle II (Automation)**: PASS. All automated workflows and non-interactive parameters function identically through the shortcut.
- **Principle IV (Extensibility)**: PASS. Entrypoints hook directly into Click command tree without tight coupling.
- **Principle V (Reliability & Verifiability)**: PASS. Automated test suite validates entrypoints, help displays, subcommand routing, and exit codes.
- **Principle IX (CLI Ergonomics & Friction Reduction)**: PASS. Primary driver of this feature: provides 3-keystroke `tde` shortcut alongside `tidal-discovery-engine` alias, cutting entrypoint typing by >60%.
- **Principle X (Critical Dependency Currency)**: PASS. Uses standard PEP 621 `[project.scripts]` and `setuptools>=61.0` build system compatible with modern `uv`.
- **Principle XI (Human Readability & Inline Intent Documentation)**: PASS. Clear comments added to `pyproject.toml` and test modules explaining packaging choices.

## Project Structure

### Documentation (this feature)

```text
specs/020-cli-shortcut/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan
├── research.md          # Technical research & decisions (Phase 0)
├── data-model.md        # Conceptual model & state flow (Phase 1)
├── quickstart.md        # Verification & quickstart guide (Phase 1)
├── contracts/           # Interface contracts (Phase 1)
│   └── cli-contract.md  # CLI entrypoint and packaging specification
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Implementation tasks (/speckit-tasks output)
```

### Source Code (repository root)

```text
pyproject.toml                   # [MODIFY] Add [project.scripts], [build-system], [tool.setuptools]
README.md                        # [MODIFY] Update CLI examples to uv run tde and document shortcut
src/
├── __init__.py                  # [NEW] Explicit package marker for src.* import resolution
└── cli/
    └── main.py                  # Preserved root click group (target of entrypoint)
tests/
└── unit/
    └── test_cli_entrypoint.py   # [NEW] Automated tests for entrypoint discovery and parity
```

**Structure Decision**: Standard single-project Python repository layout with `src/` directory. Explicit packaging configuration added to `pyproject.toml` and `src/__init__.py` to ensure clean resolution of `src.*` modules when installed via `uv pip install -e .`.

## Complexity Tracking

> *No constitutional violations. Table left blank.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None*    | *N/A*      | *N/A*                               |
