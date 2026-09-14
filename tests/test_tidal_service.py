import unittest
from unittest.mock import MagicMock, patch
from src.services.tidal_service import (
    get_or_create_folder,
    create_playlist_in_folder,
    search_for_track,
    create_playlist,
    normalize_isrc,
    get_track_identity_key,
    build_favorites_snapshot,
    filter_out_favorites,
    FavoritesRetrievalError,
    get_playlists_in_folder,
    add_tracks_to_playlist,
    get_playlist_tracks,
    remove_tracks_from_playlist,
    search_tracks,
    resolve_text_seed_track,
    delete_playlist,
)
from requests.exceptions import HTTPError

class TestTidalServiceSearch(unittest.TestCase):
    def test_search_for_track_returns_first_track(self):
        mock_session = MagicMock()
        mock_track_input = MagicMock()
        mock_track_input.artist.name = "Artist"
        mock_track_input.title = "Title"
        
        mock_result_track = MagicMock()
        mock_session.search.return_value = {'tracks': [mock_result_track]}
        
        result = search_for_track(mock_session, mock_track_input)
        
        self.assertEqual(result, mock_result_track)
        
    def test_search_for_track_returns_none_if_empty(self):
        mock_session = MagicMock()
        mock_track_input = MagicMock()
        mock_track_input.artist.name = "Artist"
        mock_track_input.title = "Title"
        
        mock_session.search.return_value = {'tracks': []}
        
        result = search_for_track(mock_session, mock_track_input)
        
        self.assertIsNone(result)

    def test_search_tracks_v2_success(self):
        mock_session = MagicMock()
        mock_session.config.api_v2_location = "https://api.tidal.com/v2/"
        mock_session.parse_track.side_effect = lambda item: MagicMock(id=item["id"], title=item["title"])
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tracks": {
                "items": [{"id": 1234, "title": "Track Title"}]
            }
        }
        mock_session.request.request.return_value = mock_response

        tracks = search_tracks(mock_session, "Artist - Song", limit=5)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].id, 1234)
        mock_session.request.request.assert_called_once_with(
            "GET",
            "search",
            params={"query": "Artist - Song", "limit": 5},
            base_url="https://api.tidal.com/v2/",
        )

    def test_resolve_text_seed_track_exact_and_ambiguous_v2(self):
        mock_session = MagicMock()
        mock_session.config.api_v2_location = "https://api.tidal.com/v2/"

        track_exact = MagicMock()
        track_exact.name = "Exact Song"
        track_exact.title = "Exact Song"
        track_exact.artist = MagicMock()
        track_exact.artist.name = "Exact Artist"

        track_other = MagicMock()
        track_other.name = "Other Song"
        track_other.title = "Other Song"
        track_other.artist = MagicMock()
        track_other.artist.name = "Other Artist"

        # Exact match case
        mock_session.request.request.return_value.json.return_value = {
            "tracks": {"items": [{"id": 1, "title": "Exact Song"}]}
        }
        mock_session.parse_track.return_value = track_exact

        track, match_type = resolve_text_seed_track(mock_session, "Exact Artist", "Exact Song")
        self.assertEqual(match_type, "exact")
        self.assertEqual(track, track_exact)

        # Ambiguous match case
        mock_session.parse_track.return_value = track_other
        track, match_type = resolve_text_seed_track(mock_session, "Exact Artist", "Different Song")
        self.assertEqual(match_type, "ambiguous")
        self.assertEqual(track, track_other)

