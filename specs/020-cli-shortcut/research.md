# Research & Technical Decisions: CLI Shortcut Entrypoint

**Feature Branch**: `020-cli-shortcut`  
**Date**: 2026-09-21  
**Spec**: [spec.md](spec.md)  

## Overview

This research document analyzes the packaging architecture, build backend integration, and CLI entrypoint mechanisms needed to transition Tidal Discovery Engine from verbose module execution (`uv run python -m src.cli.main`) to concise, ergonomic shortcuts (`tde` and `tidal-discovery-engine`).

---

## Technical Decisions

### 1. Entrypoint Mechanism (PEP 621 `[project.scripts]`)

- **Decision**: Define the entry points using the standard PEP 621 `[project.scripts]` table in `pyproject.toml`:
  ```toml
  [project.scripts]
  tde = "src.cli.main:cli"
  tidal-discovery-engine = "src.cli.main:cli"
  ```
- **Rationale**:
  - `[project.scripts]` is the universal Python packaging standard for console script entrypoints across `uv`, `pip`, `pipx`, and modern build tools.
  - Both shortcuts target `src.cli.main:cli`, the existing Click root command group.
  - Providing both `tde` (primary concise shortcut) and `tidal-discovery-engine` (full descriptive alias) directly fulfills Constitution Principle IX (CLI Ergonomics & Friction Reduction).
- **Alternatives Considered**:
  - *Custom shell wrapper script*: Placing a shell script `tde` in the project root would not be cross-platform (Windows PowerShell / cmd vs Linux/macOS bash) and would not install cleanly into virtual environment `bin/` directories.
  - *Single shortcut name only (`tde`)*: Misses the descriptive alias matching the project/repository name.
  - *Click context aliasing only*: Click aliases only affect subcommands (e.g. `genre-organizer` vs `organize`), not the top-level operating system binary name.

---

### 2. Build Backend & Package Discovery Configuration

- **Decision**: Configure standard `[build-system]` using `setuptools>=61.0` with explicit package discovery for `src*` and namespace support:
  ```toml
  [build-system]
  requires = ["setuptools>=61.0"]
  build-backend = "setuptools.build_meta"

  [tool.setuptools.packages.find]
  where = ["."]
  include = ["src*"]
  namespaces = true
  ```
  and add `src/__init__.py`.
- **Rationale**:
  - All application code and tests import modules via the `src.` namespace (e.g., `from src.lib.logging import ...`, `from src.services import ...`).
  - Standard `src` layout in packaging tools typically strips the `src/` prefix and installs child directories (`cli`, `lib`, `services`) at the top level. Without explicit package discovery (`include = ["src*"]`, `namespaces = true`), installing the wheel/editable package causes `ModuleNotFoundError: No module named 'src'` when the entrypoint attempts `from src.cli.main import cli`.
  - Adding `src/__init__.py` alongside `tool.setuptools.packages.find` ensures `src` is properly discovered as a package by both `setuptools` and `uv` in editable and wheel builds.
  - The repository historically used setuptools (evidenced by existing `src/tidal_discovery_engine.egg-info`), making `setuptools>=61.0` the natural, non-disruptive choice.
- **Alternatives Considered**:
  - *Refactoring all imports to remove `src.` prefix*: Would require modifying dozens of files across `src/` and `tests/`, creating high risk of regressions and merge conflicts. Rejected in favor of preserving import integrity.
  - *`hatchling` backend*: While supported by `uv`, `hatchling` requires custom wheel target package declarations (`packages = ["src"]`). `setuptools` is already the established backend in this codebase.

---

### 3. Documentation & Usage Convention

- **Decision**: Standardize all README examples on `uv run tde <command>`, while documenting that `tde <command>` works directly when the virtual environment is activated, and noting that `uv run python -m src.cli.main` remains functional for backward compatibility.
- **Rationale**:
  - Running `uv run tde ...` guarantees that the command executes in the correct virtual environment with all dependencies resolved, even if the user has not run `source .venv/bin/activate`.
  - Direct invocation `tde ...` provides the ultimate 3-keystroke convenience for active terminal sessions.
  - Fulfills Constitution Principle I (User-Centricity & Understandability) and Principle IX (CLI Ergonomics).
- **Alternatives Considered**:
  - *Documenting only bare `tde`*: Can cause confusion if a user opens a fresh terminal and runs `tde` before activating the environment, leading to `command not found`.

---

### 4. Automated Testing & Verification Strategy

- **Decision**: Add automated CLI entrypoint tests using `subprocess` and Click's `CliRunner` to verify:
  1. Direct Click command group execution via `src.cli.main:cli`.
  2. Subcommand invocation parity across `recommend`, `radio`, and `organize`.
  3. `uv run tde --help` and `uv run tidal-discovery-engine --help` execution and exit code verification.
  4. Backward-compatible module invocation (`python -m src.cli.main --help`).
- **Rationale**:
  - Fulfills Constitution Principle V (Reliability & Verifiability) and Quality Gates.
  - Prevents regressions in entrypoint packaging across future dependencies or build backend changes.
