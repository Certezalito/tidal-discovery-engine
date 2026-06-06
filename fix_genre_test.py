import re
with open('tests/test_genre_playlist_service.py', 'r') as f:
    data = f.read()

data = data.replace('return [{"genres": ["Rock"]} for _ in batch]', 'return [{"genre": "Rock"} for _ in batch]')

with open('tests/test_genre_playlist_service.py', 'w') as f:
    f.write(data)
