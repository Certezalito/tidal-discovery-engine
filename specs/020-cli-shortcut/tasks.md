# Tasks: CLI Shortcut Entrypoint

**Feature Branch**: `020-cli-shortcut`  
**Date**: 2026-09-21  
**Spec**: [spec.md](spec.md)  
**Plan**: [plan.md](plan.md)  

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish package structure and build configuration for console script distribution

- [X] T001 Create explicit package marker in `src/__init__.py` to enable clean package discovery and `src.*` module resolution
- [X] T002 Configure `[build-system]` and `[tool.setuptools.packages.find]` in `pyproject.toml` with `where = ["."]`, `include = ["src*"]`, and `namespaces = true`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Register binary shortcuts in packaging metadata and install into environment

**⚠️ CRITICAL**: Must complete before user story verification can proceed

- [X] T003 Configure `[project.scripts]` in `pyproject.toml` registering `tde = "src.cli.main:cli"` and `tidal-discovery-engine = "src.cli.main:cli"`
- [X] T004 Install package in editable mode via `uv pip install -e .` to generate console script executables in `.venv/bin/`

**Checkpoint**: Foundation ready — `tde` and `tidal-discovery-engine` binaries exist in the virtual environment.

---

## Phase 3: User Story 1 - Direct CLI Invocation via Shortcut (Priority: P1) 🎯 MVP

**Goal**: Allow users to run top-level CLI commands and access global help using `tde` and `tidal-discovery-engine`.

**Independent Test**: Run `uv run tde --help` and `uv run tidal-discovery-engine --help`; confirm exit code `0` and display of the top-level command list.

### Tests for User Story 1

- [X] T005 [US1] Implement unit tests for top-level shortcut execution (`tde --help`, `tidal-discovery-engine --help`, and argument-less invocation) in `tests/unit/test_cli_entrypoint.py`

### Implementation for User Story 1

- [X] T006 [US1] Validate top-level entrypoint routing and help output against root Click group `cli` in `src/cli/main.py`

**Checkpoint**: User Story 1 functional and independently testable — primary shortcut and alias display global help cleanly.

---

## Phase 4: User Story 2 - Full Feature & Argument Parity with Direct Invocation (Priority: P2)

**Goal**: Guarantee complete option, flag, validation, and exit code equivalence between shortcut commands and direct module invocation across all subcommands (`recommend`, `radio`, `organize`).

**Independent Test**: Execute `uv run tde recommend --help`, `uv run tde radio --help`, and `uv run tde organize --help`; verify all flags match direct execution and syntax errors exit with code `2`.

### Tests for User Story 2

- [X] T007 [US2] Add test cases to `tests/unit/test_cli_entrypoint.py` verifying subcommand routing and flag parity for `recommend`, `radio`, and `organize` (including alias `genre-organizer`)
- [X] T008 [US2] Add test cases to `tests/unit/test_cli_entrypoint.py` verifying error handling parity and exit code `2` on invalid CLI options

### Implementation for User Story 2

- [X] T009 [US2] Verify Click context passing and exit code preservation across all subcommands in `src/cli/main.py`

**Checkpoint**: User Stories 1 & 2 fully operational with complete subcommand and argument parity.

---

## Phase 5: User Story 3 - Updated User Documentation & Backward Compatibility (Priority: P3)

**Goal**: Update documentation to guide users on using `uv run tde` as the primary syntax while keeping direct module execution (`python -m src.cli.main`) fully functional.

**Independent Test**: Inspect `README.md` to verify all command examples demonstrate `uv run tde`; run `uv run python -m src.cli.main --help` to confirm legacy compatibility without regressions.

### Tests for User Story 3

- [X] T010 [P] [US3] Add automated test cases in `tests/unit/test_cli_entrypoint.py` verifying that legacy direct module execution (`python -m src.cli.main`) remains operational with identical output
- [X] T011 [P] [US3] Update setup instructions and all command examples in `README.md` to showcase `uv run tde <command>`, document bare `tde` for activated environments, and note legacy invocation support

**Checkpoint**: User Story 3 complete — documentation and backward compatibility verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ensure zero regressions across entire project and validate quickstart guide

- [X] T012 Run full test suite via `uv run pytest` to ensure zero regressions across existing unit and integration tests
- [X] T013 Execute end-to-end verification scenarios per `specs/020-cli-shortcut/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User Story 1 (P1): Depends on Phase 2.
  - User Story 2 (P2): Depends on User Story 1.
  - User Story 3 (P3): Depends on User Story 2.
- **Polish (Phase 6)**: Depends on all user stories being complete.

### Parallel Opportunities

- **Phase 5 (User Story 3)**:
  - `T010` (test file `tests/unit/test_cli_entrypoint.py`) and `T011` (documentation `README.md`) touch different files and can execute in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`src/__init__.py`, `pyproject.toml` build-system)
2. Complete Phase 2: Foundational (`[project.scripts]`, `uv pip install -e .`)
3. Complete Phase 3: User Story 1 (`tests/unit/test_cli_entrypoint.py`, entrypoint verification)
4. **STOP and VALIDATE**: Test `uv run tde --help` independently (Delivers working MVP!)

### Incremental Delivery

1. Setup + Foundational → Packaging infrastructure ready
2. User Story 1 → Top-level shortcut working (MVP)
3. User Story 2 → Full subcommand & flag parity verified
4. User Story 3 → Documentation modernized & legacy compatibility guaranteed
5. Polish → Full test suite passing and quickstart validation complete
