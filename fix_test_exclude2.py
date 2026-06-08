import re
with open('tests/test_exclude_favorites.py', 'r') as f:
    data = f.read()

data = data.replace('self.runner.invoke(main, [', 'self.runner.invoke(main, [\'recommend\', ')
data = data.replace('self.runner.invoke(\n            main,\n            [', 'self.runner.invoke(\n            main,\n            [\'recommend\', ')
with open('tests/test_exclude_favorites.py', 'w') as f:
    f.write(data)