class TestTidalServiceFolders(unittest.TestCase):

    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_user = MagicMock()
        self.mock_session.user = self.mock_user
        self.mock_favorites = MagicMock()
        self.mock_user.favorites = self.mock_favorites

    def test_get_or_create_folder_exists_exact_match(self):
        # Setup
        folder_name = "My Mixes"
        mock_folder = MagicMock()
        mock_folder.name = "My Mixes"
        mock_folder.created = "2023-01-01"
        self.mock_favorites.playlist_folders.return_value = [mock_folder]

        # Execute
        result = get_or_create_folder(self.mock_session, folder_name)

        # Assert
        self.assertEqual(result, mock_folder)
        self.mock_favorites.playlist_folders.assert_called_once()
        self.mock_user.create_folder.assert_not_called()

    def test_get_or_create_folder_exists_case_insensitive(self):
        # Setup
        folder_name = "my mixes"
        mock_folder = MagicMock()
        mock_folder.name = "My Mixes"
        mock_folder.created = "2023-01-01"
        self.mock_favorites.playlist_folders.return_value = [mock_folder]

        # Execute
        result = get_or_create_folder(self.mock_session, folder_name)

        # Assert
        self.assertEqual(result, mock_folder)
        self.mock_favorites.playlist_folders.assert_called_once()
        self.mock_user.create_folder.assert_not_called()

    def test_get_or_create_folder_exists_multiple_returns_recent(self):
        # Setup
        folder_name = "My Mixes"
        mock_folder_old = MagicMock()
        mock_folder_old.name = "My Mixes"
        mock_folder_old.created = "2023-01-01"
        
        mock_folder_new = MagicMock()
        mock_folder_new.name = "My Mixes"
        mock_folder_new.created = "2023-02-01" # Newer

        self.mock_favorites.playlist_folders.return_value = [mock_folder_old, mock_folder_new]

        # Execute
        result = get_or_create_folder(self.mock_session, folder_name)

        # Assert
        self.assertEqual(result, mock_folder_new)

    def test_get_or_create_folder_creates_new(self):
        # Setup
        folder_name = "New Folder"
        self.mock_favorites.playlist_folders.return_value = []
        mock_new_folder = MagicMock()
        mock_new_folder.name = "New Folder"
        self.mock_user.create_folder.return_value = mock_new_folder

        # Execute
        result = get_or_create_folder(self.mock_session, folder_name)

        # Assert
        self.assertEqual(result, mock_new_folder)
        self.mock_user.create_folder.assert_called_with(folder_name)

    def test_get_or_create_folder_retry_on_transient_error(self):
        # Setup
        folder_name = "Retry Folder"
        self.mock_favorites.playlist_folders.return_value = []
        
        # Simulate failure then success
        mock_new_folder = MagicMock()
        self.mock_user.create_folder.side_effect = [HTTPError("503 Service Unavailable"), HTTPError("504 Gateway Timeout"), mock_new_folder]

        # Execute
        with patch('time.sleep'): # Speed up test
            result = get_or_create_folder(self.mock_session, folder_name)

        # Assert
        self.assertEqual(result, mock_new_folder)
        self.assertEqual(self.mock_user.create_folder.call_count, 3)

    @patch('src.services.tidal_service.time.sleep')
    def test_fetch_all_favorite_tracks_large_library(self, mock_sleep):
        """
        T025 [P] Add pagination/rate-limit boundary regression test for large libraries.
        Tests 5000+ tracks to ensure boundary limits are handled.
        """
        # Create 52 pages of 100 tracks to equal 5200 tracks
        def mock_tracks(offset, limit):
            if offset >= 5200:
                return []
            return [MagicMock() for _ in range(limit)]
            
        self.mock_user.favorites.tracks.side_effect = mock_tracks
        
        from src.services.tidal_service import fetch_all_favorite_tracks
        tracks, pages = fetch_all_favorite_tracks(self.mock_session, page_size=100)
        
        self.assertEqual(len(tracks), 5200)
        self.assertEqual(pages, 52)
        # Verify pagination called correct number of times (52 for data + 1 for empty)
        self.assertEqual(self.mock_user.favorites.tracks.call_count, 53)

    @patch('src.services.tidal_service.tidalapi.playlist.Folder')
    def test_create_playlist_in_folder_no_collision(self, params_mock_folder_class):
        # Setup
        folder_id = "folder-123"
        playlist_name = "My Playlist"
        track_ids = ["1", "2"]
        
        # Mock Folder instance
        mock_folder_instance = MagicMock()
        params_mock_folder_class.return_value = mock_folder_instance
        
        # Mock existing items (no collision)
        mock_existing_playlist = MagicMock()
        mock_existing_playlist.name = "Other Playlist"
        mock_folder_instance.items.return_value = [mock_existing_playlist]
        
        # Mock creation
        mock_new_playlist = MagicMock()
        self.mock_user.create_playlist.return_value = mock_new_playlist
        
        # Execute
        create_playlist_in_folder(self.mock_session, playlist_name, "Desc", folder_id, track_ids)
        
        # Assert
        # Should create with original name
        self.mock_user.create_playlist.assert_called_with(playlist_name, "Desc", parent_id=folder_id)
        # Should add tracks via v2 API
        self.mock_session.request.request.assert_called_with(
            "PUT",
            f"playlists/{mock_new_playlist.id}/items/add",
            params={"itemIds": "1,2"},
            base_url=self.mock_session.config.api_v2_location,
        )
        
    @patch('src.services.tidal_service.tidalapi.playlist.Folder')
    def test_create_playlist_in_folder_with_collision(self, params_mock_folder_class):
        # Setup
        folder_id = "folder-123"
        playlist_name = "My Playlist"
        track_ids = ["1"]
        
        # Mock Folder instance
        mock_folder_instance = MagicMock()
        params_mock_folder_class.return_value = mock_folder_instance
        
        # Mock existing items (collision)
        mock_existing_playlist = MagicMock()
        mock_existing_playlist.name = "My Playlist"
        mock_folder_instance.items.return_value = [mock_existing_playlist]
        
        # Mock creation
        mock_new_playlist = MagicMock()
        self.mock_user.create_playlist.return_value = mock_new_playlist
        
        # Execute
        create_playlist_in_folder(self.mock_session, playlist_name, "Desc", folder_id, track_ids)
        
        # Assert
        # Should create with appended counter
        self.mock_user.create_playlist.assert_called_with("My Playlist (1)", "Desc", parent_id=folder_id)

    @patch('src.services.tidal_service.tidalapi.playlist.Folder')
    def test_create_playlist_in_folder_multiple_collisions(self, params_mock_folder_class):
        # Setup
        folder_id = "folder-123"
        playlist_name = "My Playlist"
        track_ids = ["1"]
        
        # Mock Folder instance
        mock_folder_instance = MagicMock()
        params_mock_folder_class.return_value = mock_folder_instance
        
        # Mock existing items (multiple collisions)
        p1 = MagicMock()
        p1.name = "My Playlist"
        p2 = MagicMock()
        p2.name = "My Playlist (1)"
        mock_folder_instance.items.return_value = [p1, p2]
        
        mock_new_playlist = MagicMock()
        self.mock_user.create_playlist.return_value = mock_new_playlist
        
        # Execute
        create_playlist_in_folder(self.mock_session, playlist_name, "Desc", folder_id, track_ids)
        
        # Assert
        self.mock_user.create_playlist.assert_called_with("My Playlist (2)", "Desc", parent_id=folder_id)

    @patch('src.services.tidal_service.tidalapi.playlist.Folder')
    def test_create_playlist_in_folder_fallback_to_root(self, params_mock_folder_class):
        # Setup
        folder_id = "folder-123"
        
        # Mock Folder instance to exist so we get to creation
        mock_folder_instance = MagicMock()
        params_mock_folder_class.return_value = mock_folder_instance
        mock_folder_instance.items.return_value = []
        
        mock_new_playlist = MagicMock()
        
        def side_effect(name, description, parent_id):
            if parent_id == folder_id:
                mock_response = MagicMock()
                mock_response.status_code = 404
                raise HTTPError("404 Client Error: Not Found", response=mock_response)
            return mock_new_playlist
            
        self.mock_user.create_playlist.side_effect = side_effect
        
        # Execute
        with patch('time.sleep'):
            create_playlist_in_folder(self.mock_session, "Name", "Desc", folder_id, ["1"])
        
        # Assert
        # Verify it called with parent_id='root' eventually
        self.mock_user.create_playlist.assert_called_with("Name", "Desc", parent_id="root")


