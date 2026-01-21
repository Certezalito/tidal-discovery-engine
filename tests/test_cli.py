import unittest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from src.cli.main import main

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


if __name__ == '__main__':
    unittest.main()
