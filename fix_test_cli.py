import re
with open('tests/test_cli.py', 'r') as f:
    data = f.read()

data = data.replace('min_genre_size=2', 'min_genre_size=5')
data = data.replace('min_genre_size\', 2), 2', 'min_genre_size\', 5), 5')
data = data.replace('--min-genre-size\', \'5\'', '--min-genre-size\', \'10\'')
data = data.replace('kwargs2[\'min_genre_size\'], 5', 'kwargs2[\'min_genre_size\'], 10')

with open('tests/test_cli.py', 'w') as f:
    f.write(data)
