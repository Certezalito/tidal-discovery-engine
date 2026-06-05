import re
with open('tests/test_exclude_favorites.py', 'r') as f:
    data = f.read()

data = data.replace('main,\n                    [\n                        "--playlist-name",', 'main,\n                    [\n                        "recommend",\n                        "--playlist-name",')
with open('tests/test_exclude_favorites.py', 'w') as f:
    f.write(data)
