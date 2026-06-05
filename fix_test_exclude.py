import re
with open('tests/test_exclude_favorites.py', 'r') as f:
    data = f.read()

data = data.replace('from src.cli.main import main', 'from src.cli.main import cli as main')
with open('tests/test_exclude_favorites.py', 'w') as f:
    f.write(data)
