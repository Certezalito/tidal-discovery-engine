import unittest
from unittest.mock import MagicMock, patch
from src.services.genre_organizer_service import (
    calculate_sync_delta,
    run_genre_organizer_sync as run_genre_playlist_sync,
)


class TestGenrePlaylistService(unittest.TestCase):
    def test_calculate_sync_delta_basic(self):
        desired = ["1", "2", "3"]
        existing = ["2", "3", "4"]
        to_add, to_remove = calculate_sync_delta(desired, existing)

        self.assertEqual(to_add, ["1"])
        self.assertEqual(to_remove, ["4"])

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    @patch("src.services.tidal_service.delete_playlist")
    def test_run_genre_playlist_sync_thresholding_and_cleanup(
        self,
        mock_delete_pl,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        mock_session = MagicMock()

        t1 = MagicMock(id="t1", isrc="ISRC1", title="Song 1", artist=MagicMock(name="Art 1"))
        t2 = MagicMock(id="t2", isrc="ISRC2", title="Song 2", artist=MagicMock(name="Art 1"))
        t3 = MagicMock(id="t3", isrc="ISRC3", title="Song 3", artist=MagicMock(name="Art 1"))
        t4 = MagicMock(id="t4", isrc="ISRC4", title="Song 4", artist=MagicMock(name="Art 2"))
        t5 = MagicMock(id="t5", isrc="ISRC5", title="Song 5", artist=MagicMock(name="Art 3"))

        mock_fetch_tracks.return_value = ([t1, t2, t3, t4, t5], 1)

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst

        mock_cache_inst.get_cached_genres.return_value = (
            {
                "isrc:ISRC1": "Rock",
                "isrc:ISRC2": "Rock",
                "isrc:ISRC3": "Rock",
                "isrc:ISRC4": "Jazz",
                "isrc:ISRC5": "Pop",
            },
            [],
        )

        folder_mock = MagicMock(id="folder123")
        mock_get_folder.return_value = folder_mock

        obsolete_pl = MagicMock(id="pl_obs")
        obsolete_pl.name = "Obsolete Genre"
        mock_get_pls.return_value = [obsolete_pl]

        summary = run_genre_playlist_sync(
            mock_session,
            folder_name="Test Folder",
            min_genre_size=2,
        )

        self.assertEqual(summary.library_tracks_scanned, 5)
        self.assertEqual(summary.cache_hits, 5)
        self.assertEqual(summary.cache_misses, 0)
        self.assertEqual(summary.playlists_deleted, 1)
        self.assertEqual(summary.playlists_created, 2)

        mock_delete_pl.assert_called_once_with(mock_session, "pl_obs")

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    @patch("src.services.tidal_service.delete_playlist")
    @patch("src.services.tidal_service.sync_playlist_tracks")
    @patch("src.services.tidal_service.get_playlist_tracks")
    def test_run_genre_playlist_sync_duplicate_cleanup(
        self,
        mock_get_tracks,
        mock_sync,
        mock_delete_pl,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        mock_session = MagicMock()

        # Simulate 1 track for 'Rock'
        t1 = MagicMock(id="t1", isrc="ISRC1", title="Song 1", artist=MagicMock(name="Art 1"))
        mock_fetch_tracks.return_value = ([t1], 1)

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst
        mock_cache_inst.get_cached_genres.return_value = ({"isrc:ISRC1": "Rock"}, [])

        mock_get_folder.return_value = MagicMock(id="folder123")

        # Simulate duplicates: 3 'Rock' playlists
        pl1 = MagicMock(id="pl1")
        pl1.name = "Rock"
        import datetime
        pl1.created = datetime.datetime(2023, 1, 1) # Oldest

        pl2 = MagicMock(id="pl2")
        pl2.name = "Rock (1)"
        pl2.created = datetime.datetime(2023, 1, 2)

        pl3 = MagicMock(id="pl3")
        pl3.name = "rock (2)" # Test case insensitivity and suffix
        pl3.created = datetime.datetime(2023, 1, 3)

        mock_get_pls.return_value = [pl3, pl1, pl2] # Unordered

        mock_get_tracks.return_value = [] # Empty playlist for sync calculation

        summary = run_genre_playlist_sync(
            mock_session,
            folder_name="Test Folder",
            min_genre_size=1,
        )

        # It should delete pl2 and pl3, keep pl1
        self.assertEqual(mock_delete_pl.call_count, 2)
        
        deleted_ids = [call.args[1] for call in mock_delete_pl.call_args_list]
        self.assertIn("pl2", deleted_ids)
        self.assertIn("pl3", deleted_ids)
        self.assertNotIn("pl1", deleted_ids)
        
        # It should sync pl1
        mock_get_tracks.assert_called_once_with(mock_session, "pl1")
        self.assertEqual(summary.playlists_deleted, 2)
        self.assertEqual(summary.playlists_created, 0)
        self.assertEqual(summary.playlists_updated, 1)

    @patch("src.services.tidal_service.tidalapi.playlist.Folder")
    def test_get_playlists_in_folder_pagination(self, mock_folder_cls):
        from src.services.tidal_service import get_playlists_in_folder
        
        mock_session = MagicMock()
        
        # Simulate pagination using cursor via raw requests
        # We need to mock session.request.request().json()
        mock_request = MagicMock()
        mock_session.request = mock_request
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = {
            "items": [{"data": {"title": f"pl_{i}", "id": f"{i}"}} for i in range(50)],
            "cursor": "token1"
        }
        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = {
            "items": [{"data": {"title": f"pl_{i}", "id": f"{i}"}} for i in range(50, 100)],
            "cursor": "token2"
        }
        mock_resp3 = MagicMock()
        mock_resp3.json.return_value = {
            "items": [{"data": {"title": f"pl_{i}", "id": f"{i}"}} for i in range(100, 120)],
            "cursor": None
        }
        
        mock_request.request.side_effect = [mock_resp1, mock_resp2, mock_resp3]
        mock_request.map_json.side_effect = lambda pl_dict, parse: [MagicMock(name=d["title"]) for d in pl_dict["items"]]
        
        result = get_playlists_in_folder(mock_session, "folder_id_123")
        
        self.assertEqual(len(result), 120)
        self.assertEqual(mock_request.request.call_count, 3)

if __name__ == "__main__":
    unittest.main()
