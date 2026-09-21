# Feature Specification: CLI Shortcut Entrypoint

**Feature Branch**: `020-cli-shortcut`  
**Created**: 2026-09-21  
**Status**: Draft  
**Input**: User description: "this project is called via uv run python -m src.cli.main, i believe we can change that to cli shortcut"

## Clarifications

### Session 2026-09-21

- Q: Which executable command name(s) should be configured as the CLI shortcut? (FR-001) → A: Both `tde` (primary concise command) and `tidal-discovery-engine` (full descriptive alias).
- Q: How should the CLI shortcut commands be formatted in the user-facing documentation (README)? (FR-007) → A: Use `uv run tde <command>` as primary format across README examples, noting that bare `tde <command>` is available when the virtual environment is activated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Direct CLI Invocation via Shortcut (Priority: P1)

As a music listener and command-line user, I want to execute Tidal Discovery Engine commands using a concise CLI command name (`tde`) or full alias (`tidal-discovery-engine`), so that I can run playlist generation, radio curation, and library organization quickly without typing long module paths.

**Why this priority**: Minimizing typing friction and command complexity directly improves usability and everyday adoption. Users interact with the application solely through the CLI, so having a short and memorable entrypoint is fundamental to the user experience.

**Independent Test**: Execute `tde --help` (and `tidal-discovery-engine --help`) in the terminal environment. Verify that the command runs immediately, presents the top-level help text, and displays the list of available subcommands without requiring module execution syntax.

**Acceptance Scenarios**:

1. **Given** the user is working in the terminal environment with the application installed, **When** they invoke `tde --help`, **Then** the system outputs the main CLI help text and lists all available subcommands (`recommend`, `radio`, `organize`).
2. **Given** the user invokes `tidal-discovery-engine --help`, **When** the command executes, **Then** the system outputs the exact same help text and options as `tde --help`.
3. **Given** the user runs `tde` with no arguments, **When** the entrypoint runs, **Then** the system prints standard usage information and exits gracefully.

---

### User Story 2 - Full Feature and Argument Parity with Direct Invocation (Priority: P2)

As an active user of the CLI commands (`recommend`, `radio`, `organize`), I want all subcommands, options, and behaviors to function identically when using the shortcut command as they do when invoked directly via the module path, so that my existing knowledge and parameter habits remain unchanged.

**Why this priority**: Users rely on diverse flags (such as `--gemini`, `--exclude-favorites`, `--shuffle`, `--folder`, `--playlist-name`). The shortcut must provide complete functional equivalence without dropping or modifying any command argument or capability.

**Independent Test**: Execute subcommands (e.g., `tde recommend --help`, `tde radio --help`, `tde organize --help`) and verify that all options, flags, and descriptions match direct module execution exactly. Run a sample execution and verify that logs, exit codes, and output are completely identical.

**Acceptance Scenarios**:

1. **Given** the user runs `tde recommend [options]`, **When** the command executes, **Then** recommendations are generated and saved with the exact behavior and parameters as direct module invocation.
2. **Given** the user runs `tde radio --artist "..." --track "..." [options]`, **When** the command executes, **Then** the radio playlist generation flow executes with identical parameter handling and behavior.
3. **Given** the user runs `tde organize [options]`, **When** the command executes, **Then** the genre organization flow executes with identical options and interactive confirmation prompts.
4. **Given** the user passes invalid arguments or triggers an error under `tde`, **When** validation fails, **Then** the command exits with the exact same error messages and exit code as direct module invocation.

---

### User Story 3 - Updated User Documentation & Backward Compatibility (Priority: P3)

As a new or returning user reading the project documentation (README), I want the quickstart instructions and command examples to feature the concise CLI shortcut (`uv run tde <command>`) as the standard invocation syntax, while keeping direct execution (`tde`) documented for activated environments and preserving direct module execution (`python -m src.cli.main`) for existing automated scripts.

**Why this priority**: Clear documentation ensures users discover and use the ergonomic command name immediately without environment confusion. Preserving backward compatibility guarantees that existing cron jobs or scripts do not break.

