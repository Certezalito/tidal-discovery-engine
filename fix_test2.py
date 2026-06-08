import re
with open('tests/test_cli.py', 'r') as f:
    lines = f.readlines()
with open('tests/test_cli.py', 'w') as f:
    for line in lines:
        if 'main,' in line and 'runner.invoke' not in line:
            f.write(line.replace('main,', 'cli,'))
        elif 'main(' in line:
            f.write(line.replace('main(', 'cli('))
        else:
            f.write(line.replace('result = self.runner.invoke(main', 'result = self.runner.invoke(cli'))
