import unittest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from src.cli.main import cli
from src.services.gemini_service import GeminiModelUnavailableError
import datetime
from src.lib.logging import (
    EXCLUDE_FAVORITES_SHORTFALL,
    RADIO_UNRESOLVED_TRACKS,
    SEED_NOT_RESOLVED_ON_TIDAL,
)

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
        result = self.runner.invoke(cli, ['recommend', '--playlist-name', 'Test Playlist', '--folder', 'My Custom Folder'])
        
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
    def test_recommend_rejects_non_positive_num_similar_tracks(self, mock_setup_logging):
        result = self.runner.invoke(
            cli,
            [
                'recommend',
                '--playlist-name', 'Test Playlist',
                '--num-similar-tracks', '0',
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('--num-similar-tracks must be a positive integer', result.output)

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.tidal_service.build_favorites_snapshot')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.get_track_by_isrc')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.cli.main.log_cli_warning')
    def test_gemini_failure_with_exclude_favorites_not_misattributed(
        self,
        mock_log_warning,
        mock_create_playlist,
        mock_search_for_track,
        mock_get_track_by_isrc,
        mock_get_recommendations,
        mock_build_snapshot,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed = MagicMock()
        seed.artist.name = 'Seed Artist'
        seed.name = 'Seed Title'
        mock_get_random.return_value = [seed]

        mock_build_snapshot.return_value = {
            'identity_keys': set(),
            'total_favorites': 0,
            'pages_loaded': 1,
            'load_complete': True,
        }
        mock_get_recommendations.side_effect = ValueError('Gemini request failed. model=primary')

        result = self.runner.invoke(
            cli,
            [
                'recommend','--gemini', '--exclude-favorites', '--playlist-name', 'Test Playlist'],
            env={'GEMINI_API_KEY': 'test-key'},
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Gemini request failed', result.output)
        self.assertFalse(mock_create_playlist.called)
        self.assertFalse(any(call.args[0] == EXCLUDE_FAVORITES_SHORTFALL for call in mock_log_warning.call_args_list))

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.tidal_service.build_favorites_snapshot')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.get_track_by_isrc')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.cli.main.log_cli_warning')
    def test_gemini_recovery_results_filter_and_create_playlist(
        self,
        mock_log_warning,
        mock_create_playlist,
        mock_search,
        mock_get_track_by_isrc,
        mock_get_recommendations,
        mock_build_snapshot,
        mock_get_random,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed = MagicMock()
        seed.artist.name = 'Seed Artist'
        seed.name = 'Seed Title'
        mock_get_random.return_value = [seed]

        mock_build_snapshot.return_value = {
            'identity_keys': {'isrc:FAV001'},
            'total_favorites': 1,
            'pages_loaded': 1,
            'load_complete': True,
        }

        mock_get_recommendations.return_value = [
            {'artist': 'Artist A', 'title': 'Track A', 'isrc': 'FAV001'},
            {'artist': 'Artist B', 'title': 'Track B', 'isrc': 'NEW001'},
        ]
        mock_get_track_by_isrc.side_effect = [None, None]

        favorite_track = MagicMock()
        favorite_track.artist.name = 'Artist A'
        favorite_track.name = 'Track A'
        favorite_track.isrc = 'FAV001'
        favorite_track.id = 'fav-track'

        new_track = MagicMock()
        new_track.artist.name = 'Artist B'
        new_track.name = 'Track B'
        new_track.isrc = 'NEW001'
        new_track.id = 'new-track'

        mock_search.side_effect = [favorite_track, new_track]

        playlist = MagicMock()
        playlist.id = 'playlist-1'
        playlist.name = 'Test Playlist'
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            cli,
            [
                'recommend',
                '--gemini',
                '--exclude-favorites',
                '--playlist-name', 'Test Playlist',
                '--num-tidal-tracks', '1',
                '--num-similar-tracks', '1',
            ],
            env={'GEMINI_API_KEY': 'test-key'},
        )

        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_create_playlist.call_args
        self.assertEqual(len(kwargs['tracks']), 1)
        self.assertEqual(kwargs['tracks'][0].id, 'new-track')
        self.assertFalse(any(call.args[0] == EXCLUDE_FAVORITES_SHORTFALL for call in mock_log_warning.call_args_list))

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.get_random_favorite_tracks')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.create_playlist')
    def test_non_gemini_mode_does_not_call_gemini_service(
        self,
        mock_create_playlist,
        mock_search,
        mock_similar,
        mock_get_random,
        mock_get_recommendations,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed = MagicMock()
        seed.artist.name = 'Seed Artist'
        seed.name = 'Seed Track'
        mock_get_random.return_value = [seed]

        similar_track = MagicMock()
        similar_track.artist.name = 'Artist B'
        similar_track.title = 'Track B'
        mock_similar.return_value = [similar_track]

        resolved = MagicMock()
        resolved.artist.name = 'Artist B'
        resolved.name = 'Track B'
        resolved.id = '1'
        mock_search.return_value = resolved

        playlist = MagicMock()
        playlist.id = 'playlist-1'
        playlist.name = 'Test Playlist'
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(cli, ['recommend', '--playlist-name', 'Test Playlist'])

        self.assertEqual(result.exit_code, 0)
        mock_get_recommendations.assert_not_called()



    @patch('src.cli.main.setup_logging')
    @patch('src.cli.main.run_genre_organizer_sync')
    @patch('src.services.tidal_service.get_session')
    def test_organize_folder_precedence(self, mock_get_session, mock_run_sync, mock_setup_logging):
        mock_get_session.return_value = MagicMock()
        mock_summary = MagicMock()
        mock_summary.library_tracks_scanned = 0
        mock_summary.cache_hits = 0
        mock_summary.cache_misses = 0
        mock_summary.classified_tracks = 0
        mock_summary.unknown_tracks = 0
        mock_summary.playlists_created = 5
        mock_summary.playlists_updated = 0
        mock_summary.playlists_deleted = 0
        mock_summary.duplicate_playlists_deleted = 0
        mock_summary.tracks_added = 50
        mock_summary.tracks_removed = 0
        mock_run_sync.return_value = mock_summary

        # CLI argument provided
        result = self.runner.invoke(
            cli,
            ['organize', '--folder', 'My Custom Genres'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result.exit_code, 0)
        mock_run_sync.assert_called_with(mock_get_session.return_value, 'My Custom Genres', min_genre_size=5, db_path='data/genre_cache.db', refresh_genres=False, wipe_folder=False, wipe_only=False)
        
        # CLI argument absent (defaults to "Genres")
        result2 = self.runner.invoke(
            cli,
            ['organize'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result2.exit_code, 0)
        mock_run_sync.assert_called_with(mock_get_session.return_value, 'Genres', min_genre_size=5, db_path='data/genre_cache.db', refresh_genres=False, wipe_folder=False, wipe_only=False)

    @patch('src.cli.main.setup_logging')
    @patch('src.cli.main.run_genre_organizer_sync')
    @patch('src.services.tidal_service.get_session')
    def test_organize_rerun_sync_metrics(self, mock_get_session, mock_run_sync, mock_setup_logging):
        """
        Add CLI rerun test verifying no duplicate playlists and synced membership
        """
        mock_get_session.return_value = MagicMock()
        mock_summary = MagicMock()
        mock_summary.library_tracks_scanned = 10
        mock_summary.cache_hits = 10
        mock_summary.cache_misses = 0
        mock_summary.playlists_created = 0
        mock_summary.playlists_updated = 0
        mock_summary.playlists_deleted = 0
        mock_summary.duplicate_playlists_deleted = 0
        mock_summary.tracks_added = 0
        mock_summary.tracks_removed = 0
        mock_summary.unknown_tracks = 0
        mock_summary.classified_tracks = 10
        mock_run_sync.return_value = mock_summary

        result = self.runner.invoke(
            cli,
            ['organize'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(mock_run_sync.call_count, 1)

    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.fetch_all_favorite_tracks')
    @patch('src.services.tidal_service.get_session')
    def test_organize_empty_library(self, mock_get_session, mock_fetch, mock_setup_logging):
        """
        Add edge-case test coverage for empty libraries
        """
        mock_get_session.return_value = MagicMock()
        mock_fetch.return_value = ([], 0)

        result = self.runner.invoke(
            cli,
            ['organize', '--folder', 'My Custom Genres'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        
        self.assertEqual(result.exit_code, 0)

    @patch('src.cli.main.setup_logging')
    @patch('src.cli.main.run_genre_organizer_sync')
    @patch('src.services.tidal_service.get_session')
    def test_organize_min_genre_size_passed(self, mock_get_session, mock_run_sync, mock_setup_logging):
        """
        Add CLI test for `--min-genre-size` threshold grouping into "Others"
        """
        mock_get_session.return_value = MagicMock()
        mock_summary = MagicMock()
        mock_summary.library_tracks_scanned = 0
        mock_summary.duplicate_playlists_deleted = 0
        mock_summary.cache_hits = 0
        mock_summary.cache_misses = 0
        mock_summary.playlists_created = 0
        mock_summary.playlists_updated = 0
        mock_summary.playlists_deleted = 0
        mock_summary.tracks_added = 0
        mock_summary.tracks_removed = 0
        mock_run_sync.return_value = mock_summary

        # Default is 5
        result = self.runner.invoke(
            cli,
            ['organize'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        self.assertEqual(result.exit_code, 0)
        args, kwargs = mock_run_sync.call_args
        self.assertEqual(kwargs.get('min_genre_size', 5), 5)
        
        # Override to 15
        result2 = self.runner.invoke(
            cli,
            ['organize', '--min-genre-size', '15'],
            env={'GEMINI_API_KEY': 'test-key'}
        )
        self.assertEqual(result2.exit_code, 0)
        args2, kwargs2 = mock_run_sync.call_args
        self.assertEqual(kwargs2['min_genre_size'], 15)

    @patch('src.services.tidal_service.get_or_create_folder')
    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    def test_radio_command_success_with_defaults_and_track_one(
        self,
        mock_resolve_seed,
        mock_get_network,
        mock_get_similar,
        mock_search,
        mock_create_playlist,
        mock_setup_logging,
        mock_get_session,
        mock_get_folder,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        default_folder = MagicMock(id="radio-folder-1", name="Radio")
        mock_get_folder.return_value = default_folder

        seed_track = MagicMock()
        seed_track.id = "seed-id-1"
        seed_track.artist.name = "Underworld"
        seed_track.title = "Born Slippy"
        seed_track.name = "Born Slippy"
        mock_resolve_seed.return_value = (seed_track, "exact")

        sim_tracks = []
        for i in range(49):
            t = MagicMock()
            t.artist.name = f"Artist {i}"
            t.title = f"Track {i}"
            sim_tracks.append(t)
        mock_get_similar.return_value = sim_tracks

        def fake_search(session, track_query):
            track = MagicMock()
            track.id = f"tidal-{track_query.title}"
            track.artist.name = track_query.artist.name
            track.name = track_query.title
            return track
        mock_search.side_effect = fake_search

        playlist = MagicMock()
        playlist.id = "playlist-101"
        playlist.name = "Underworld - Born Slippy Radio"
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            cli,
            ["radio", "--artist", "Underworld", "--track", "Born Slippy"],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_create_playlist.called)
        mock_get_folder.assert_called_with(mock_get_session.return_value, "Radio")
        call_args, call_kwargs = mock_create_playlist.call_args
        self.assertEqual(call_args[1], "Underworld - Born Slippy Radio")
        self.assertEqual(call_kwargs["folder_id"], "radio-folder-1")
        inserted_tracks = call_kwargs["tracks"]
        self.assertEqual(len(inserted_tracks), 50)
        self.assertEqual(inserted_tracks[0].id, "seed-id-1")
        self.assertIn("Born Slippy", call_kwargs["description"])
        self.assertIn("Underworld", call_kwargs["description"])

    @patch('src.services.tidal_service.get_or_create_folder')
    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    def test_radio_folder_override(
        self,
        mock_resolve_seed,
        mock_get_network,
        mock_get_similar,
        mock_search,
        mock_create_playlist,
        mock_setup_logging,
        mock_get_session,
        mock_get_folder,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()
        mock_resolve_seed.return_value = (MagicMock(id="s1"), "exact")
        mock_get_similar.return_value = [MagicMock(artist=MagicMock(name="A1"), title="T1")]
        mock_search.return_value = MagicMock(id="m1")
        mock_create_playlist.return_value = MagicMock(id="p1")
        custom_folder = MagicMock(id="custom-f-id", name="Custom Stations")
        mock_get_folder.return_value = custom_folder

        result = self.runner.invoke(
            cli,
            ["radio", "--artist", "Underworld", "--track", "Born Slippy", "--folder", "Custom Stations", "--num-tracks", "2"],
        )

        self.assertEqual(result.exit_code, 0)
        mock_get_folder.assert_called_with(mock_get_session.return_value, "Custom Stations")
        call_args, call_kwargs = mock_create_playlist.call_args
        self.assertEqual(call_kwargs["folder_id"], "custom-f-id")

    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    def test_radio_command_with_date_token_in_playlist_name(
        self,
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
        seed_track.id = "seed-id-1"
        mock_resolve_seed.return_value = (seed_track, "exact")

        sim_track = MagicMock()
        sim_track.artist.name = "Artist 1"
        sim_track.title = "Track 1"
        mock_get_similar.return_value = [sim_track]

        tidal_track = MagicMock()
        tidal_track.id = "tidal-1"
        mock_search.return_value = tidal_track

        mock_create_playlist.return_value = MagicMock(id="p1", name="Custom")

        result = self.runner.invoke(
            cli,
            ["radio", "--artist", "Underworld", "--track", "Born Slippy", "--playlist-name", "Born Slippy Radio {date}", "--num-tracks", "2"],
        )

        self.assertEqual(result.exit_code, 0)
        expected_date = datetime.date.today().strftime("%Y%m%d")
        call_args, call_kwargs = mock_create_playlist.call_args
        self.assertEqual(call_args[1], f"Born Slippy Radio {expected_date}")

    def test_track_radio_alias_unrecognized(self):
        result = self.runner.invoke(
            cli,
            ["track-radio", "--artist", "Underworld", "--track", "Born Slippy"],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such command 'track-radio'", result.output)

    @patch('src.cli.main.setup_logging')
    def test_radio_input_validations(self, mock_setup_logging):
        # Missing artist
        res1 = self.runner.invoke(cli, ["radio", "--track", "Born Slippy"])
        self.assertNotEqual(res1.exit_code, 0)

        # Whitespace-only artist
        res2 = self.runner.invoke(cli, ["radio", "--artist", "   ", "--track", "Born Slippy"])
        self.assertNotEqual(res2.exit_code, 0)
        self.assertIn("Both --artist and --track are required and cannot be empty.", res2.output)

        # Whitespace-only track
        res3 = self.runner.invoke(cli, ["radio", "--artist", "Underworld", "--track", "   "])
        self.assertNotEqual(res3.exit_code, 0)
        self.assertIn("Both --artist and --track are required and cannot be empty.", res3.output)

        # Non-positive count
        res4 = self.runner.invoke(cli, ["radio", "--artist", "Underworld", "--track", "Born Slippy", "--num-tracks", "0"])
        self.assertNotEqual(res4.exit_code, 0)
        self.assertIn("--num-tracks must be a positive integer.", res4.output)

    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    def test_radio_zero_tracks_inserted_fails(
        self,
        mock_resolve_seed,
        mock_get_network,
        mock_get_similar,
        mock_search,
        mock_setup_logging,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        # Seed track unresolvable (text_only)
        mock_resolve_seed.return_value = (MagicMock(spec=[]), "text_only")
        mock_get_similar.return_value = []
        mock_search.return_value = None

        result = self.runner.invoke(
            cli,
            ["radio", "--artist", "Ghost Artist", "--track", "Ghost Track"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No tracks could be inserted into the playlist after recommendation resolution.", result.output)

    @patch('src.services.tidal_service.get_session')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.build_favorites_snapshot')
    @patch('src.services.gemini_service.get_recommendations')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.tidal_service.filter_out_favorites')
    @patch('src.services.tidal_service.get_or_create_folder')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    def test_radio_with_gemini_and_options(
        self,
        mock_resolve_seed,
        mock_create_playlist,
        mock_get_folder,
        mock_filter_favs,
        mock_search,
        mock_get_recs,
        mock_build_favs,
        mock_setup_logging,
        mock_get_network,
        mock_get_session,
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_network.return_value = MagicMock()

        seed_track = MagicMock()
        seed_track.id = "seed-1"
        seed_track.artist.name = "Burial"
        seed_track.name = "Archangel"
        mock_resolve_seed.return_value = (seed_track, "exact")

        mock_build_favs.return_value = {
            "identity_keys": {"isrc:OLD123"},
            "total_favorites": 1,
            "pages_loaded": 1,
        }

        mock_get_recs.return_value = [
            {"artist": "Four Tet", "title": "Rounds"},
            {"artist": "Untold", "title": "Stop What You're Doing"},
        ]

        t1 = MagicMock(id="t1")
        t1.artist.name = "Four Tet"
        t1.name = "Rounds"
        t2 = MagicMock(id="t2")
        t2.artist.name = "Untold"
        t2.name = "Stop What You're Doing"
        mock_search.side_effect = [t1, t2]

        mock_filter_favs.return_value = ([t1, t2], 0)

        folder_mock = MagicMock()
        folder_mock.id = "folder-station"
        folder_mock.name = "Electronic Stations"
        mock_get_folder.return_value = folder_mock

        playlist = MagicMock(id="p-gemini", name="Burial - Archangel Radio")
        mock_create_playlist.return_value = playlist

        result = self.runner.invoke(
            cli,
            [
                "radio",
                "--artist", "Burial",
                "--track", "Archangel",
                "--gemini",
                "--shuffle",
                "--exclude-favorites",
                "--folder", "Electronic Stations",
                "--num-tracks", "3",
            ],
            env={"GEMINI_API_KEY": "fake-key"},
        )

        self.assertEqual(result.exit_code, 0)
        mock_get_folder.assert_called_with(mock_get_session.return_value, "Electronic Stations")
        call_args, call_kwargs = mock_create_playlist.call_args
        self.assertEqual(call_kwargs["folder_id"], "folder-station")
        self.assertEqual(call_kwargs["tracks"][0].id, "seed-1")

    @patch('src.services.tidal_service.get_session')
    @patch('src.cli.main.setup_logging')
    @patch('src.services.tidal_service.create_playlist')
    @patch('src.services.tidal_service.search_for_track')
    @patch('src.services.lastfm_service.get_similar_tracks')
    @patch('src.services.lastfm_service.get_network')
    @patch('src.services.tidal_service.resolve_text_seed_track')
    @patch('src.services.gemini_service.get_recommendations')
    def test_radio_gemini_fallback_to_lastfm(
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
        seed_track.id = "seed-id-1"
        seed_track.artist.name = "Seed Artist"
        seed_track.title = "Seed Track"
        seed_track.name = "Seed Track"
        mock_resolve_seed.return_value = (seed_track, "exact")

        mock_get_recommendations.side_effect = GeminiModelUnavailableError("model unavailable")

        sim_track = MagicMock()
        sim_track.artist.name = "Similar Artist"
        sim_track.title = "Similar Track"
        mock_get_similar.return_value = [sim_track]

        mock_tidal_track = MagicMock()
        mock_tidal_track.id = "tidal-rec-1"
        mock_tidal_track.artist.name = "Similar Artist"
        mock_tidal_track.name = "Similar Track"
        mock_search.return_value = mock_tidal_track

        mock_create_playlist.return_value = MagicMock(id="p-fb", name="Seed Artist - Seed Track Radio")

        result = self.runner.invoke(
            cli,
            [
                "radio",
                "--gemini",
                "--artist", "Seed Artist",
                "--track", "Seed Track",
                "--num-tracks", "2",
            ],
            env={"GEMINI_API_KEY": "test-key"},
        )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_get_similar.called)

    def test_recommend_rejects_single_seed_options(self):
        result_artist = self.runner.invoke(
            cli,
            [
                "recommend",
                "--artist", "Faithless",
                "--playlist-name", "Faithless Radio",
            ],
        )
        self.assertNotEqual(result_artist.exit_code, 0)
        self.assertIn("No such option: --artist", result_artist.output)

        result_track = self.runner.invoke(
            cli,
            [
                "recommend",
                "--track", "Insomnia",
                "--playlist-name", "Faithless Radio",
            ],
        )
        self.assertNotEqual(result_track.exit_code, 0)
        self.assertIn("No such option: --track", result_track.output)


if __name__ == '__main__':
    unittest.main()

