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

    @patch('src.services.tidal_service.get_playlist_tracks')
    def test_sync_playlist_tracks_surgical_uuid_removal_preserves_kept_copy(self, mock_get_tracks):
        """Passing a surplus occurrence's item_uuid removes only that slot via v2 API."""
        session = MagicMock()
        session.config.api_v2_location = "https://api.tidal.com/v2/"
        surplus_uuid = "00000000-0000-0000-0000-000000000002"

        result = sync_playlist_tracks(session, "pl_123", [], [surplus_uuid])
        self.assertTrue(result)
        # Should NOT re-fetch playlist tracks to resolve a valid item_uuid
        mock_get_tracks.assert_not_called()
        session.request.request.assert_called_once_with(
            "PUT",
            "playlists/pl_123/items/remove",
            params={"itemUuids": surplus_uuid},
            base_url="https://api.tidal.com/v2/",
        )

    @patch('src.services.tidal_service.add_tracks_to_playlist')
    @patch('src.services.tidal_service.remove_tracks_from_playlist')
    def test_sync_playlist_tracks_removes_before_adding(self, mock_remove, mock_add):
        """Removal must execute before addition so non-UUID duplicate fallback restores 1 copy."""
        session = MagicMock()
        call_order = []
        mock_remove.side_effect = lambda *args, **kwargs: call_order.append("remove") or True
        mock_add.side_effect = lambda *args, **kwargs: call_order.append("add") or True

        result = sync_playlist_tracks(session, "pl_123", ["101"], ["101"])
        self.assertTrue(result)
        self.assertEqual(call_order, ["remove", "add"])

if __name__ == '__main__':
    unittest.main()
