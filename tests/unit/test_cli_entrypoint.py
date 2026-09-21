"""Unit and integration tests for CLI shortcut entrypoints.

This module validates that the console script entrypoints (`tde` and
`tidal-discovery-engine`) configured in `pyproject.toml` provide complete
functional and argument parity with the direct module execution
(`python -m src.cli.main`).

Testing scope includes:
- User Story 1 (P1): Top-level shortcut execution (`tde`, `tidal-discovery-engine`).
- User Story 2 (P2): Subcommand routing and parameter parity (`recommend`, `radio`, `organize`).
- User Story 3 (P3): Backward compatibility with legacy direct module execution.
"""

import os
import subprocess
import sys
from pathlib import Path
import pytest
from click.testing import CliRunner

from src.cli.main import cli

# Determine the project root and virtualenv executable paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_BIN = PROJECT_ROOT / ".venv" / "bin"
TDE_BIN = VENV_BIN / "tde"
TIDAL_DISCOVERY_ENGINE_BIN = VENV_BIN / "tidal-discovery-engine"


# ============================================================================
# User Story 1 (P1): Top-Level Shortcut Execution
# ============================================================================


def test_tde_binary_exists():
    """Verify that `tde` executable binary was generated in virtual environment."""
    assert TDE_BIN.is_file(), f"Expected binary at {TDE_BIN} not found. Run `uv pip install -e .`"
    assert os.access(TDE_BIN, os.X_OK), f"Binary at {TDE_BIN} is not executable."


def test_tidal_discovery_engine_binary_exists():
    """Verify that `tidal-discovery-engine` executable binary exists in virtual environment."""
    assert (
        TIDAL_DISCOVERY_ENGINE_BIN.is_file()
    ), f"Expected binary at {TIDAL_DISCOVERY_ENGINE_BIN} not found. Run `uv pip install -e .`"
    assert os.access(
        TIDAL_DISCOVERY_ENGINE_BIN, os.X_OK
    ), f"Binary at {TIDAL_DISCOVERY_ENGINE_BIN} is not executable."


def test_tde_help_output_and_exit_code():
    """Verify that invoking `tde --help` executes cleanly with exit code 0."""
    result = subprocess.run(
        [str(TDE_BIN), "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}: {result.stderr}"
    assert "Tidal Discovery Engine CLI" in result.stdout
    assert "Commands:" in result.stdout
    assert "recommend" in result.stdout
    assert "radio" in result.stdout
    assert "organize" in result.stdout


def test_tidal_discovery_engine_alias_parity():
    """Verify that `tidal-discovery-engine --help` matches `tde --help` output."""
    tde_res = subprocess.run(
        [str(TDE_BIN), "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    alias_res = subprocess.run(
        [str(TIDAL_DISCOVERY_ENGINE_BIN), "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert alias_res.returncode == 0
    # Normalize the executable name in the usage line to ensure command parity
    normalized_tde = tde_res.stdout.replace("Usage: tde", "Usage: PROG")
    normalized_alias = alias_res.stdout.replace("Usage: tidal-discovery-engine", "Usage: PROG")
    assert normalized_tde == normalized_alias


def test_tde_argumentless_invocation():
    """Verify invoking `tde` with no arguments prints usage and exits with code 2 (matching direct module execution)."""
    result = subprocess.run(
        [str(TDE_BIN)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    direct_res = subprocess.run(
        [sys.executable, "-m", "src.cli.main"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == direct_res.returncode == 2
    assert "Usage: tde [OPTIONS] COMMAND [ARGS]..." in result.stderr


def test_click_root_group_in_process():
    """Verify Click root group executes cleanly in-process via Click CliRunner."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Tidal Discovery Engine CLI" in result.output
    assert "recommend" in result.output
    assert "radio" in result.output
    assert "organize" in result.output


# ============================================================================
# User Story 2 (P2): Subcommand Routing & Parity
# ============================================================================


@pytest.mark.parametrize(
    "subcommand",
    ["recommend", "radio", "organize", "genre-organizer"],
)
def test_subcommand_help_parity(subcommand):
    """Verify all subcommands display identical help output through the shortcut."""
    # Direct module invocation via python
    direct_res = subprocess.run(
        [sys.executable, "-m", "src.cli.main", subcommand, "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert direct_res.returncode == 0, f"Direct execution failed: {direct_res.stderr}"

    # Shortcut invocation via tde
    shortcut_res = subprocess.run(
        [str(TDE_BIN), subcommand, "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert shortcut_res.returncode == 0, f"Shortcut execution failed: {shortcut_res.stderr}"

    # Normalize program prefixes (e.g., `src.cli.main` vs `tde`)
    normalized_direct = direct_res.stdout.replace(
        f"Usage: python -m src.cli.main {subcommand}", "Usage: PROG"
    ).replace(f"Usage: main.py {subcommand}", "Usage: PROG")
    normalized_shortcut = shortcut_res.stdout.replace(
        f"Usage: tde {subcommand}", "Usage: PROG"
    )

    assert (
        normalized_shortcut == normalized_direct
    ), f"Help parity mismatch for subcommand '{subcommand}'"


def test_invalid_option_error_exit_code():
    """Verify invalid options exit with code 2 and standard error messaging."""
    result = subprocess.run(
        [str(TDE_BIN), "--nonexistent-flag"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 2
    assert "No such option: --nonexistent-flag" in result.stderr


def test_invalid_subcommand_error_exit_code():
    """Verify invalid subcommand names exit with code 2 and helpful command suggestions."""
    result = subprocess.run(
        [str(TDE_BIN), "unknown-subcommand"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 2
    assert "No such command 'unknown-subcommand'" in result.stderr


# ============================================================================
# User Story 3 (P3): Backward Compatibility
# ============================================================================


def test_legacy_direct_module_execution():
    """Verify that direct module execution (`python -m src.cli.main`) remains operational."""
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.main", "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
    assert "Tidal Discovery Engine CLI" in result.stdout
    assert "recommend" in result.stdout
    assert "radio" in result.stdout
    assert "organize" in result.stdout
