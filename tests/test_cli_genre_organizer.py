"""CLI integration tests for organize command, genre-organizer alias, and legacy stub."""

import os
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from src.cli.main import cli


def _make_mock_summary():
    mock_summary = MagicMock()
    mock_summary.library_tracks_scanned = 100
    mock_summary.cache_hits = 90
    mock_summary.cache_misses = 10
    mock_summary.classified_tracks = 95
    mock_summary.unknown_tracks = 5
    mock_summary.playlists_created = 3
    mock_summary.playlists_updated = 2
    mock_summary.playlists_deleted = 1
    mock_summary.duplicate_playlists_deleted = 0
    mock_summary.tracks_added = 20
    mock_summary.tracks_removed = 0
    return mock_summary


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_options(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(
            cli,
            ["organize", "--folder", "My Genres", "--min-genre-size", "3", "--db-path", "test.db"],
        )

    assert result.exit_code == 0
    assert "Database Cache Hits:    90" in result.output
    assert "Token Cost Reduction:   90.0%" in result.output

    mock_sync.assert_called_once_with(
        mock_session,
        "My Genres",
        min_genre_size=3,
        db_path="test.db",
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_defaults(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize"])

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=10,
        db_path="data/genre_cache.db",
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_genre_organizer_alias(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(
            cli,
            ["genre-organizer", "--folder", "Alias Folder", "--min-genre-size", "5"],
        )

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Alias Folder",
        min_genre_size=5,
        db_path="data/genre_cache.db",
    )


def test_legacy_genre_playlist_fails_with_guidance():
    runner = CliRunner()
    result = runner.invoke(cli, ["genre-playlist"])

    assert result.exit_code == 1
    assert "Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer')." in result.output


def test_legacy_genre_playlist_with_arguments_fails_with_guidance():
    runner = CliRunner()
    result = runner.invoke(cli, ["genre-playlist", "--folder", "Old Genres", "--min-genre-size", "5"])

    assert result.exit_code == 1
    assert "Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer')." in result.output


def test_cli_help_lists_organize_and_hides_genre_playlist():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "organize" in result.output
    assert "genre-organizer" in result.output
    assert "genre-playlist" not in result.output
