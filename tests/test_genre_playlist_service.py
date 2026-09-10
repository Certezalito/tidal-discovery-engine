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


if __name__ == "__main__":
    unittest.main()
