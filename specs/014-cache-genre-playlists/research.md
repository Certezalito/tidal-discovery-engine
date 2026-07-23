# Research: Genre Playlist Database Caching & Optimization

## Phase 0 Findings

### Decision 1: SQLite Database Engine & Schema Strategy

- **Decision**: Use Python's built-in `sqlite3` module with an embedded SQLite database file (e.g., `data/genre_cache.db` or configured path) to store track genre classifications.
- **Rationale**: SQLite requires no external server setup, runs natively in Python 3.12+, supports fast indexing on track IDs/ISRCs, and guarantees persistence across periodic runs.
- **Schema Design**:
  - `track_genre_cache` table:
    - `track_id` (TEXT PRIMARY KEY) - Tidal Track ID / ISRC
    - `artist` (TEXT)
    - `title` (TEXT)
    - `primary_genre` (TEXT) - Primary single best-fit genre
    - `status` (TEXT) - `'CLASSIFIED'` or `'UNKNOWN'`
    - `updated_at` (TIMESTAMP)
- **Alternatives Considered**:
  - JSON file cache: Heavy performance degradation and file write risks with thousands of tracks; prone to corrupt writes if interrupted.
  - Redis / external DB: Violates the minimal setup principle and adds unnecessary infrastructure dependencies for a local CLI app.

---

### Decision 2: Cache Query & Gemini Re-Evaluation Strategy

- **Decision**:
  1. For each library track, perform a fast batch primary key lookup in SQLite.
  2. If present and `status == 'CLASSIFIED'`, hit cache (0 Gemini token cost).
  3. If missing OR `status == 'UNKNOWN'`, collect track for Gemini batch request.
  4. Upon receiving Gemini response, upsert result into SQLite with `status = 'CLASSIFIED'` or `status = 'UNKNOWN'`.
- **Rationale**: Re-querying Gemini for missing/unknown tracks allows future runs to resolve tracks when Gemini's metadata improves, while 100% avoiding AI calls for previously classified tracks.
- **Alternatives Considered**:
  - Permanent cache for "Unknown": Locks unidentified tracks forever into "Unknown".
  - Expiration-based cache invalidation: Causes unnecessary re-queries for static track metadata.

---

### Decision 3: Genre Thresholding (`--min-genre-size`) & "Others" Grouping

- **Decision**:
  1. Group all library tracks by their `primary_genre`.
  2. Separate genres with track count `>= min_genre_size` (default 5) from those `< min_genre_size`.
  3. Combine all tracks from genres `< min_genre_size` into a single "Others" genre playlist bucket.
  4. Ensure every track belongs to strictly 1 bucket ("Named Genre", "Others", or "Unknown").
- **Rationale**: Solves Tidal folder sprawl and keeps playlists organized into actionable groupings.

---

### Decision 4: Idempotent Tidal Folder Sync & Update Ordering

- **Decision**:
  1. Fetch existing playlists within target Tidal folder.
  2. Compare current target track lists with desired genre playlist contents.
  3. Perform diff-based sync: add missing tracks, remove deleted tracks.
  4. Delete or empty playlists in Tidal whose genre track count dropped to 0.
  5. Execute updates in ascending order of track count (smallest playlist first, largest last) so Tidal client's "Updated Date" sorting lists the largest playlists at the top.
- **Rationale**: Guarantees zero duplicate tracks, maintains folder cleanliness, and aligns with Tidal UI sorting behavior.