**Independent Test**: Inspect the project README to confirm all command examples utilize the concise shortcut syntax (`uv run tde <command>`), note that `tde <command>` works with activated virtual environments, and verify that invoking the legacy syntax (`python -m src.cli.main <command>`) still executes the application successfully.

**Acceptance Scenarios**:

1. **Given** a user reads the setup and command instructions in `README.md`, **When** reviewing command examples, **Then** all quickstart and feature examples display the concise command syntax (`uv run tde <command>`), with a clear note that `tde <command>` works directly when the virtual environment is activated.
2. **Given** an existing automation workflow or user invokes `python -m src.cli.main recommend`, **When** the command runs, **Then** it continues to function as before without deprecation failure.
3. **Given** documentation introduces the shortcut, **When** users follow the installation instructions, **Then** guidance clearly describes how the shortcut becomes available upon installation.

---

### Edge Cases

- **Command Invocation Outside Active Virtual Environment**: If a user runs bare `tde` in a shell where the virtual environment is not activated or on `PATH`, the system shell reports `command not found`. Documenting `uv run tde` as the primary syntax provides an out-of-the-box command that works reliably without requiring shell activation.
- **Execution with No Subcommand Provided**: Running `tde` without subcommands must output the usage overview and exit with standard CLI status, without raising unhandled exceptions or stack traces.
- **Unrecognized Subcommands or Typos**: Invoking `tde unknown-command` must produce a clear, standard error indicating the command is not recognized and suggest available valid commands.
- **Signal Handling and Interrupts**: Pressing Ctrl+C during a long-running shortcut command (e.g. genre organization or radio generation) must terminate the process cleanly with standard interrupt exit codes, matching direct invocation behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a concise executable command named `tde` for terminal invocation.
- **FR-002**: System MUST provide a descriptive executable alias named `tidal-discovery-engine` providing identical capabilities to `tde`.
- **FR-003**: All existing subcommands (`recommend`, `radio`, `organize` / `genre-organizer`) and their respective arguments and options MUST be accessible via the shortcut commands.
- **FR-004**: Invoking commands via the shortcut MUST yield identical exit codes, console output streams (stdout and stderr), and logging behavior as invoking them via module execution.
- **FR-005**: Invoking the shortcut without arguments or with `--help` MUST display top-level CLI guidance and list all available subcommands.
- **FR-006**: Direct module-based execution (`python -m src.cli.main`) MUST continue to be supported without regression or breaking changes.
- **FR-007**: User documentation (`README.md`) MUST present `uv run tde <command>` as the primary invocation method across all setup steps and feature command examples, note that `tde <command>` works directly when the virtual environment is activated, and document that legacy module invocation (`python -m src.cli.main`) remains supported.

### Key Entities *(include if feature involves data)*

- **CLI Entrypoint**: The registered command-line binary interface (`tde` / `tidal-discovery-engine`) that routes user input, flags, and subcommands to the application command controller.
- **Command Session**: An interactive or non-interactive execution of a specific subcommand, maintaining credentials, logging context, and exit status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can invoke commands typing at least 60% fewer characters in the command prefix (e.g., `uv run tde <subcommand>` vs `uv run python -m src.cli.main <subcommand>`).
- **SC-002**: 100% of existing CLI commands, subcommands, and options function with identical output and exit codes when invoked through the shortcut.
- **SC-003**: 100% of command-line examples in the user-facing documentation (`README.md`) demonstrate the concise shortcut syntax (`uv run tde`).
- **SC-004**: Zero regressions or breaking changes for users or automated workflows invoking the CLI via the existing module path.
- **SC-005**: Invoking the CLI shortcut with `--help` displays complete usage instructions within 1 second on standard systems.

## Assumptions

- Users install the project using the standard package and environment management tooling recommended in the repository (`uv`).
- The primary, ergonomic command name is `tde`, representing the project's standard abbreviation, and `tidal-discovery-engine` is provided as a full-name alias.
- Environment variable discovery (`.env`) and local credentials (`tidal_session.json`) work identically regardless of whether the tool is launched via the shortcut or directly via the module path.
