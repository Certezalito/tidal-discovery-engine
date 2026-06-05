with open('tests/test_cli.py', 'r') as f:
    data = f.read()

data = data.replace('main,\n            [\'recommend\',\n\'--gemini', 'cli,\n            [\'recommend\', \'--gemini')
data = data.replace("self.runner.invoke(main, ['--playlist-name'", "self.runner.invoke(cli, ['recommend', '--playlist-name'")
with open('tests/test_cli.py', 'w') as f:
    f.write(data)