class TestTidalServicePlaylistDescription(unittest.TestCase):
    def test_create_playlist_description_uses_inserted_count_without_requested_phrase(self):
        mock_session = MagicMock()
        mock_playlist = MagicMock()
        mock_session.user.create_playlist.return_value = mock_playlist

        seed = MagicMock()
        seed.title = "Xpander"
        seed.artist.name = "Sasha"

        inserted_a = MagicMock()
        inserted_a.id = "1"
        inserted_b = MagicMock()
        inserted_b.id = "2"
        inserted_c = MagicMock()
        inserted_c.id = "3"

        create_playlist(
            session=mock_session,
            name="My Playlist",
            num_tidal_tracks=1,
            num_similar_tracks=500,
            seed_tracks=[seed],
            final_tags=[],
            tracks=[inserted_a, inserted_b, inserted_c],
        )

        args, _ = mock_session.user.create_playlist.call_args
        description = args[1]

        self.assertIn("Inserted 3 tracks into this playlist.", description)
        self.assertNotIn("Requested up to 500 recommendations.", description)
        self.assertNotIn("Found 500 similar tracks for each via Last.fm.", description)


class TestTidalServiceExclusion(unittest.TestCase):
    def _track(self, title, artist, isrc=None):
        track = MagicMock()
        track.title = title
        track.name = title
        track.artist.name = artist
        track.isrc = isrc
        return track

    def test_normalize_isrc_removes_noise_and_uppercases(self):
        self.assertEqual(normalize_isrc(" us-a1b-23 00001 "), "USA1B2300001")

    def test_identity_key_prefers_isrc(self):
        track = self._track("Track", "Artist", isrc="us-a1b-23 00001")
        self.assertEqual(get_track_identity_key(track), "isrc:USA1B2300001")

    def test_identity_key_falls_back_to_title_artist(self):
        track = self._track(" Teardrop ", " Massive Attack ", isrc=None)
        self.assertEqual(get_track_identity_key(track), "fallback:teardrop|massive attack")

    def test_build_favorites_snapshot_collects_identity_keys(self):
        session = MagicMock()
        page_1 = [self._track("Track A", "Artist A", isrc="USAAA00001")]
        page_2 = [self._track("Track B", "Artist B", isrc=None)]
        session.user.favorites.tracks.side_effect = [page_1, page_2, []]

        snapshot = build_favorites_snapshot(session, page_size=100, max_page_retries=2)

        self.assertTrue(snapshot["load_complete"])
        self.assertEqual(snapshot["total_favorites"], 2)
        self.assertEqual(snapshot["pages_loaded"], 2)
        self.assertIn("isrc:USAAA00001", snapshot["identity_keys"])
        self.assertIn("fallback:track b|artist b", snapshot["identity_keys"])

    @patch("src.services.tidal_service.time.sleep")
    def test_build_favorites_snapshot_retries_transient_page_errors(self, mock_sleep):
        session = MagicMock()
        good_page = [self._track("Track A", "Artist A", isrc="USAAA00001")]
        session.user.favorites.tracks.side_effect = [
            HTTPError("503"),
            good_page,
            [],
        ]

        snapshot = build_favorites_snapshot(session, page_size=100, max_page_retries=2)

        self.assertEqual(snapshot["total_favorites"], 1)
        self.assertEqual(session.user.favorites.tracks.call_count, 3)

    @patch("src.services.tidal_service.time.sleep")
    def test_build_favorites_snapshot_fails_closed_after_retry_exhaustion(self, mock_sleep):
        session = MagicMock()
        session.user.favorites.tracks.side_effect = HTTPError("503")

        with self.assertRaises(FavoritesRetrievalError):
            build_favorites_snapshot(session, page_size=100, max_page_retries=2)

    def test_filter_out_favorites_excludes_matching_tracks(self):
        candidates = [
            self._track("Track A", "Artist A", isrc="USAAA00001"),
            self._track("Track B", "Artist B", isrc=None),
        ]
        favorite_keys = {"isrc:USAAA00001"}

        filtered, excluded = filter_out_favorites(candidates, favorite_keys)

        self.assertEqual(excluded, 1)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "Track B")


