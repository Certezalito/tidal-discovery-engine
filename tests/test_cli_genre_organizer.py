"""CLI integration tests for organize command, genre-organizer alias, legacy stub, and --refresh-genres flag."""

import logging
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


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_flex_flag(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--flex"])

    assert result.exit_code == 0
    assert "Connecting to Gemini via Flex tier (50% cost savings)." in result.output
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
        flex=True,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_no_flex_flag(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--no-flex"])

    assert result.exit_code == 0
    assert "Connecting to Gemini via Flex tier" not in result.output
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
        flex=False,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_genre_organizer_alias_flex_flag(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["genre-organizer", "--flex"])

    assert result.exit_code == 0
    assert "Connecting to Gemini via Flex tier (50% cost savings)." in result.output
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
        flex=True,
    )


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_keyboard_interrupt(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.side_effect = KeyboardInterrupt()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--flex"])

    assert result.exit_code == 130
    assert "Operation canceled by user." in result.output


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_flex_confirmation_in_summary_and_logs(mock_sync, mock_get_session, caplog):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with caplog.at_level(logging.INFO):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            result = runner.invoke(cli, ["organize", "--flex"])

    assert result.exit_code == 0
    assert "Gemini Service Tier:    Flex mode utilized (50% token cost reduction)" in result.output
    assert "Gemini flex mode utilized for batch genre classification." in caplog.text


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_flex_fallback_in_summary_and_logs(mock_sync, mock_get_session, caplog):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_summary = _make_mock_summary()
    mock_summary.fallback_triggered = True
    mock_summary.service_tier = "standard"
    mock_sync.return_value = mock_summary

    with caplog.at_level(logging.INFO):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            result = runner.invoke(cli, ["organize", "--flex"])

    assert result.exit_code == 0
    assert "Gemini Service Tier:    Standard tier utilized (fallback from flex)" in result.output
    assert "Flex mode utilized" not in result.output
    assert "Gemini standard tier utilized for batch genre classification (fallback from flex)." in caplog.text
    assert "Gemini flex mode utilized for batch genre classification." not in caplog.text


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_organizer_sync")
def test_organize_cli_flex_fallback_standard_flag(mock_sync, mock_get_session):
    runner = CliRunner()
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_sync.return_value = _make_mock_summary()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(cli, ["organize", "--flex", "--flex-fallback-standard"])

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
        flex=True,
        flex_fallback_standard=True,
    )

    mock_sync.reset_mock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result_no = runner.invoke(cli, ["organize", "--flex", "--no-flex-fallback-standard"])

    assert result_no.exit_code == 0
    mock_sync.assert_called_once_with(
        mock_session,
        "Genres",
        min_genre_size=5,
        db_path="data/genre_cache.db",
        refresh_genres=False,
        wipe_folder=False,
        wipe_only=False,
        flex=True,
        flex_fallback_standard=False,
    )


@patch("src.services.gemini_service.classify_tracks_genres")
@patch("src.services.tidal_service.create_playlist_in_folder")
@patch("src.services.tidal_service.get_playlists_in_folder", return_value=[])
@patch("src.services.tidal_service.get_or_create_folder")
@patch("src.services.tidal_service.fetch_all_favorite_tracks")
def test_genre_organizer_sticky_fallback_across_batches(
    mock_get_tracks,
    mock_get_folder,
    mock_get_playlists,
    mock_create_playlist,
    mock_classify,
    tmp_path,
):
    from src.services.genre_organizer_service import run_genre_organizer_sync
    mock_session = MagicMock()
    mock_get_folder.return_value = MagicMock(id="f1")

    # 100 tracks to create multiple batches (BATCH_SIZE is 50 in genre_organizer_service)
    class FakeTrack:
        def __init__(self, i):
            self.id = f"t{i}"
            self.name = f"Track {i}"
            self.title = f"Track {i}"
            self.isrc = f"ISRC{i}"
            self.artist = type("FakeArtist", (), {"name": f"Artist {i}"})()

    tracks = [FakeTrack(i) for i in range(100)]
    mock_get_tracks.return_value = (tracks, 2)

    calls = []

    def side_effect_classify(api_key, batch_inputs, flex=None, flex_fallback_standard=None, on_fallback=None, **kwargs):
        calls.append(flex)
        if on_fallback and flex:
            on_fallback()
        return [
            {"artist": t["artist"], "title": t["title"], "isrc": t.get("isrc"), "primary_genre": "Rock", "sub_genres": []}
            for t in batch_inputs
        ]

    mock_classify.side_effect = side_effect_classify

    db_path = str(tmp_path / "test_genre_cache.db")
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        summary = run_genre_organizer_sync(
            mock_session,
            "Genres",
            db_path=db_path,
            flex=True,
            flex_fallback_standard=True,
        )

    assert summary.library_tracks_scanned == 100
    assert mock_classify.call_count == 2
    assert calls == [True, False]
    assert mock_classify.call_args_list[0].kwargs.get("flex_fallback_standard") is True
    assert mock_classify.call_args_list[1].kwargs.get("flex_fallback_standard") is True
    assert summary.fallback_triggered is True
    assert summary.service_tier == "standard"
