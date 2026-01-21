import unittest
from unittest.mock import MagicMock, patch
from src.services.tidal_service import get_or_create_folder, create_playlist_in_folder, search_for_track
from tidalapi.exceptions import ObjectNotFound
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
        with patch('time.sleep') as mock_sleep: # Speed up test
            result = get_or_create_folder(self.mock_session, folder_name)

        # Assert
        self.assertEqual(result, mock_new_folder)
        self.assertEqual(self.mock_user.create_folder.call_count, 3)

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
        result = create_playlist_in_folder(self.mock_session, playlist_name, "Desc", folder_id, track_ids)
        
        # Assert
        # Should create with original name
        self.mock_user.create_playlist.assert_called_with(playlist_name, "Desc", parent_id=folder_id)
        # Should add tracks
        mock_new_playlist.add.assert_called_with(track_ids)
        
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
        p1 = MagicMock(); p1.name = "My Playlist"
        p2 = MagicMock(); p2.name = "My Playlist (1)"
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
        with patch('time.sleep') as mock_sleep:
            create_playlist_in_folder(self.mock_session, "Name", "Desc", folder_id, ["1"])
        
        # Assert
        # Verify it called with parent_id='root' eventually
        self.mock_user.create_playlist.assert_called_with("Name", "Desc", parent_id="root")

if __name__ == '__main__':
    unittest.main()
