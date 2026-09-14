import unittest
from unittest.mock import MagicMock, patch, call
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
        self.assertEqual(summary.folder_id, "folder123")
        self.assertEqual(summary.folder_url, "https://tidal.com/browse/folder/folder123")

        mock_delete_pl.assert_called_once_with(mock_session, "pl_obs")

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    def test_multi_genre_distribution_and_deduplication(
        self,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        """User Story 2: Track maps to primary and multiple sub-genres with deduplication."""
        mock_session = MagicMock()
        folder_mock = MagicMock(id="folder_multi")
        mock_get_folder.return_value = folder_mock
        mock_get_pls.return_value = []

        track = MagicMock(id="t_tron", isrc="GBAHT0900329", title="Tron", artist=MagicMock(name="Foals"))
        mock_fetch_tracks.return_value = ([track], 1)

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst

        # Track has primary_genre 'Math Rock' and sub_genres 'Dance-Punk', 'Post-Punk Revival', plus duplicate 'math rock'
        mock_cache_inst.get_cached_genres.return_value = (
            {
                "isrc:GBAHT0900329": {
                    "primary_genre": "Math Rock",
                    "sub_genres": ["Dance-Punk", "Post-Punk Revival", "math rock"],
                }
            },
            [],
        )

        summary = run_genre_playlist_sync(
            mock_session,
            folder_name="Genres",
            min_genre_size=1,
        )

        # 3 distinct playlists created: Math Rock, Dance-Punk, Post-Punk Revival (duplicate math rock ignored)
        self.assertEqual(summary.playlists_created, 3)

        created_playlist_names = [call.kwargs["name"] for call in mock_create_pl.call_args_list]
        self.assertIn("Math Rock", created_playlist_names)
        self.assertIn("Dance-Punk", created_playlist_names)
        self.assertIn("Post-Punk Revival", created_playlist_names)

        # Verify track was only added once to Math Rock
        for c in mock_create_pl.call_args_list:
            if c.kwargs["name"] == "Math Rock":
                self.assertEqual(c.kwargs["track_ids"], ["t_tron"])

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    def test_sub_genres_min_genre_size_suppression(
        self,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        """User Story 3: Sub-genres with fewer than min_genre_size tracks are suppressed, while qualifying sub-genres >= min_genre_size receive dedicated playlists."""
        mock_session = MagicMock()
        folder_mock = MagicMock(id="folder_thresh")
        mock_get_folder.return_value = folder_mock
        mock_get_pls.return_value = []

        # t1: Rare Genre with no subgenres (1 track < 5 -> goes to Others)
        # t2: Common Primary with sparse subgenre 'Micro-Genre' (1 track < 5 -> Micro-Genre suppressed, Common Primary has only 1 track -> goes to Others)
        # t3-t7: 5 tracks with qualifying subgenre 'Qualifying Sub' and primary 'Indie Rock' (Indie Rock >= 5, Qualifying Sub >= 5 -> both created)
        t1 = MagicMock(id="t1", isrc="ISRC1", title="Song 1", artist=MagicMock(name="Artist 1"))
        t2 = MagicMock(id="t2", isrc="ISRC2", title="Song 2", artist=MagicMock(name="Artist 2"))
        qualifying_tracks = [
            MagicMock(id=f"t{i}", isrc=f"ISRC{i}", title=f"Song {i}", artist=MagicMock(name=f"Artist {i}"))
            for i in range(3, 8)
        ]
        all_tracks = [t1, t2] + qualifying_tracks

        mock_fetch_tracks.return_value = (all_tracks, 1)

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst

        cached_dict = {
            "isrc:ISRC1": {
                "primary_genre": "Rare Primary",
                "sub_genres": [],
            },
            "isrc:ISRC2": {
                "primary_genre": "Common Primary",
                "sub_genres": ["Micro-Genre"],
            },
        }
        for i in range(3, 8):
            cached_dict[f"isrc:ISRC{i}"] = {
                "primary_genre": "Indie Rock",
                "sub_genres": ["Qualifying Sub"],
            }

        mock_cache_inst.get_cached_genres.return_value = (cached_dict, [])

        summary = run_genre_playlist_sync(
            mock_session,
            folder_name="Genres",
            min_genre_size=5,  # threshold is 5 tracks
        )

        created_playlist_names = [call.kwargs["name"] for call in mock_create_pl.call_args_list]

        # 'Micro-Genre' has only 1 track (< 5), so it MUST NOT be created as a standalone playlist!
        self.assertNotIn("Micro-Genre", created_playlist_names)

        # 'Qualifying Sub' has 5 tracks (>= 5), so it MUST be created!
        self.assertIn("Qualifying Sub", created_playlist_names)

        # 'Indie Rock' has 5 tracks (>= 5), so it MUST be created!
        self.assertIn("Indie Rock", created_playlist_names)

        # 'Rare Primary' and 'Common Primary' each have only 1 track (< 5), so their primary tracks are consolidated into 'Others'
        self.assertIn("Others", created_playlist_names)
        self.assertNotIn("Rare Primary", created_playlist_names)
        self.assertNotIn("Common Primary", created_playlist_names)

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.delete_playlist")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    def test_run_genre_organizer_sync_wipe_folder(
        self,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_delete_pl,
        mock_cache_service_cls,
    ):
        """User Story 4: Wiping folder deletes all pre-existing playlists and creates fresh playlists."""
        mock_session = MagicMock()
        folder_mock = MagicMock(id="folder_wipe")
        mock_get_folder.return_value = folder_mock

        old_pl_1 = MagicMock(id="old_pl_1", name="Old Rock")
        old_pl_2 = MagicMock(id="old_pl_2", name="Old Pop")
        mock_get_pls.return_value = [old_pl_1, old_pl_2]

        # Provide tracks to create a new playlist
        tracks = [
            MagicMock(id=f"t{i}", isrc=f"ISRC{i}", title=f"Song {i}", artist=MagicMock(name="Artist"))
            for i in range(5)
        ]
        mock_fetch_tracks.return_value = (tracks, 1)

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst
        mock_cache_inst.get_cached_genres.return_value = (
            {f"isrc:ISRC{i}": {"primary_genre": "Rock", "sub_genres": []} for i in range(5)},
            [],
        )

        summary = run_genre_playlist_sync(
            mock_session,
            folder_name="Test Folder",
            min_genre_size=2,
            wipe_folder=True,
        )

        # Both old playlists must be wiped
        self.assertEqual(summary.playlists_wiped, 2)
        mock_delete_pl.assert_any_call(mock_session, "old_pl_1")
        mock_delete_pl.assert_any_call(mock_session, "old_pl_2")
        self.assertEqual(mock_delete_pl.call_count, 2)

        # New playlist must be created inside the same folder container
        self.assertEqual(summary.playlists_created, 1)
        mock_create_pl.assert_called_once_with(
            mock_session,
            name="Rock",
            description="Auto-generated genre playlist for Rock.",
            folder_id="folder_wipe",
            track_ids=[f"t{i}" for i in range(5)],
        )

    @patch("src.services.tidal_service.delete_playlist")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    def test_run_genre_organizer_sync_wipe_only(
        self,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_delete_pl,
    ):
        """User Story 4: --wipe-only deletes all playlists and exits without scanning tracks or creating playlists."""
        mock_session = MagicMock()
        folder_mock = MagicMock(id="folder_wipe_only")
        mock_get_folder.return_value = folder_mock

        pl_a = MagicMock(id="pl_a", name="Playlist A")
        pl_b = MagicMock(id="pl_b", name="Playlist B")
        mock_get_pls.return_value = [pl_a, pl_b]

        summary = run_genre_playlist_sync(
            mock_session,
            folder_name="Test Folder",
            wipe_only=True,
        )

        self.assertEqual(summary.playlists_wiped, 2)
        mock_delete_pl.assert_any_call(mock_session, "pl_a")
        mock_delete_pl.assert_any_call(mock_session, "pl_b")
        self.assertEqual(mock_delete_pl.call_count, 2)

        # Must not scan tracks or create playlists
        mock_fetch_tracks.assert_not_called()
        mock_create_pl.assert_not_called()
        self.assertEqual(summary.playlists_created, 0)
        self.assertEqual(summary.library_tracks_scanned, 0)


if __name__ == "__main__":
    unittest.main()

