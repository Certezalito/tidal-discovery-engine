# Gemini AI Service Contract

## Function: `classify_tracks_genres`

Location: [`src/services/gemini_service.py`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/gemini_service.py)

### Input
- `api_key` (`str`): Google Gemini API Key.
- `tracks` (`list[dict]`): List of song dictionaries containing:
  - `artist`: `str`
  - `title`: `str`
  - `isrc`: `str | None`

### Prompt Structure
```text
I will provide a list of songs. 
For each song, identify:
1. Exactly ONE specific primary musical genre (e.g. 'Math Rock', 'Synthwave', 'Trip Hop').
2. Up to 3 specific sub-genres (e.g. 'Dance-Punk', 'Post-Punk Revival').

IMPORTANT RESTRICTIONS:
- DO NOT use broad umbrella genres (e.g. 'Rock', 'Pop', 'Alternative', 'Electronic', 'Music').
- DO NOT invent non-existent genres; use established standard sub-genres.
- Keep sub-genres focused and limited to at most 3 per track.

SONGS:
- Foals - Tron (ISRC: GBVKZ0725315)
...
```

### Structured Output Schema
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "isrc": { "type": ["string", "null"] },
      "title": { "type": ["string", "null"] },
      "artist": { "type": ["string", "null"] },
      "primary_genre": { "type": ["string", "null"] },
      "sub_genres": {
        "type": "array",
        "items": { "type": "string" }
      }
    },
    "required": ["primary_genre", "sub_genres"]
  }
}
```

### Return Value
`list[dict]`:
```python
[
  {
    "isrc": "GBVKZ0725315",
    "artist": "Foals",
    "title": "Tron",
    "primary_genre": "Math Rock",
    "sub_genres": ["Dance-Punk", "Post-Punk Revival", "Art Punk"]
  }
]
```
