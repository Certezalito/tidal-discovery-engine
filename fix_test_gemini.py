import re
with open('tests/test_gemini_service.py', 'r') as f:
    data = f.read()

data = data.replace('genres=["Rock", "Pop"]', 'genre="Rock"')
data = data.replace('genres=[]', 'genre=None')
data = data.replace('results[0]["genres"]', 'results[0]["genre"]')
data = data.replace('results[1]["genres"]', 'results[1]["genre"]')
data = data.replace('["Rock", "Pop"]', '"Rock"')
data = data.replace('[]', 'None')
data = data.replace('genres=["Electronic"]', 'genre="Electronic"')
data = data.replace('genres=["Metal", "Hard Rock"]', 'genre="Metal"')
data = data.replace('genres=["Classical"]', 'genre="Classical"')
data = data.replace('set(result["genres"])', 'set([result["genre"]] if result.get("genre") else [])')

with open('tests/test_gemini_service.py', 'w') as f:
    f.write(data)
