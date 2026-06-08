with open('tests/test_cli.py', 'r') as f:
    data = f.read()

data = data.replace("mock_run_sync.assert_called_with(mock_get_session.return_value, 'My Custom Genres')", "mock_run_sync.assert_called_with(mock_get_session.return_value, 'My Custom Genres', min_genre_size=2)")
data = data.replace("mock_run_sync.assert_called_with(mock_get_session.return_value, 'Genres')", "mock_run_sync.assert_called_with(mock_get_session.return_value, 'Genres', min_genre_size=2)")

with open('tests/test_cli.py', 'w') as f:
    f.write(data)
