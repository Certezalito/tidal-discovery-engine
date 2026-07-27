"""CLI integration tests for genre-playlist command options."""

import os
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from src.cli.main import cli


@patch("src.cli.main.tidal_service.get_session")
@patch("src.cli.main.run_genre_playlist_sync")
def test_genre_playlist_cli_options(mock_sync, mock_get_session):
    runner = CliRunner()
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    
    mock_summary = MagicMock()
    mock_summary.library_tracks_scanned = 100
    mock_summary.cache_hits = 90
    mock_summary.cache_misses = 10
    mock_summary.classified_tracks = 95
    mock_summary.unknown_tracks = 5
    mock_summary.playlists_created = 3
    mock_summary.playlists_updated = 2
    mock_summary.playlists_deleted = 1
    mock_summary.tracks_added = 20
    mock_summary.tracks_removed = 0
    mock_sync.return_value = mock_summary

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        result = runner.invoke(
            cli,
            ["genre-playlist", "--folder", "My Genres", "--min-genre-size", "3", "--db-path", "test.db"],
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
