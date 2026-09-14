import unittest
from unittest.mock import MagicMock, patch
from src.services.tidal_service import sync_playlist_tracks

class TestSyncPlaylistTracks(unittest.TestCase):
    @patch('src.services.tidal_service.add_tracks_to_playlist')
    @patch('src.services.tidal_service.remove_tracks_from_playlist')
    def test_sync_playlist_tracks_success(self, mock_remove, mock_add):
        session = MagicMock()
        
        result = sync_playlist_tracks(session, "pl_123", ["track1"], ["track2"])
        self.assertTrue(result)
        mock_remove.assert_called_once_with(session, "pl_123", ["track2"])
        mock_add.assert_called_once_with(session, "pl_123", ["track1"])

    @patch('src.services.tidal_service.add_tracks_to_playlist')
    @patch('src.services.tidal_service.remove_tracks_from_playlist')
    def test_sync_playlist_tracks_failure(self, mock_remove, mock_add):
        session = MagicMock()
        mock_add.side_effect = Exception("API error")
        
        result = sync_playlist_tracks(session, "pl_123", ["track1"], [])
        self.assertFalse(result)

    @patch('src.services.tidal_service.add_tracks_to_playlist')
    @patch('src.services.tidal_service.remove_tracks_from_playlist')
    def test_sync_playlist_tracks_only_remove(self, mock_remove, mock_add):
        session = MagicMock()
        
        result = sync_playlist_tracks(session, "pl_123", [], ["track2"])
        self.assertTrue(result)
        mock_remove.assert_called_once_with(session, "pl_123", ["track2"])
        mock_add.assert_not_called()

if __name__ == '__main__':
    unittest.main()
