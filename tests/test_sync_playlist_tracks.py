import unittest
from unittest.mock import MagicMock, patch
from src.services.tidal_service import sync_playlist_tracks

class TestSyncPlaylistTracks(unittest.TestCase):
    @patch('src.services.tidal_service.tidalapi.playlist.UserPlaylist')
    def test_sync_playlist_tracks_success(self, mock_playlist_cls):
        mock_playlist = MagicMock()
        mock_playlist_cls.return_value = mock_playlist
        session = MagicMock()
        
        result = sync_playlist_tracks(session, "pl_123", ["track1"], ["track2"])
        self.assertTrue(result)
        mock_playlist.delete_by_id.assert_called_once_with(["track2"])
        mock_playlist.add.assert_called_once_with(["track1"])

    @patch('src.services.tidal_service.tidalapi.playlist.UserPlaylist')
    def test_sync_playlist_tracks_failure(self, mock_playlist_cls):
        mock_playlist = MagicMock()
        mock_playlist_cls.return_value = mock_playlist
        session = MagicMock()
        
        # Simulate network error
        mock_playlist.add.side_effect = Exception("404 Not Found")
        
        result = sync_playlist_tracks(session, "pl_123", ["track1"], [])
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
