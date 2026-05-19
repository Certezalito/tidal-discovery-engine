import os
import time
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import main
from src.services.tidal_service import FavoritesRetrievalError


class TestExcludeFavoritesCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def _make_lastfm_track(self, artist, title):
        track = MagicMock()
        track.artist.name = artist
        track.title = title
        return track

    def _make_tidal_track(self, artist, title, isrc=None, track_id=None):
        track = MagicMock()
        track.artist.name = artist
        track.name = title
        track.title = title
        track.isrc = isrc
        track.id = track_id or f"{artist}-{title}"
        return track

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_exclude_favorites_filters_output_tracks(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]

        similar_a = self._make_lastfm_track("Artist A", "Track A")
        similar_b = self._make_lastfm_track("Artist B", "Track B")
        mock_get_similar.return_value = [similar_a, similar_b]

        tidal_a = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A", track_id="1")
        tidal_b = self._make_tidal_track("Artist B", "Track B", isrc="ISRC_B", track_id="2")
        mock_search_for_track.side_effect = [tidal_a, tidal_b]

        mock_build_snapshot.return_value = {
            "identity_keys": {"isrc:ISRCA"},
            "total_favorites": 1,
            "pages_loaded": 1,
            "load_complete": True,
        }

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--num-tidal-tracks",
                "1",
                "--num-similar-tracks",
                "2",
                "--exclude-favorites",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        args, kwargs = mock_create_playlist.call_args
        tracks = kwargs["tracks"]
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].id, "2")

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_exclude_favorites_supplements_to_requested_count_when_possible(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]

        # Main over-fetches when exclusion is enabled; we return 6 candidates.
        mock_get_similar.return_value = [
            self._make_lastfm_track(f"Artist {i}", f"Track {i}") for i in range(6)
        ]
        mock_search_for_track.side_effect = [
            self._make_tidal_track(f"Artist {i}", f"Track {i}", isrc=f"ISRC_{i}", track_id=str(i))
            for i in range(6)
        ]

        # Exclude two tracks; requested count is still achievable.
        mock_build_snapshot.return_value = {
            "identity_keys": {"isrc:ISRC0", "isrc:ISRC1"},
            "total_favorites": 2,
            "pages_loaded": 1,
            "load_complete": True,
        }

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--num-tidal-tracks",
                "1",
                "--num-similar-tracks",
                "2",
                "--exclude-favorites",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_create_playlist.call_args
        self.assertEqual(len(kwargs["tracks"]), 2)

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    @patch("src.cli.main.log_cli_warning")
    def test_exclude_favorites_shortfall_emits_warning(
        self,
        mock_log_warning,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]
        mock_get_similar.return_value = [self._make_lastfm_track("Artist A", "Track A")]
        mock_search_for_track.return_value = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A", track_id="1")

        # Exclude the only candidate to force shortfall.
        mock_build_snapshot.return_value = {
            "identity_keys": {"isrc:ISRCA"},
            "total_favorites": 1,
            "pages_loaded": 1,
            "load_complete": True,
        }

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--num-tidal-tracks",
                "1",
                "--num-similar-tracks",
                "2",
                "--exclude-favorites",
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue(any(call.args[0] == "EXCLUDE_FAVORITES_SHORTFALL" for call in mock_log_warning.call_args_list))

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_no_favorites_lookup_without_flag_across_default_mode(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]

        similar = self._make_lastfm_track("Artist A", "Track A")
        mock_get_similar.return_value = [similar]
        mock_search_for_track.return_value = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A", track_id="1")

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--num-tidal-tracks",
                "1",
                "--num-similar-tracks",
                "1",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_build_snapshot.assert_not_called()

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.resolve_text_seed_track")
    @patch("src.services.gemini_service.get_recommendations")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_no_favorites_lookup_without_flag_across_gemini_and_mode3(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_get_recommendations,
        mock_resolve_text_seed_track,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed_track = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_resolve_text_seed_track.return_value = (seed_track, "exact")

        mock_get_recommendations.return_value = [{"artist": "Artist A", "title": "Track A", "isrc": None}]
        mock_search_for_track.return_value = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A", track_id="1")

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            main,
            [
                "--gemini",
                "--playlist-name",
                "Test Playlist",
                "--artist",
                "Seed Artist",
                "--track",
                "Seed Title",
                "--num-similar-tracks",
                "1",
            ],
            env={"GEMINI_API_KEY": "test-key"},
        )

        self.assertEqual(result.exit_code, 0)
        mock_build_snapshot.assert_not_called()

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_fail_closed_when_favorites_fetch_fails(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []
        mock_get_random.return_value = [self._make_tidal_track("Seed Artist", "Seed Title")]
        mock_get_similar.return_value = [self._make_lastfm_track("Artist A", "Track A")]
        mock_search_for_track.return_value = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A")
        mock_build_snapshot.side_effect = FavoritesRetrievalError("page failed")

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--exclude-favorites",
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Failed to retrieve your complete favorites list", result.output)
        mock_create_playlist.assert_not_called()

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_fail_closed_when_favorites_snapshot_incomplete(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []
        mock_get_random.return_value = [self._make_tidal_track("Seed Artist", "Seed Title")]
        mock_get_similar.return_value = [self._make_lastfm_track("Artist A", "Track A")]
        mock_search_for_track.return_value = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A")
        mock_build_snapshot.side_effect = FavoritesRetrievalError("incomplete favorites snapshot")

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--exclude-favorites",
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Failed to retrieve your complete favorites list", result.output)
        mock_create_playlist.assert_not_called()

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_no_favorites_cache_files_created(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]
        mock_get_similar.return_value = [self._make_lastfm_track("Artist A", "Track A")]
        mock_search_for_track.return_value = self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A", track_id="1")

        mock_build_snapshot.return_value = {
            "identity_keys": set(),
            "total_favorites": 1,
            "pages_loaded": 1,
            "load_complete": True,
        }

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)
                result = self.runner.invoke(
                    main,
                    [
                        "--playlist-name",
                        "Test Playlist",
                        "--exclude-favorites",
                    ],
                )
                self.assertEqual(result.exit_code, 0)
                for name in os.listdir(tmp_dir):
                    self.assertNotIn("favorite_cache", name)
            finally:
                os.chdir(cwd)

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    def test_output_artifact_matches_baseline_without_flag(
        self,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]
        mock_get_similar.return_value = [
            self._make_lastfm_track("Artist A", "Track A"),
            self._make_lastfm_track("Artist B", "Track B"),
        ]
        mock_search_for_track.side_effect = [
            self._make_tidal_track("Artist A", "Track A", isrc="ISRC_A", track_id="1"),
            self._make_tidal_track("Artist B", "Track B", isrc="ISRC_B", track_id="2"),
        ]

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--num-tidal-tracks",
                "1",
                "--num-similar-tracks",
                "2",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_create_playlist.call_args
        track_ids = [track.id for track in kwargs["tracks"]]
        self.assertEqual(track_ids, ["1", "2"])

    @patch("src.services.tidal_service.get_session")
    @patch("src.services.lastfm_service.get_network")
    @patch("src.cli.main.setup_logging")
    @patch("src.services.tidal_service.get_random_favorite_tracks")
    @patch("src.services.lastfm_service.get_similar_tracks")
    @patch("src.services.lastfm_service.get_top_tags_for_artist")
    @patch("src.services.tidal_service.search_for_track")
    @patch("src.services.tidal_service.create_playlist")
    @patch("src.services.tidal_service.build_favorites_snapshot")
    def test_exclusion_runtime_under_threshold_typical_fixture(
        self,
        mock_build_snapshot,
        mock_create_playlist,
        mock_search_for_track,
        mock_top_tags,
        mock_get_similar,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_top_tags.return_value = []

        seed = self._make_tidal_track("Seed Artist", "Seed Title", isrc="SEED123")
        mock_get_random.return_value = [seed]

        # Simulate a typical-library exclusion run with enough candidates.
        mock_build_snapshot.return_value = {
            "identity_keys": {f"isrc:FAV{index:05d}" for index in range(2000)},
            "total_favorites": 2000,
            "pages_loaded": 20,
            "load_complete": True,
        }

        similar_tracks = [self._make_lastfm_track(f"Artist {i}", f"Track {i}") for i in range(20)]
        mock_get_similar.return_value = similar_tracks
        mock_search_for_track.side_effect = [
            self._make_tidal_track(f"Artist {i}", f"Track {i}", isrc=f"ISRC{i:05d}", track_id=str(i))
            for i in range(20)
        ]

        playlist = MagicMock()
        playlist.id = "playlist-1"
        playlist.name = "Test Playlist"
        mock_create_playlist.return_value = playlist

        start = time.perf_counter()
        result = self.runner.invoke(
            main,
            [
                "--playlist-name",
                "Test Playlist",
                "--num-tidal-tracks",
                "1",
                "--num-similar-tracks",
                "5",
                "--exclude-favorites",
            ],
        )
        elapsed = time.perf_counter() - start

        self.assertEqual(result.exit_code, 0)
        self.assertLessEqual(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main()
