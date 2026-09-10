# Feature Specification: Rename Genre Playlist Command to Genre Organizer

**Feature Branch**: `018-rename-genre-playlist`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "i want a new branch to rename the genre playlist command, all documentation/code will need updating, i want to rename to to genre organizer (unless you have an idea for less friction in the command name)"

## Clarifications

### Session 2026-09-10

- Q: How should the CLI intercept and present error guidance when users invoke the retired `genre-playlist` command? (FR-004) → A: Register a hidden `genre-playlist` command stub that outputs `Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').` and exits with code 1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute Genre Organization via Low-Friction Primary Command (Priority: P1)

As a music listener managing a Tidal library, I want to invoke the genre organization feature using the ergonomic, single-word primary command `organize` (or descriptive alias `genre-organizer`) so that I can automatically scan my library, classify tracks by genre, and sync organized genre playlists with minimal typing friction.

**Why this priority**: Establishing the low-friction primary command name `organize` aligns the CLI with existing single-word commands (`radio`, `recommend`) and fulfills Constitution Principle IX (CLI Ergonomics & Friction Reduction).

**Independent Test**: Can be fully tested by running `organize` (and alias `genre-organizer`) with valid credentials and verifying that full library scanning, genre classification, and playlist synchronization execute identically to the prior system.

**Acceptance Scenarios**:

1. **Given** an authenticated user running the primary command `organize` without flags, **When** executed, **Then** the system scans the Tidal library, classifies genres via Gemini (with local caching), creates/updates playlists in the default `Genres` folder, and presents a structured sync summary.
2. **Given** a user running the alias `genre-organizer` with flags (`--folder`, `--min-genre-size`, `--db-path`), **When** executed, **Then** the system respects all specified parameters identically to the primary command.

---

### User Story 2 - Comprehensive Internal Codebase and Test Suite Alignment (Priority: P2)

As a developer or maintainer of the project, I want the codebase naming (CLI entry points, service modules, functions, and automated tests) to consistently use genre organizer terminology so that there is no conceptual drift or confusion between code and user-facing commands.

**Why this priority**: Prevents technical debt and maintains documentation integrity across the application by ensuring service modules and test files cleanly reflect the new command domain.

**Independent Test**: Can be fully tested by executing the renamed automated test suite (`tests/test_cli_genre_organizer.py`) and verifying all unit/integration tests pass against the renamed service module and CLI handler.

**Acceptance Scenarios**:

1. **Given** the service layer, **When** importing the genre organization service, **Then** it is located at `src.services.genre_organizer_service` providing `run_genre_organizer_sync`.
2. **Given** the test suite, **When** running automated CLI and service tests, **Then** test coverage validates `organize` and `genre-organizer` with zero references to obsolete module names.

---

### User Story 3 - Immediate Guidance for Legacy Invocations (Priority: P2)

As an existing user or script runner attempting to run the retired `genre-playlist` command, I want the system to cleanly reject the retired command while providing clear, immediate guidance pointing to `organize` and `genre-organizer`.

**Why this priority**: Supports a clean break from the legacy command name while ensuring users accustomed to the previous syntax are immediately informed of the replacement without guessing or digging through logs.

**Independent Test**: Can be fully tested by invoking `genre-playlist` on the CLI and verifying that the command fails cleanly with exit code 1 and error message `Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').`.

**Acceptance Scenarios**:

1. **Given** a user invoking `genre-playlist`, **When** the command is entered, **Then** the hidden command stub executes, outputs `Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').`, and exits with code 1.

---

### User Story 4 - Consistent Documentation and Help Output (Priority: P3)

As a user consulting the project documentation or CLI help, I want `README.md`, `--help` menus, and example commands to feature `organize` and `genre-organizer` so that I can easily discover the feature and understand all configuration options.

**Why this priority**: Satisfies Constitution Principle I (User-Centricity & Understandability) by ensuring all user-facing documentation accurately describes the available commands, default values, and usage examples.

**Independent Test**: Can be fully tested by inspecting top-level `python -m src.cli.main --help` and reading `README.md` to ensure complete accuracy and zero stale references to `genre-playlist`.

**Acceptance Scenarios**:

1. **Given** a user viewing top-level CLI help (`--help`), **When** reviewing commands, **Then** `organize` and alias `genre-organizer` are displayed with their descriptions, and `genre-playlist` is hidden from the command list.
2. **Given** a user reading `README.md`, **When** consulting the genre organization section, **Then** all examples and explanations document `organize` and `genre-organizer` along with available options.

---

### Edge Cases

- What happens when a user attempts to execute the legacy command name `genre-playlist`?
  - A hidden `genre-playlist` command stub catches the invocation, outputs `Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').`, and exits with code 1.
- What happens if a user provides conflicting or unrecognized flags to `organize`?
  - Standard concise CLI validation errors are displayed indicating invalid arguments and showing correct syntax.
- What happens to existing genre cache database files (`data/genre_cache.db`)?
  - The default database cache path remains `data/genre_cache.db` so existing cached track classifications are preserved seamlessly across the command rename.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `organize` as the primary CLI command for scanning libraries, classifying genres, and synchronizing genre playlists.
- **FR-002**: System MUST provide `genre-organizer` as a supported command alias that executes identical functionality to `organize`.
- **FR-003**: System MUST support `--folder` (default `"Genres"`), `--min-genre-size` (default `10`), and `--db-path` (default `"data/genre_cache.db"`) on both `organize` and `genre-organizer`.
- **FR-004**: System MUST register a hidden `genre-playlist` command stub that exits with code 1 and outputs `Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').`.
- **FR-005**: System MUST refactor internal implementation naming to match the new domain:
  - Service module renamed to `src/services/genre_organizer_service.py`
  - Core orchestration function renamed to `run_genre_organizer_sync`
  - Test suite renamed to `tests/test_cli_genre_organizer.py`
- **FR-006**: System MUST update all documentation, including `README.md`, CLI help docstrings, and quickstart/examples, replacing references to `genre-playlist` with `organize` and `genre-organizer`.
- **FR-007**: Error messaging and CLI output MUST adhere to Principle IX by offering concise, clear summaries and immediate guidance without requiring source-code inspection.

### Key Entities *(include if feature involves data)*

- **Genre Organizer Command**: The primary user-facing CLI command (`organize`) and alias (`genre-organizer`) used to categorize library tracks and sync genre playlists.
- **Destination Folder**: The target folder within the streaming service where genre playlists are grouped (default: `Genres`).
- **Genre Cache**: The persistent SQLite database (`data/genre_cache.db`) storing track genre mappings to optimize execution speed and reduce AI token consumption.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can execute genre playlist synchronization using either `organize` or `genre-organizer` with 100% functional parity and zero regression in classification or playlist updates.
- **SC-002**: Command invocation typing overhead is reduced from 14 characters (`genre-playlist`) to 8 characters (`organize`), matching the single-word pattern of `radio` and `recommend`.
- **SC-003**: Invocations of the retired `genre-playlist` command return immediate, actionable guidance with exit code 1 in under 1 second guiding users to `organize`.
- **SC-004**: 100% of references in `README.md` and CLI `--help` menus are updated to document `organize` and `genre-organizer`.
- **SC-005**: 100% of automated tests in the renamed test suite pass with zero failures or deprecation warnings.

## Assumptions

- The underlying categorization algorithm, Gemini prompt strategy, SQLite cache schema, and Tidal playlist synchronization logic remain identical to existing functionality.
- The default SQLite cache location remains `data/genre_cache.db` to prevent cache invalidation or re-querying costs for existing users.
- Development environment uses Python 3.12+ and `uv` as defined in the project constitution.
