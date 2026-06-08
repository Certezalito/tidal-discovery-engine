with open('src/services/gemini_service.py', 'r') as f:
    data = f.read()
data = data.replace("'genres'", "'genre'")
data = data.replace("A song can have multiple genres if appropriate. ", "Select exactly ONE best-match genre for each song. ")
with open('src/services/gemini_service.py', 'w') as f:
    f.write(data)
