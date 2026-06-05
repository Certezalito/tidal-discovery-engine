import unittest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from src.cli.main import cli
from src.services.gemini_service import GeminiModelUnavailableError
from src.lib.logging import EXCLUDE_FAVORITES_SHORTFALL

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
    
    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.get_or_create_folder')
    @patch('src.services.tidal_service.create_playlist_in_folder')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.tidal_service.search_for_track')
    def test_main_with_folder(self, mock_search, mock_similar, mock_get_network, mock_random, mock_create_playlist, mock_create_in_folder, mock_get_folder, mock_setup_logging, mock_get_session):
        # Setup mocks
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        
        # Mock seed and similar tracks
        mock_track = MagicMock()
        mock_track.name = "Track"
        mock_track.artist.name = "Artist"
        mock_random.return_value = [mock_track]
        
        mock_sim_track = MagicMock()
        mock_similar.return_value = [mock_sim_track]
        
        mock_tidal_track = MagicMock()
        mock_search.return_value = mock_tidal_track
        
        mock_folder = MagicMock()
        mock_folder.id = "folder-123"
        mock_get_folder.return_value = mock_folder
        
        # Invoke CLI with --folder
        result = self.runner.invoke(cli, ['recommend', '--playlist-name', 'Test Playlist', '--folder', 'My Custom Folder'])
        
        # Assert
        # If --folder is not supported, this will be 2
        self.assertEqual(result.exit_code, 0)
        
        # Logic verification
        mock_get_folder.assert_called_with(mock_get_session.return_value, 'My Custom Folder')
        
        # We mocked create_playlist, so it won't call create_playlist_in_folder internally.
        # We verify create_playlist is called with folder_id
        args, kwargs = mock_create_playlist.call_args
        self.assertEqual(kwargs['folder_id'], 'folder-123')

    @patch('src.cli.main.setup_logging')
    def test_mode3_rejects_non_positive_num_similar_tracks(self, mock_setup_logging):
        result = self.runner.invoke(
            cli,
            [
                'recommend',
                '--playlist-name', 'Test Playlist',
                '--artist', 'Seed Artist',
                '--track', 'Seed Track',
                '--num-similar-tracks', '0',
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('--num-similar-tracks must be a positive integer', result.output)

    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    @patch('src.services.gemini_service.get_recommendations')
    def test_mode3_falls_back_to_lastfm_when_model_unavailable(
        self,
        mock_get_recommendations,
        mock_resolve_seed,
        mock_get_network,
        mock_get_similar,
        mock_search,
        mock_create_playlist,
        mock_setup_logging,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed_track = MagicMock()
        seed_track.artist.name = 'Seed Artist'
        seed_track.title = 'Seed Track'
        mock_resolve_seed.return_value = (seed_track, 'exact')

        mock_get_recommendations.side_effect = GeminiModelUnavailableError('model unavailable')

        sim_track = MagicMock()
        sim_track.artist.name = 'Similar Artist'
        sim_track.title = 'Similar Track'
        mock_get_similar.return_value = [sim_track]

        mock_tidal_track = MagicMock()
        mock_tidal_track.artist.name = 'Similar Artist'
        mock_tidal_track.name = 'Similar Track'
        mock_search.return_value = mock_tidal_track

        playlist = MagicMock()
        playlist.id = 'playlist-1'
        playlist.name = 'Test Playlist'
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            cli,
            [
                'recommend',
                '--gemini',
                '--playlist-name', 'Test Playlist',
                '--artist', 'Seed Artist',
                '--track', 'Seed Track',
            ],
            env={'GEMINI_API_KEY': 'test-key'},
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_get_similar.called)

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.tidal_service.build_favorites_snapshot')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.cli.main.log_cli_warning')
    def test_gemini_failure_with_exclude_favorites_not_misattributed(
        self,
        mock_log_warning,
        mock_create_playlist,
        mock_get_recommendations,
        mock_build_snapshot,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed = MagicMock()
        seed.artist.name = 'Seed Artist'
        seed.name = 'Seed Title'
        mock_get_random.return_value = [seed]

        mock_build_snapshot.return_value = {
            'identity_keys': set(),
            'total_favorites': 0,
            'pages_loaded': 1,
            'load_complete': True,
        }
        mock_get_recommendations.side_effect = ValueError('Gemini request failed. model=primary')

        result = self.runner.invoke(
            cli,
            [
                'recommend','--gemini', '--exclude-favorites', '--playlist-name', 'Test Playlist'],
            env={'GEMINI_API_KEY': 'test-key'},
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Gemini request failed', result.output)
        self.assertFalse(mock_create_playlist.called)
        self.assertFalse(any(call.args[0] == EXCLUDE_FAVORITES_SHORTFALL for call in mock_log_warning.call_args_list))

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.tidal_service.build_favorites_snapshot')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.get_track_by_isrc')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.cli.main.log_cli_warning')
    def test_gemini_recovery_results_filter_and_create_playlist(
        self,
        mock_log_warning,
        mock_create_playlist,
        mock_search,
        mock_get_track_by_isrc,
        mock_get_recommendations,
        mock_build_snapshot,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed = MagicMock()
        seed.artist.name = 'Seed Artist'
        seed.name = 'Seed Title'
        mock_get_random.return_value = [seed]

        mock_build_snapshot.return_value = {
            'identity_keys': {'isrc:FAV001'},
            'total_favorites': 1,
            'pages_loaded': 1,
            'load_complete': True,
        }

        mock_get_recommendations.return_value = [
            {'artist': 'Artist A', 'title': 'Track A', 'isrc': 'FAV001'},
            {'artist': 'Artist B', 'title': 'Track B', 'isrc': 'NEW001'},
        ]
        mock_get_track_by_isrc.side_effect = [None, None]

        favorite_track = MagicMock()
        favorite_track.artist.name = 'Artist A'
        favorite_track.name = 'Track A'
        favorite_track.isrc = 'FAV001'
        favorite_track.id = 'fav-track'

        new_track = MagicMock()
        new_track.artist.name = 'Artist B'
        new_track.name = 'Track B'
        new_track.isrc = 'NEW001'
        new_track.id = 'new-track'

        mock_search.side_effect = [favorite_track, new_track]

        playlist = MagicMock()
        playlist.id = 'playlist-1'
        playlist.name = 'Test Playlist'
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            cli,
            [
                'recommend',
                '--gemini',
                '--exclude-favorites',
                '--playlist-name', 'Test Playlist',
                '--num-tidal-tracks', '1',
                '--num-similar-tracks', '1',
            ],
            env={'GEMINI_API_KEY': 'test-key'},
        )

        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_create_playlist.call_args
        self.assertEqual(len(kwargs['tracks']), 1)
        self.assertEqual(kwargs['tracks'][0].id, 'new-track')
        self.assertFalse(any(call.args[0] == EXCLUDE_FAVORITES_SHORTFALL for call in mock_log_warning.call_args_list))

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.create_playlist')
    def test_non_gemini_mode_does_not_call_gemini_service(
        self,
        mock_create_playlist,
        mock_search,
        mock_similar,
        mock_get_random,
        mock_get_recommendations,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed = MagicMock()
        seed.artist.name = 'Seed Artist'
        seed.name = 'Seed Track'
        mock_get_random.return_value = [seed]

        similar_track = MagicMock()
        similar_track.artist.name = 'Artist B'
        similar_track.title = 'Track B'
        mock_similar.return_value = [similar_track]

        resolved = MagicMock()
        resolved.artist.name = 'Artist B'
        resolved.name = 'Track B'
        resolved.id = '1'
        mock_search.return_value = resolved

        playlist = MagicMock()
        playlist.id = 'playlist-1'
        playlist.name = 'Test Playlist'
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(cli, ['recommend', '--playlist-name', 'Test Playlist'])

        self.assertEqual(result.exit_code, 0)
        mock_get_recommendations.assert_not_called()



    @patch('src.cli.main.setup_logging')
    @patch('src.cli.main.run_genre_playlist_sync')
    @patch('src.services.tidal_service.get_session')
    def test_genre_playlist_folder_precedence(self, mock_get_session, mock_run_sync, mock_setup_logging):
        mock_get_session.return_value = MagicMock()
        mock_summary = MagicMock()
        mock_summary.library_tracks_scanned = 0
        mock_run_sync.return_value = mock_summary

        # CLI argument provided
        result = self.runner.invoke(
            cli,
            ['genre-playlist', '--folder', 'My Custom Genres'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result.exit_code, 0)
        mock_run_sync.assert_called_with(mock_get_session.return_value, 'My Custom Genres')
        
        # CLI argument absent (defaults to "Genres")
        result2 = self.runner.invoke(
            cli,
            ['genre-playlist'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result2.exit_code, 0)
        mock_run_sync.assert_called_with(mock_get_session.return_value, 'Genres')

    @patch('src.cli.main.setup_logging')
    @patch('src.cli.main.run_genre_playlist_sync')
    @patch('src.services.tidal_service.get_session')
    def test_genre_playlist_rerun_sync_metrics(self, mock_get_session, mock_run_sync, mock_setup_logging):
        """
        T018 [US2] Add CLI rerun test verifying no duplicate playlists and synced membership
        """
        mock_get_session.return_value = MagicMock()
        mock_summary = MagicMock()
        mock_summary.library_tracks_scanned = 10
        mock_summary.playlists_created = 0
        mock_summary.playlists_updated = 1
        mock_summary.tracks_added = 2
        mock_summary.tracks_removed = 1
        mock_summary.unknown_tracks = 0
        mock_summary.classified_tracks = 10
        mock_run_sync.return_value = mock_summary

        result = self.runner.invoke(
            cli,
            ['genre-playlist'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(mock_run_sync.call_count, 1)

    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.fetch_all_favorite_tracks')
    @patch('src.services.tidal_service.get_session')
    def test_genre_playlist_empty_library(self, mock_get_session, mock_fetch, mock_setup_logging):
        """
        T024 [P] Add edge-case test coverage for empty libraries
        """
        mock_get_session.return_value = MagicMock()
        mock_fetch.return_value = ([], 0)

        result = self.runner.invoke(
            cli,
            ['genre-playlist', '--folder', 'My Custom Genres'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result.exit_code, 0)
        
if __name__ == '__main__':
    unittest.cli()
