import unittest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from src.cli.main import main
from src.services.gemini_service import GeminiModelUnavailableError

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
        result = self.runner.invoke(main, ['--playlist-name', 'Test Playlist', '--folder', 'My Custom Folder'])
        
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
            main,
            [
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
            main,
            [
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
    @patch('src.cli.main.setup_logging')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.create_playlist')
    def test_mode3_gemini_zero_insertions_fails(
        self,
        mock_create_playlist,
        mock_search,
        mock_get_recommendations,
        mock_resolve_seed,
        mock_get_network,
        mock_setup_logging,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed_track = MagicMock()
        seed_track.artist.name = 'Seed Artist'
        seed_track.name = 'Seed Track'
        mock_resolve_seed.return_value = (seed_track, 'exact')

        mock_get_recommendations.return_value = [
            {'artist': 'Missing Artist', 'title': 'Missing Track', 'isrc': None}
        ]
        mock_search.return_value = None

        result = self.runner.invoke(
            main,
            [
                '--gemini',
                '--playlist-name', 'Test Playlist',
                '--artist', 'Seed Artist',
                '--track', 'Seed Track',
            ],
            env={'GEMINI_API_KEY': 'test-key'},
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('No tracks could be inserted into the playlist', result.output)
        self.assertFalse(mock_create_playlist.called)


if __name__ == '__main__':
    unittest.main()
