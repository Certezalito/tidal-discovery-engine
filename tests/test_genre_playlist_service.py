import unittest
from unittest.mock import MagicMock, patch, call
from src.services.genre_organizer_service import (
    TrackDedupGroup,
    calculate_playlist_sync_plan,
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

    # --- Feature 023: Duplicate Track Prevention, Automatic Cleanup & Zero-Churn Idempotency ---

    def test_calculate_sync_delta_detects_surplus_duplicates_and_normalizes_id_types(self):
        """T009: calculate_sync_delta removes surplus duplicates and avoids int/str churn."""
        to_add, to_remove = calculate_sync_delta(["1", "2"], ["1", "1", "1", "2"])
        self.assertEqual(to_add, [])
        self.assertEqual(to_remove, ["1", "1"])

        to_add_types, to_remove_types = calculate_sync_delta([101, 102], ["101", "102"])
        self.assertEqual(to_add_types, [])
        self.assertEqual(to_remove_types, [])

    def test_calculate_playlist_sync_plan_surgical_duplicate_and_obsolete_cleanup(self):
        """US2: Removes 2x/3x exact duplicates, cross-release ISRC duplicates, and all obsolete copies via item_uuid."""
        g1 = TrackDedupGroup(
            dedup_key="isrc:ISRC1",
            cache_key="isrc:ISRC1",
            representative_track=MagicMock(id="111", isrc="ISRC1"),
            candidate_track_ids=["111", "222"],
            canonical_track_id="111",
        )
        g2 = TrackDedupGroup(
            dedup_key="id:333",
            cache_key="fallback:song3|art3",
            representative_track=MagicMock(id="333", isrc=None),
            candidate_track_ids=["333"],
            canonical_track_id="333",
        )

        u1 = "00000000-0000-0000-0000-000000000001"
        u2 = "00000000-0000-0000-0000-000000000002"
        u3 = "00000000-0000-0000-0000-000000000003"
        u4 = "00000000-0000-0000-0000-000000000004"
        u5 = "00000000-0000-0000-0000-000000000005"
        u6 = "00000000-0000-0000-0000-000000000006"
        u7 = "00000000-0000-0000-0000-000000000007"

        existing_tracks = [
            MagicMock(id=222, isrc="ISRC1", item_uuid=u1),  # Alternate release already in playlist -> KEEP (FR-003)
            MagicMock(id=111, isrc="ISRC1", item_uuid=u2),  # Same ISRC duplicate -> REMOVE u2
            MagicMock(id=222, isrc="ISRC1", item_uuid=u3),  # 3rd copy of ISRC1 -> REMOVE u3
            MagicMock(id=333, isrc=None, item_uuid=u4),     # Missing-ISRC qualifying track -> KEEP
            MagicMock(id=333, isrc=None, item_uuid=u5),     # Exact catalog ID duplicate -> REMOVE u5
            MagicMock(id=999, isrc="ISRC9", item_uuid=u6),  # Obsolete copy 1 -> REMOVE u6
            MagicMock(id=999, isrc="ISRC9", item_uuid=u7),  # Obsolete copy 2 -> REMOVE u7
        ]

        plan = calculate_playlist_sync_plan([g1, g2], existing_tracks)

        self.assertEqual(plan.to_add_ids, [])
        self.assertEqual(plan.to_remove_items, [u2, u3, u5, u6, u7])
        self.assertEqual(plan.duplicates_removed, 3)

    def test_calculate_playlist_sync_plan_non_uuid_duplicate_fallback(self):
        """US2: When item_uuid is absent on surplus duplicate, removes by track_id and re-adds 1 clean copy."""
        g1 = TrackDedupGroup(
            dedup_key="isrc:ISRC1",
            cache_key="isrc:ISRC1",
            representative_track=MagicMock(id="111", isrc="ISRC1"),
            candidate_track_ids=["111"],
            canonical_track_id="111",
        )
        existing_tracks = [
            MagicMock(id="111", isrc="ISRC1", item_uuid=None),
            MagicMock(id="111", isrc="ISRC1", item_uuid=None),
        ]

        plan = calculate_playlist_sync_plan([g1], existing_tracks)
        self.assertEqual(plan.to_remove_items, ["111"])
        self.assertEqual(plan.to_add_ids, ["111"])
        self.assertEqual(plan.duplicates_removed, 1)

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.create_playlist_in_folder")
    def test_us1_isrc_dedup_distinct_versions_missing_isrc_and_post_dedup_threshold(
        self,
        mock_create_pl,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        """
        US1: Verifies ISRC deduplication with deterministic canonical ID selection,
        preservation of remix/live distinct ISRCs, missing-ISRC catalog ID fallback,
        and post-dedup --min-genre-size thresholding (FR-002, FR-003, FR-004, FR-008).
        """
        mock_session = MagicMock()
        mock_get_folder.return_value = MagicMock(id="folder_us1")
        mock_get_pls.return_value = []

        def _make_track(tid, isrc, title, artist_name):
            track = MagicMock(id=tid, isrc=isrc, title=title)
            track.artist = type("Artist", (), {"name": artist_name})()
            return track

        # "Shoegaze" has 5 raw tracks but only 4 UNIQUE recordings (222 & 111 share ISRC1) -> < 5 -> routes to Others!
        # "Dream Pop" has 5 unique tracks: studio (ISRC10), remix (ISRC11), live (ISRC12),
        # plus 2 tracks without ISRC (distinct catalog IDs 500 & 501, with 500 repeated once in scan) -> 5 unique!
        t_shoe_album = _make_track(222, "ISRC1", "Only Shallow", "MBV")
        t_shoe_single = _make_track(111, "ISRC1", "Only Shallow", "MBV")
        t_shoe_2 = _make_track(112, "ISRC2", "Loomer", "MBV")
        t_shoe_3 = _make_track(113, "ISRC3", "Touched", "MBV")
        t_shoe_4 = _make_track(114, "ISRC4", "To Here Knows When", "MBV")

        t_dp_studio = _make_track(301, "ISRC10", "Cherry-coloured Funk", "Cocteau Twins")
        t_dp_remix = _make_track(302, "ISRC11", "Cherry-coloured Funk (Remix)", "Cocteau Twins")
        t_dp_live = _make_track(303, "ISRC12", "Cherry-coloured Funk (Live)", "Cocteau Twins")
        t_dp_no_isrc_a = _make_track(500, None, "Untitled A", "Unknown Artist")
        t_dp_no_isrc_a_dup = _make_track(500, None, "Untitled A", "Unknown Artist")
        t_dp_no_isrc_b = _make_track(501, None, "Untitled B", "Unknown Artist")

        # Deliberately place id=222 BEFORE id=111 to verify deterministic lowest-ID selection (111)
        mock_fetch_tracks.return_value = (
            [
                t_shoe_album,
                t_shoe_single,
                t_shoe_2,
                t_shoe_3,
                t_shoe_4,
                t_dp_studio,
                t_dp_remix,
                t_dp_live,
                t_dp_no_isrc_a,
                t_dp_no_isrc_a_dup,
                t_dp_no_isrc_b,
            ],
            1,
        )

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst
        mock_cache_inst.get_cached_genres.return_value = (
            {
                "isrc:ISRC1": {"primary_genre": "Shoegaze", "sub_genres": ["Noise Pop"]},
                "isrc:ISRC2": {"primary_genre": "Shoegaze", "sub_genres": ["Noise Pop"]},
                "isrc:ISRC3": {"primary_genre": "Shoegaze", "sub_genres": ["Noise Pop"]},
                "isrc:ISRC4": {"primary_genre": "Shoegaze", "sub_genres": ["Noise Pop"]},
                "isrc:ISRC10": {"primary_genre": "Dream Pop", "sub_genres": []},
                "isrc:ISRC11": {"primary_genre": "Dream Pop", "sub_genres": []},
                "isrc:ISRC12": {"primary_genre": "Dream Pop", "sub_genres": []},
                "fallback:untitled a|unknown artist": {"primary_genre": "Dream Pop", "sub_genres": []},
                "fallback:untitled b|unknown artist": {"primary_genre": "Dream Pop", "sub_genres": []},
            },
            [],
        )

        run_genre_playlist_sync(mock_session, folder_name="Genres", min_genre_size=5)

        created_by_name = {c.kwargs["name"]: c.kwargs["track_ids"] for c in mock_create_pl.call_args_list}

        # Shoegaze & Noise Pop only have 4 UNIQUE tracks after deduplicating ISRC1 -> neither gets a standalone playlist!
        self.assertNotIn("Shoegaze", created_by_name)
        self.assertNotIn("Noise Pop", created_by_name)

        # Shoegaze's 4 unique tracks route to Others, with deterministic canonical ID "111" (not "222")
        self.assertIn("Others", created_by_name)
        self.assertEqual(created_by_name["Others"], ["111", "112", "113", "114"])

        # Dream Pop has all 5 unique tracks (studio + remix + live + 2 distinct missing-ISRC tracks, no dup of 500)
        self.assertIn("Dream Pop", created_by_name)
        self.assertEqual(created_by_name["Dream Pop"], ["301", "302", "303", "500", "501"])

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.get_playlist_tracks")
    @patch("src.services.tidal_service.sync_playlist_tracks")
    def test_us2_and_us3_existing_cleanup_multipage_and_consecutive_zero_churn(
        self,
        mock_sync_tracks,
        mock_get_playlist_tracks,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        """
        US2 & US3: Cleans up existing playlist with multi-page duplicate occurrences on Run 1,
        preserves alternate catalog release already present in the playlist, and achieves
        0 additions / 0 removals on Run 2 even when Tidal favorites pagination order reverses.
        """
        mock_session = MagicMock()
        mock_get_folder.return_value = MagicMock(id="folder_sync")

        existing_pl = MagicMock(id="pl_idm")
        existing_pl.name = "IDM"
        mock_get_pls.return_value = [existing_pl]

        # Library has 2 releases of ISRC1 (id=101 and id=202) plus 4 more unique tracks (total 5 unique)
        t1_a = MagicMock(id=101, isrc="ISRC1", title="Xtal", artist=MagicMock(name="Aphex Twin"))
        t1_b = MagicMock(id=202, isrc="ISRC1", title="Xtal", artist=MagicMock(name="Aphex Twin"))
        other_tracks = [
            MagicMock(id=100 + i, isrc=f"ISRC{i}", title=f"Track {i}", artist=MagicMock(name="BoC"))
            for i in range(2, 6)
        ]

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst
        cached_map = {
            f"isrc:ISRC{i}": {"primary_genre": "IDM", "sub_genres": []} for i in range(1, 6)
        }
        mock_cache_inst.get_cached_genres.return_value = (cached_map, [])

        # Simulate stateful playlist contents across Run 1 and Run 2 (spanning >100 positions conceptually)
        u = lambda n: f"00000000-0000-0000-0000-{n:012d}"
        playlist_state = [
            MagicMock(id=202, isrc="ISRC1", item_uuid=u(1)),  # Alternate release already in playlist -> KEEP
            MagicMock(id=102, isrc="ISRC2", item_uuid=u(2)),
            MagicMock(id=103, isrc="ISRC3", item_uuid=u(3)),
            MagicMock(id=104, isrc="ISRC4", item_uuid=u(4)),
            MagicMock(id=105, isrc="ISRC5", item_uuid=u(5)),
            MagicMock(id=202, isrc="ISRC1", item_uuid=u(6)),  # Exact duplicate on later page -> REMOVE
            MagicMock(id=101, isrc="ISRC1", item_uuid=u(7)),  # Cross-release ISRC duplicate -> REMOVE
        ]

        mock_get_playlist_tracks.side_effect = lambda sess, pl_id: list(playlist_state)

        def apply_sync(sess, pl_id, to_add_ids, to_remove_ids):
            remove_set = set(to_remove_ids)
            playlist_state[:] = [t for t in playlist_state if t.item_uuid not in remove_set]
            next_idx = 100
            for tid in to_add_ids:
                next_idx += 1
                playlist_state.append(MagicMock(id=tid, isrc=None, item_uuid=u(next_idx)))
            return True

        mock_sync_tracks.side_effect = apply_sync

        # Run 1: Favorites order has t1_a (101) before t1_b (202)
        mock_fetch_tracks.return_value = ([t1_a, t1_b] + other_tracks, 2)
        summary_run1 = run_genre_playlist_sync(mock_session, folder_name="Genres", min_genre_size=5)

        self.assertEqual(summary_run1.playlists_updated, 1)
        self.assertEqual(summary_run1.tracks_added, 0)
        self.assertEqual(summary_run1.tracks_removed, 2)
        mock_sync_tracks.assert_called_once_with(
            mock_session,
            "pl_idm",
            to_add_ids=[],
            to_remove_ids=[u(6), u(7)],
        )
        # Kept the pre-existing release (202) and removed only the two duplicate slots
        self.assertEqual([t.id for t in playlist_state], [202, 102, 103, 104, 105])

        # Run 2: Reverse favorites pagination order (t1_b before t1_a, reversed others) -> MUST be zero churn!
        mock_sync_tracks.reset_mock()
        mock_fetch_tracks.return_value = (list(reversed(other_tracks)) + [t1_b, t1_a], 2)
        summary_run2 = run_genre_playlist_sync(mock_session, folder_name="Genres", min_genre_size=5)

        self.assertEqual(summary_run2.playlists_updated, 0)
        self.assertEqual(summary_run2.tracks_added, 0)
        self.assertEqual(summary_run2.tracks_removed, 0)
        mock_sync_tracks.assert_not_called()

        # Run 3: Add 1 new qualifying track -> adds ONLY that single new track with 0 removals
        t6 = MagicMock(id=106, isrc="ISRC6", title="Track 6", artist=MagicMock(name="BoC"))
        cached_map["isrc:ISRC6"] = {"primary_genre": "IDM", "sub_genres": []}
        mock_fetch_tracks.return_value = ([t1_a, t1_b] + other_tracks + [t6], 2)
        summary_run3 = run_genre_playlist_sync(mock_session, folder_name="Genres", min_genre_size=5)

        self.assertEqual(summary_run3.playlists_updated, 1)
        self.assertEqual(summary_run3.tracks_added, 1)
        self.assertEqual(summary_run3.tracks_removed, 0)
        mock_sync_tracks.assert_called_once_with(
            mock_session,
            "pl_idm",
            to_add_ids=["106"],
            to_remove_ids=[],
        )

    @patch("src.services.genre_cache_service.GenreCacheService")
    @patch("src.services.tidal_service.fetch_all_favorite_tracks")
    @patch("src.services.tidal_service.get_or_create_folder")
    @patch("src.services.tidal_service.get_playlists_in_folder")
    @patch("src.services.tidal_service.get_playlist_tracks")
    @patch("src.services.tidal_service.sync_playlist_tracks")
    def test_skips_delisted_remapped_track_while_preserving_different_isrc_releases(
        self,
        mock_sync_tracks,
        mock_get_playlist_tracks,
        mock_get_pls,
        mock_get_folder,
        mock_fetch_tracks,
        mock_cache_service_cls,
    ):
        """
        Delisted/unavailable tracks (available=False or 404 ObjectNotFound) are skipped
        before items/add so Tidal cannot remap them onto a live track and create same-release
        duplicates, while different-ISRC releases on separate albums remain preserved.
        """
        from tidalapi.exceptions import ObjectNotFound

        def _mk(tid, isrc, title, artist_name, item_uuid=None):
            t = MagicMock(id=tid, isrc=isrc, title=title, item_uuid=item_uuid)
            t.artist = type("Artist", (), {"name": artist_name})()
            return t

        mock_session = MagicMock()
        # 68921617 is delisted (available=False), 228223770 is 404 ObjectNotFound
        def track_lookup(tid):
            if str(tid) == "68921617":
                return MagicMock(available=False)
            if str(tid) == "228223770":
                raise ObjectNotFound("404")
            return MagicMock(available=True)

        mock_session.track.side_effect = track_lookup
        mock_get_folder.return_value = MagicMock(id="folder_cw")
        pl = MagicMock(id="pl_cw")
        pl.name = "Chillwave"
        mock_get_pls.return_value = [pl]

        favs = [
            _mk(175941190, "QZDA62137841", "Too Much To Lose", "Sun Glitters"),
            _mk(68921617, "QZ4JJ1702717", "Too Much to Lose", "Sun Glitters"),
            _mk(228223770, "USOLD9999999", "Delisted Track", "Old Band"),
            _mk(216339792, "USZMA1300002", "Dionysian", "Mister Lies"),
            _mk(216336623, "USZMA1200084", "Dionysian", "Mister Lies"),
        ]
        mock_fetch_tracks.return_value = (favs, 1)

        mock_cache_inst = MagicMock()
        mock_cache_service_cls.return_value = mock_cache_inst
        mock_cache_inst.get_cached_genres.return_value = (
            {
                "isrc:QZDA62137841": {"primary_genre": "Chillwave", "sub_genres": []},
                "isrc:QZ4JJ1702717": {"primary_genre": "Chillwave", "sub_genres": []},
                "isrc:USOLD9999999": {"primary_genre": "Chillwave", "sub_genres": []},
                "isrc:USZMA1300002": {"primary_genre": "Chillwave", "sub_genres": []},
                "isrc:USZMA1200084": {"primary_genre": "Chillwave", "sub_genres": []},
            },
            [],
        )

        u = lambda n: f"00000000-0000-0000-0000-{n:012d}"
        mock_get_playlist_tracks.return_value = [
            _mk(175941190, "QZDA62137841", "Too Much To Lose", "Sun Glitters", item_uuid=u(1)),
            _mk(175941190, "QZDA62137841", "Too Much To Lose", "Sun Glitters", item_uuid=u(2)),
            _mk(216339792, "USZMA1300002", "Dionysian", "Mister Lies", item_uuid=u(3)),
            _mk(216336623, "USZMA1200084", "Dionysian", "Mister Lies", item_uuid=u(4)),
        ]
        mock_sync_tracks.return_value = True

        summary = run_genre_playlist_sync(mock_session, folder_name="Genres", min_genre_size=1)

        # Must remove ONLY u(2) (dup 175941190), skip delisted 68921617 & 228223770 (0 added),
        # and keep BOTH Mister Lies different-ISRC releases (u3 & u4)!
        self.assertEqual(summary.playlists_updated, 1)
        self.assertEqual(summary.tracks_added, 0)
        self.assertEqual(summary.tracks_removed, 1)
        mock_sync_tracks.assert_called_once_with(
            mock_session,
            "pl_cw",
            to_add_ids=[],
            to_remove_ids=[u(2)],
        )


if __name__ == "__main__":
    unittest.main()

