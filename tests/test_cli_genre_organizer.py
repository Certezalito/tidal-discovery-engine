"""CLI integration tests for organize command, genre-organizer alias, legacy stub, and --refresh-genres flag."""

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
    mock_summary.playlists_wiped = 0
    mock_summary.tracks_added = 20
    mock_summary.tracks_removed = 0
    mock_summary.folder_url = "https://tidal.com/browse/folder/mock-folder-id"
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
    assert "Folder URL:             https://tidal.com/browse/folder/mock-folder-id" in result.output
    assert "View folder 'My Genres' here: https://tidal.com/browse/folder/mock-folder-id" in result.output

    mock_sync.assert_called_once_with(
        mock_session,
        "My Genres",
        min_genre_size=3,
        db_path="test.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
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
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_refresh_genres(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--refresh-genres"])

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=True,
        wipe_folder=False,
        wipe_only=False,
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
            ["genre-organizer", "--folder", "Alias Folder", "--min-genre-size", "5", "--refresh-genres"],
        )

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Alias Folder",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=True,
        wipe_folder=False,
        wipe_only=False,
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


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_without_folder_url(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_summary = _make_mock_summary()
    mock_summary.folder_url = None
    mock_sync.return_value = mock_summary

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize"])

    assert result.exit_code == 0
    assert "Folder URL:" not in result.output
    assert "View folder" not in result.output


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_wipe_folder_with_yes(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_summary = _make_mock_summary()
    mock_summary.playlists_wiped = 4
    mock_sync.return_value = mock_summary

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--wipe-folder", "--yes"])

    assert result.exit_code == 0
    assert "Playlists Wiped:        4" in result.output
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=True,
        wipe_only=False,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_wipe_alias_and_short_yes(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_summary = _make_mock_summary()
    mock_summary.playlists_wiped = 2
    mock_sync.return_value = mock_summary

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--wipe", "-y"])

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=True,
        wipe_only=False,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_wipe_only(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_summary = _make_mock_summary()
    mock_summary.playlists_wiped = 3
    mock_sync.return_value = mock_summary

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--wipe-only", "--yes"])

    assert result.exit_code == 0
    assert "Playlists Wiped:        3" in result.output
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=True,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_wipe_interactive_confirm_yes(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_summary = _make_mock_summary()
    mock_summary.playlists_wiped = 2
    mock_sync.return_value = mock_summary

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--wipe-folder"], input="y\n")

    assert result.exit_code == 0
    assert "Are you sure you want to delete all playlists in folder 'Genres'?" in result.output
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=True,
        wipe_only=False,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_wipe_interactive_confirm_abort(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--wipe-folder"], input="n\n")

    assert result.exit_code != 0  # click.confirm aborts with non-zero exit code
    assert "Aborted" in result.output
    mock_sync.assert_not_called()

