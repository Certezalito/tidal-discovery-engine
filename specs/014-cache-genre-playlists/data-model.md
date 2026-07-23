# Data Model: Genre Playlist Database Caching & Optimization

## Entities & Schemas

```mermaid
erDiagram
    TrackGenreCache {
        string track_id PK "Tidal Track ID or ISRC"
        string artist "Track Artist"
        string title "Track Title"
        string primary_genre "Primary Best-Fit Genre"
        string status "CLASSIFIED or UNKNOWN"
        datetime updated_at "Timestamp of last lookup"
    }

    GenreAssignment {
        string track_id "Tidal Track ID"
        string assigned_playlist_name "Genre Name, 'Others', or 'Unknown'"
    }

    TidalPlaylistFolder {
        string folder_id "Tidal Folder ID"
        string folder_name "Folder Name"
    }

    GenrePlaylist {
        string playlist_id "Tidal Playlist ID"
        string playlist_name "Genre / Bucket Name"
        string folder_id FK "Tidal Folder ID"
        int track_count "Total assigned tracks"
    }

    TrackGenreCache ||--o| GenreAssignment : "provides genre"
    GenreAssignment }|--|| GenrePlaylist : "grouped into"
    GenrePlaylist }|--|| TidalPlaylistFolder : "nested within"
```

### Table Schema: `track_genre_cache` (SQLite)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `track_id` | TEXT | PRIMARY KEY | Unique identifier for track (Tidal Track ID or ISRC) |
| `artist` | TEXT | NOT NULL | Artist name |
| `title` | TEXT | NOT NULL | Track title |
| `primary_genre` | TEXT | NOT NULL | Best-fit primary genre name |
| `status` | TEXT | NOT NULL | Classification state: `'CLASSIFIED'` or `'UNKNOWN'` |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last cache insert/update timestamp |

### State Transitions

```mermaid
stateDiagram-v2
    [*] --> Uncached : New Library Track
    Uncached --> QueryGemini : Batch Cache Miss
    QueryGemini --> Classified : Gemini returns valid genre
    QueryGemini --> Unknown : Gemini returns no/ambiguous genre

    CachedUnknown --> QueryGemini : Subsequent run re-evaluation
    Classified --> CachedClassified : Direct Cache Hit (0 AI tokens)

    CachedClassified --> GenreGrouping : Map to Primary Genre
    GenreGrouping --> NamedGenrePlaylist : Track count >= threshold
    GenreGrouping --> OthersPlaylist : Track count < threshold
```
