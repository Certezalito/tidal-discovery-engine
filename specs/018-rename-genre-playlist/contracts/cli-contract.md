# CLI Contract: Genre Organizer (`organize`, `genre-organizer`, `genre-playlist`)

**Feature**: `specs/018-rename-genre-playlist/spec.md`  
**Branch**: `018-rename-genre-playlist`  
**Date**: 2026-09-10  

## 1. Primary Command: `organize`

### Synopsis
```bash
python -m src.cli.main organize [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--folder` | TEXT | `"Genres"` | Destination folder name for genre playlists on Tidal. |
| `--min-genre-size` | INTEGER | `10` | Minimum track count for a dedicated genre playlist. Genres with fewer tracks are pooled in "Others". |
| `--db-path` | PATH | `"data/genre_cache.db"` | Path to the SQLite persistent database cache file. |
| `--help` | FLAG | - | Show help message and exit. |

### Environment Variables
- `GEMINI_API_KEY`: Required. Checked prior to synchronization. If missing, exits with code 1.

### Exit Codes
- `0`: Synchronization completed successfully.
- `1`: Validation error, missing API key, or unhandled exception.

### Standard Output Example
```text
Starting genre organizer sync in folder 'Genres' with min genre size 10...
Genre organizer sync complete.

--- Genre Organizer Sync Summary ---
Library Tracks Scanned: 150
Database Cache Hits:    120
Gemini API Queries:     30
Playlists Created:      5
Playlists Updated:      2
Playlists Deleted:      0
Token Cost Reduction:   80.0%
Tracks Added:           35
Tracks Removed:         0
------------------------------------
```

---

## 2. Supported Alias: `genre-organizer`

### Synopsis
```bash
python -m src.cli.main genre-organizer [OPTIONS]
```

### Specification
- Shares identical options (`--folder`, `--min-genre-size`, `--db-path`), default values, environment variable requirements, exit codes, and output formats as the primary `organize` command.
- Listed in top-level `--help` alongside `organize`.

---

## 3. Legacy Interception Stub: `genre-playlist`

### Synopsis
```bash
python -m src.cli.main genre-playlist [ANY...]
```

### Specification
- **Hidden**: Marked with `hidden=True` in Click; MUST NOT appear in `python -m src.cli.main --help`.
- **Permissive Argument Parsing**: Accepts any arguments or options without raising unknown-option errors before invocation.
- **Exit Code**: `1` (via `click.ClickException`).
- **Standard Error / Output**:
```text
Error: 'genre-playlist' was renamed to 'organize' (alias: 'genre-organizer').
```

---

## 4. Top-Level Help Output Contract

Executing `python -m src.cli.main --help` MUST produce command listings containing:

```text
Commands:
  genre-organizer  Reads the full Tidal library, categorizes tracks by...
  organize         Reads the full Tidal library, categorizes tracks by...
  radio            Generate a Tidal playlist with Last.fm...
  recommend        Generate a Tidal playlist from top Last.fm recommendations...
```

`genre-playlist` MUST NOT appear anywhere in the output.
