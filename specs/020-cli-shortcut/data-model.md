# Data Model & Conceptual Architecture: CLI Shortcut Entrypoint

**Feature Branch**: `020-cli-shortcut`  
**Date**: 2026-09-21  
**Spec**: [spec.md](spec.md)  

## Conceptual Entities

This feature establishes binary entrypoints and standardizes command invocation sessions. The conceptual model defines the relationship between the terminal environment, packaging scripts, and the application runtime.

---

### 1. CLI Entrypoint

The registered console script binary that bridges the operating system shell to the Python application.

| Field / Attribute | Type | Description |
|-------------------|------|-------------|
| `binary_name` | String | Executable name (`tde` or `tidal-discovery-engine`) |
| `target_module` | String | Fully-qualified Python module path (`src.cli.main`) |
| `target_callable` | String | Name of the Click entry callable (`cli`) |
| `build_system` | Table | Packaging specification in `pyproject.toml` |
| `environment_mode` | Enum | `uv_managed` (`uv run <binary>`) or `venv_activated` (`<binary>`) |

#### Validation & Constraints

- `binary_name` MUST be either `tde` or `tidal-discovery-engine`.
- Both entrypoints MUST point to the identical target callable (`src.cli.main:cli`).
- Target callable MUST accept standard Click command-line arguments and flags.

---

### 2. Command Session

An individual execution lifecycle of the CLI tool from invocation to exit.

| Field / Attribute | Type | Description |
|-------------------|------|-------------|
| `invocation_syntax` | String | The exact command string entered by the user or script |
| `entrypoint_type` | Enum | `SHORTCUT_PRIMARY` (`tde`), `SHORTCUT_ALIAS` (`tidal-discovery-engine`), `LEGACY_MODULE` (`python -m src.cli.main`) |
| `subcommand` | Enum / String | Invoked subcommand (`recommend`, `radio`, `organize`, or None for top-level help) |
| `parameters` | Dict | Parsed CLI flags, options, and arguments |
| `exit_code` | Integer | Process termination status (`0` for success, non-zero for error) |
| `output_stream` | Stream | Standard output and error console logs |

#### Lifecycle & State Transitions

```
+-------------------+
| Terminal Launch   | User executes command (e.g. `uv run tde recommend`)
+---------+---------+
          |
          v
+-------------------+
| Entrypoint Routing| Shell / UV locates `tde` in virtualenv bin
+---------+---------+
          |
          v
+-------------------+
| Click Arg Parsing | Parses subcommand and flags (or shows help)
+---------+---------+
          |
     +----+----+
     |         |
[Valid]    [Invalid / --help]
     |         |
     v         v
+---------+ +-------------------+
| Execute | | Print Error / Help|
+----+----+ +---------+---------+
     |                |
     v                v
+-------------------------------+
| Process Termination (Exit Code)|
+-------------------------------+
```