class TestTidalServiceGetPlaylistsInFolder(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.config.api_v2_location = "https://api.tidal.com/v2"

    @patch("src.services.tidal_service.time.sleep")
    def test_get_playlists_in_folder_retries_transient_504(self, mock_sleep):
        mock_response_504 = MagicMock()
        mock_response_504.status_code = 504
        error_504 = HTTPError("504 Server Error: Gateway Time-out", response=mock_response_504)

        good_response = MagicMock()
        good_response.json.return_value = {
            "items": [{"data": {"title": "Rock", "id": "pl-1"}}],
            "cursor": None,
        }

        self.mock_session.request.request.side_effect = [error_504, good_response]
        self.mock_session.request.map_json.side_effect = lambda d, parse: [MagicMock(name=x["title"]) for x in d["items"]]

        result = get_playlists_in_folder(self.mock_session, "folder-123", max_retries=3, retry_delay=1)

        self.assertEqual(len(result), 1)
        self.assertEqual(self.mock_session.request.request.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("src.services.tidal_service.time.sleep")
    def test_get_playlists_in_folder_fails_closed_after_retries_exhausted(self, mock_sleep):
        mock_response_504 = MagicMock()
        mock_response_504.status_code = 504
        error_504 = HTTPError("504 Server Error: Gateway Time-out", response=mock_response_504)

        self.mock_session.request.request.side_effect = error_504

        with self.assertRaises(HTTPError):
            get_playlists_in_folder(self.mock_session, "folder-123", max_retries=2, retry_delay=1)

        self.assertEqual(self.mock_session.request.request.call_count, 3)

    def test_get_playlists_in_folder_returns_empty_on_404(self):
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        error_404 = HTTPError("404 Client Error: Not Found", response=mock_response_404)

        self.mock_session.request.request.side_effect = error_404

        result = get_playlists_in_folder(self.mock_session, "missing-folder")
        self.assertEqual(result, [])


class TestAddTracksToPlaylist(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.config.api_v2_location = "https://api.tidal.com/v2/"

    def test_add_tracks_to_playlist_success(self):
        result = add_tracks_to_playlist(self.mock_session, "playlist-1", ["101", "102"])
        self.assertTrue(result)
        self.mock_session.request.request.assert_called_once_with(
            "PUT",
            "playlists/playlist-1/items/add",
            params={"itemIds": "101,102"},
            base_url="https://api.tidal.com/v2/",
        )

    def test_add_tracks_to_playlist_empty_list(self):
        result = add_tracks_to_playlist(self.mock_session, "playlist-1", [])
        self.assertTrue(result)
        self.mock_session.request.request.assert_not_called()

    def test_add_tracks_to_playlist_chunking(self):
        track_ids = [str(i) for i in range(75)]
        result = add_tracks_to_playlist(self.mock_session, "playlist-1", track_ids, chunk_size=50)
        self.assertTrue(result)
        self.assertEqual(self.mock_session.request.request.call_count, 2)
        
        # Verify first chunk has 50 items
        first_call = self.mock_session.request.request.call_args_list[0]
        self.assertEqual(first_call.kwargs["params"]["itemIds"], ",".join(track_ids[:50]))

        # Verify second chunk has 25 items
        second_call = self.mock_session.request.request.call_args_list[1]
        self.assertEqual(second_call.kwargs["params"]["itemIds"], ",".join(track_ids[50:]))

    @patch("src.services.tidal_service.time.sleep")
    def test_add_tracks_to_playlist_retry_on_504(self, mock_sleep):
        mock_response_504 = MagicMock()
        mock_response_504.status_code = 504
        error_504 = HTTPError("504 Server Error", response=mock_response_504)
        
        self.mock_session.request.request.side_effect = [error_504, MagicMock()]
        result = add_tracks_to_playlist(self.mock_session, "playlist-1", ["101"], max_retries=2, retry_delay=1)
        self.assertTrue(result)
        self.assertEqual(self.mock_session.request.request.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    def test_add_tracks_to_playlist_raises_on_400_without_retry(self):
        mock_response_400 = MagicMock()
        mock_response_400.status_code = 400
        error_400 = HTTPError("400 Bad Request", response=mock_response_400)
        
        self.mock_session.request.request.side_effect = error_400
        with self.assertRaises(HTTPError):
            add_tracks_to_playlist(self.mock_session, "playlist-1", ["101"], max_retries=2)
        # Should not retry 4xx errors
        self.assertEqual(self.mock_session.request.request.call_count, 1)

    @patch('src.services.tidal_service.tidalapi.playlist.Folder')
    def test_create_playlist_in_folder_v2_fallback_to_playlist_add(self, mock_folder_cls):
        mock_folder = MagicMock()
        mock_folder.items.return_value = []
        mock_folder_cls.return_value = mock_folder

        mock_new_playlist = MagicMock()
        self.mock_session.user.create_playlist.return_value = mock_new_playlist
        
        # When v2 request fails, it should fall back to playlist.add
        self.mock_session.request.request.side_effect = Exception("V2 failure")

        playlist = create_playlist_in_folder(self.mock_session, "FallBack Playlist", "Desc", "folder-1", ["101", "102"])
        self.assertEqual(playlist, mock_new_playlist)
        mock_new_playlist.add.assert_called_once_with(["101", "102"])


class TestGetPlaylistTracks(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.config.api_v2_location = "https://api.tidal.com/v2/"
        self.mock_session.locale = "en_US"
        self.mock_session.parse_track.side_effect = lambda item: MagicMock(
            id=item["id"],
            title=item.get("title", "Song"),
            artist=MagicMock(name=item.get("artists", [{}])[0].get("name", "Artist")),
        )

    def test_get_playlist_tracks_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [
                {"id": "uuid-1", "item": {"id": 101, "title": "Track 1"}},
                {"id": "uuid-2", "item": {"id": 102, "title": "Track 2"}},
            ],
            "cursor": None,
        }
        self.mock_session.request.request.return_value = mock_response

        tracks = get_playlist_tracks(self.mock_session, "pl-1")
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0].id, 101)
        self.assertEqual(tracks[0].item_uuid, "uuid-1")
        self.assertEqual(tracks[1].id, 102)
        self.assertEqual(tracks[1].item_uuid, "uuid-2")
        self.mock_session.request.request.assert_called_once_with(
            "GET",
            "playlists/pl-1/items",
            params={"locale": "en_US", "limit": 100},
            base_url="https://api.tidal.com/v2/",
        )

    def test_get_playlist_tracks_pagination(self):
        page1 = MagicMock()
        page1.json.return_value = {
            "content": [{"id": "uuid-1", "item": {"id": 101}}],
            "cursor": "cursor-token-123",
        }
        page2 = MagicMock()
        page2.json.return_value = {
            "content": [{"id": "uuid-2", "item": {"id": 102}}],
            "cursor": None,
        }
        self.mock_session.request.request.side_effect = [page1, page2]

        tracks = get_playlist_tracks(self.mock_session, "pl-1")
        self.assertEqual(len(tracks), 2)
        self.assertEqual(self.mock_session.request.request.call_count, 2)
        second_call = self.mock_session.request.request.call_args_list[1]
        self.assertEqual(second_call.kwargs["params"]["cursor"], "cursor-token-123")

    @patch("src.services.tidal_service.time.sleep")
    def test_get_playlist_tracks_retry_on_504(self, mock_sleep):
        mock_resp_504 = MagicMock()
        mock_resp_504.status_code = 504
        error_504 = HTTPError("504 Server Error", response=mock_resp_504)

        good_page = MagicMock()
        good_page.json.return_value = {
            "content": [{"id": "uuid-1", "item": {"id": 101}}],
            "cursor": None,
        }
        self.mock_session.request.request.side_effect = [error_504, good_page]

        tracks = get_playlist_tracks(self.mock_session, "pl-1", max_retries=2, retry_delay=1)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(self.mock_session.request.request.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    def test_get_playlist_tracks_404_returns_none(self):
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        error_404 = HTTPError("404 Not Found", response=mock_resp_404)
        self.mock_session.request.request.side_effect = error_404

        result = get_playlist_tracks(self.mock_session, "missing-pl")
        self.assertIsNone(result)

    def test_get_playlist_tracks_empty_playlist(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [], "cursor": None}
        self.mock_session.request.request.return_value = mock_response

        tracks = get_playlist_tracks(self.mock_session, "empty-pl")
        self.assertEqual(tracks, [])


class TestRemoveTracksFromPlaylist(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.config.api_v2_location = "https://api.tidal.com/v2/"

    def test_remove_tracks_with_item_uuids(self):
        uuids = ["393177c9-3ef0-4943-8226-e6ab64230851", "72800665-fec4-4825-a58c-c0a196c02cc7"]
        result = remove_tracks_from_playlist(self.mock_session, "pl-1", uuids)
        self.assertTrue(result)
        self.mock_session.request.request.assert_called_once_with(
            "PUT",
            "playlists/pl-1/items/remove",
            params={"itemUuids": ",".join(uuids)},
            base_url="https://api.tidal.com/v2/",
        )

    @patch("src.services.tidal_service.get_playlist_tracks")
    def test_remove_tracks_with_track_ids_resolves_uuids(self, mock_get_tracks):
        mock_t1 = MagicMock(id=101, item_uuid="uuid-101")
        mock_t2 = MagicMock(id=102, item_uuid="uuid-102")
        mock_t3 = MagicMock(id=103, item_uuid="uuid-103")
        mock_get_tracks.return_value = [mock_t1, mock_t2, mock_t3]

        result = remove_tracks_from_playlist(self.mock_session, "pl-1", [101, 103])
        self.assertTrue(result)
        self.mock_session.request.request.assert_called_once_with(
            "PUT",
            "playlists/pl-1/items/remove",
            params={"itemUuids": "uuid-101,uuid-103"},
            base_url="https://api.tidal.com/v2/",
        )

    def test_remove_tracks_empty_list(self):
        result = remove_tracks_from_playlist(self.mock_session, "pl-1", [])
        self.assertTrue(result)
        self.mock_session.request.request.assert_not_called()

    def test_remove_tracks_chunking(self):
        uuids = [f"00000000-0000-0000-0000-{i:012d}" for i in range(75)]
        result = remove_tracks_from_playlist(self.mock_session, "pl-1", uuids, chunk_size=50)
        self.assertTrue(result)
        self.assertEqual(self.mock_session.request.request.call_count, 2)

    @patch("src.services.tidal_service.time.sleep")
    def test_remove_tracks_retry_on_504(self, mock_sleep):
        mock_resp_504 = MagicMock()
        mock_resp_504.status_code = 504
        error_504 = HTTPError("504 Server Error", response=mock_resp_504)

        uuids = ["393177c9-3ef0-4943-8226-e6ab64230851"]
        self.mock_session.request.request.side_effect = [error_504, MagicMock()]

        result = remove_tracks_from_playlist(self.mock_session, "pl-1", uuids, max_retries=2, retry_delay=1)
        self.assertTrue(result)
        self.assertEqual(self.mock_session.request.request.call_count, 2)
        mock_sleep.assert_called_once_with(1)


class TestDeletePlaylist(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.config.api_v2_location = "https://api.tidal.com/v2/"

    def test_delete_playlist_v2_success(self):
        self.mock_session.request.request.return_value = MagicMock(status_code=204)
        result = delete_playlist(self.mock_session, "pl-to-delete")
        self.assertTrue(result)
        self.mock_session.request.request.assert_called_once_with(
            "PUT",
            "my-collection/playlists/folders/remove",
            params={"trns": "trn:playlist:pl-to-delete"},
            base_url="https://api.tidal.com/v2/",
        )

    def test_delete_playlist_v2_404_handled_gracefully(self):
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        self.mock_session.request.request.side_effect = HTTPError("404 Not Found", response=mock_resp_404)

        result = delete_playlist(self.mock_session, "nonexistent-pl")
        self.assertTrue(result)

    @patch("src.services.tidal_service.tidalapi.playlist.UserPlaylist")
    def test_delete_playlist_falls_back_to_legacy(self, mock_user_pl_cls):
        self.mock_session.request.request.side_effect = Exception("v2 down")
        mock_pl_inst = MagicMock()
        mock_user_pl_cls.return_value = mock_pl_inst

        result = delete_playlist(self.mock_session, "pl-fallback", max_retries=0)
        self.assertTrue(result)
        mock_user_pl_cls.assert_called_once_with(self.mock_session, "pl-fallback")
        mock_pl_inst.delete.assert_called_once()


if __name__ == '__main__':
    unittest.main()
