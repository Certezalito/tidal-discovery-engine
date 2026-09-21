# CLI Interface Contract: `tde` & `tidal-discovery-engine`

**Feature Branch**: `020-cli-shortcut`  
**Date**: 2026-09-21  
**Spec**: [spec.md](../spec.md)  

## 1. Executable Entrypoint Contract

The application exposes two console script binaries registered via `pyproject.toml`:

```toml
[project.scripts]
tde = "src.cli.main:cli"
tidal-discovery-engine = "src.cli.main:cli"
```

### Packaging Configuration Contract

To support proper module resolution for `src.*` imports, the build configuration MUST specify:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
namespaces = true
```

---

## 2. Invocation Syntax & Equivalence

The shortcut binary `tde` and alias `tidal-discovery-engine` MUST provide 100% equivalence to direct module execution:

| Invocation Pattern | Primary Use Case | Environment Requirement |
|-------------------|------------------|-------------------------|
| `uv run tde <subcommand> [args]` | Universal terminal usage | Project directory with `uv` |
| `tde <subcommand> [args]` | Fast interactive terminal usage | Activated virtual environment (`source .venv/bin/activate`) |
| `uv run tidal-discovery-engine <subcommand> [args]` | Descriptive / formal invocation | Project directory with `uv` |
| `uv run python -m src.cli.main <subcommand> [args]` | Legacy backward-compatible execution | Project directory with `uv` |

---

## 3. Subcommand Matrix

All subcommands and options defined on the root Click group MUST be accessible identically across all invocation patterns:

### Top-Level Commands

- `tde --help` / `tde -h`: Display global help and list subcommands.
- `tde recommend`: Favorite-track recommendation generator.
- `tde radio`: Dedicated single-seed track radio generator.
- `tde organize` (alias: `genre-organizer`): Genre playlist categorization and organization.

### Exit Code Contract

| Exit Code | Condition |
|-----------|-----------|
| `0` | Success; command executed successfully or `--help` displayed |
| `1` | Runtime error, API failure, or validation failure handled by `click.ClickException` |
| `2` | Click CLI syntax error (e.g., unrecognized flag, missing required parameter) |
| `130` | Execution interrupted via `SIGINT` (Ctrl+C) |

---

## 4. Documentation & Examples Contract

In `README.md`, all command examples MUST be formatted with the primary shortcut:

- Authentication: `uv run tde recommend`
- Recommendations: `uv run tde recommend [options]`
- Track Radio: `uv run tde radio --artist "..." --track "..." [options]`
- Genre Organization: `uv run tde organize [options]`
- Setup instructions MUST explain that `uv pip install -e .` exposes `tde`, and note that `tde` can be run directly when the virtual environment is activated.
