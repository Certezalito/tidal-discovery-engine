# Tidal Discovery Engine

A command-line tool that generates Tidal playlists with recommended tracks using Last.fm similarity data or Google Gemini AI, seeded from your favorite tracks or a specific song.

## Setup

1. Clone the repository:

    ```bash
    git clone https://github.com/Certezalito/tidal-discovery-engine.git && cd tidal-discovery-engine
    ```

2. Create a virtual environment (Python 3.12+) and install dependencies:

    ```bash
    uv venv && uv pip install -e .
    ```

3. Create a `.env` file in the project root with your API keys:

    ```
    LASTFM_API_KEY=your_lastfm_api_key
    GEMINI_API_KEY=your_gemini_api_key
    GEMINI_MODEL=
    GEMINI_FALLBACK_MODEL=
    ```

    - Get a Last.fm API key from the [Last.fm API account page](https://www.last.fm/api/account/create).
    - Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Required only if you use `--gemini`.
    - `GEMINI_MODEL` is optional. Resolution order: exported environment variable → `.env` value → built-in default (`gemini-flash-latest`). Setting to `latest` or leaving blank automatically uses Google's latest Flash model.
    - `GEMINI_FALLBACK_MODEL` is optional. Used only when the primary model is unavailable or not found.

4. Run the script once interactively to authenticate with Tidal:

    ```bash
    uv run python -m src.cli.main recommend
    ```

    This creates a `tidal_session.json` file in the project root, which is reused for all future non-interactive runs.

## Commands

The CLI supports three commands: `recommend`, `radio`, and `organize` (alias: `genre-organizer`). Each command has its own set of options.

### `recommend`

Uses Last.fm OR Gemini depending on your configuration (defaults to Last.fm):

**Quick start** — generate a playlist based on your Tidal favorites using Last.fm recommendations:

```bash
uv run python -m src.cli.main recommend
```

#### Variations on `recommend` 

#### `--exclude-favorites`

To exclude tracks you already saved in Tidal favorites from the resulting playlist:

```bash
uv run python -m src.cli.main recommend --playlist-name "TDE {date}" --exclude-favorites
```
#### `--shuffle`

Randomizes the selection of tracks by pulling a larger pool and picking from the pool.  Think of it as pulling "Deeper cuts." 

```bash
uv run python -m src.cli.main recommend --shuffle --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}" --folder "Tidal Discovery Engine"
```

#### `--gemini` require Gemini API key in `.env` 

Uses Google Gemini AI instead of Last.fm to generate recommendations. 

```bash
uv run python -m src.cli.main recommend --gemini --playlist-name "TDE Gemini Hits" --folder "Tidal Discovery Engine"
```


### `radio`

Generates a dedicated track radio playlist seeded with a specific song. The seed track is placed at **Track #1** on Tidal, followed by recommendations up to the requested total count (default **50 tracks**: 1 seed + 49 recommendations).

**Quick start** — generate a track radio playlist:

```bash
uv run python -m src.cli.main radio --artist "Matt Darey" --track "Gamemaster" --playlist-name "Gamemaster Vibes {date}"
```

Expected outcome:
- Playlist named `"Gamemaster Vibes %today's date%"` containing 50 tracks total.
- Track #1 is `"Gamemaster"` by Matt Darey.
- Tracks #2–#50 are 49 recommendations from Last.fm.
- Playlist description includes seed metadata: `"Seed track: Gamemaster by Matt Darey • Total tracks: 50"`.
- Playlist is organized inside the `"Radio"` folder on Tidal by default.

#### Variations on `radio` 

#### `--gemini` Gemini AI Recommendations, require Gemini API key in `.env` 

Use Google Gemini AI instead of Last.fm for recommendations:

```bash
uv run python -m src.cli.main radio --artist "Burial" --track "Archangel" --gemini
```

- **Graceful fallback**: If the configured Gemini model is unavailable, the command automatically falls back to Last.fm recommendations with a warning.

#### `--shuffle` 

Deeper cuts are returned

```bash
uv run python -m src.cli.main radio --artist "Burial" --track "Archangel" --gemini --shuffle
```



### `organize` (alias: `genre-organizer`)

Requires `GEMINI_API_KEY` in `.env`.

> ⚠️ **TOKEN CONSUMPTION WARNING**: The `organize` command is an **expensive command token-wise** because Gemini analyzes and classifies every single track across your Tidal library. To prevent recurring API costs, a local SQLite database cache (default: `data/genre_cache.db`) is automatically created and maintained. Subsequent runs reuse cached classifications with zero Gemini token cost.

> ⚠️ **DESTRUCTIVE OPERATION**: The `organize` command strictly owns the folder it targets. **Any playlists in the target folder that do not match the expected generated genres (including manually created playlists) will be permanently deleted.** Do not point this command at a folder containing your personally created playlists. 

Reads your entire Tidal library, uses Gemini to classify each track by genre, and creates or syncs one playlist per genre inside a dedicated folder. This mode helps you organize your entire library automatically.

**First Run & Syncing** — organize your library into a folder named "Genres" (the default folder name) with the default minimum genre size (5 tracks, any genre without 5 tracks will be discard to prevent playlist sprawl):

```bash
uv run python -m src.cli.main organize
```


**Custom Folder, Threshold & Database Path** — organize into a specific folder, set a custom threshold (e.g. 10 tracks, overriding the default of 5), and specify a custom SQLite database cache file:

```bash
uv run python -m src.cli.main organize --folder "My Music Styles" --min-genre-size 10 --db-path "data/genre_cache.db"
```

**Clean-Slate Folder Wipe & Re-Sync** — delete all existing playlists inside the destination folder and build fresh playlists:

```bash
uv run python -m src.cli.main organize --wipe-folder
# or using the short alias:
uv run python -m src.cli.main organize --wipe
```

**Empty Folder & Exit (Wipe-Only)** — delete all playlists inside the target folder and terminate immediately without scanning tracks or querying Gemini:

```bash
uv run python -m src.cli.main organize --wipe-only
```

**Non-Interactive Automation** — bypass interactive confirmation prompts when running in scripts, cron jobs, or CI/CD:

```bash
uv run python -m src.cli.main organize --wipe-folder --yes
# or using short flag:
uv run python -m src.cli.main organize --wipe -y
```

Expected outcome: A folder is created (or reused), containing playlists for each genre identified in your library. Each track is categorized into its specific primary genre AND up to 3 sub-genres (e.g. *Foals - "Tron"* appears in *Math Rock*, *Dance-Punk*, and *Post-Punk Revival*). Genres and sub-genres with at least 5 tracks (or configured `--min-genre-size`) receive dedicated standalone playlists. Primary genres falling below `--min-genre-size` are consolidated into an "Others" playlist, while sparse sub-genres below `--min-genre-size` are suppressed from standalone playlist creation to prevent library clutter. Tracks with ambiguous or unidentifiable genres are placed into an "Unknown" playlist. When sync completes, a summary is printed with a direct link to view the folder on Tidal.

**`organize` notes:**
**Force Re-Classification (`--refresh-genres`)** — bypass the local database cache and force Gemini to re-classify every track across your entire library. **Note:** This option is token-expensive depending on your library size:
```bash
uv run python -m src.cli.main organize --refresh-genres
```
- **Clean-Slate Folder Wiping:** Because Tidal prevents deleting non-empty playlist folders, `--wipe-folder` and `--wipe-only` delete each individual playlist inside the target folder, preserving the folder container and its persistent URL while providing a clean slate.
- **Interactive Confirmation:** Running `--wipe-folder` or `--wipe-only` in an interactive terminal prompts for confirmation (`Are you sure you want to delete all playlists in folder '...'? [y/N]`) unless `--yes` / `-y` is supplied or non-interactive execution is detected.
- **Multi-Genre Organization:** Gemini identifies 1 primary genre and up to 3 specific sub-genres, strictly avoiding generic umbrella terms like "Rock" or "Pop" when specific styles apply. Tracks are added to both their primary and all qualifying sub-genre playlists.
- **Minimum Genre Size & Sub-Genre Suppression:** The default minimum genre size is 5 tracks. Standalone playlists are created only for genres and sub-genres with at least 5 tracks (or the configured `--min-genre-size`). Primary genres with fewer tracks are consolidated into "Others", while sparse sub-genres with fewer tracks are suppressed from standalone playlist creation to prevent clutter.
- Re-running the command syncs the existing playlists by adding new tracks and removing tracks that are no longer in your library, without creating duplicates.
- **SQLite Caching:** Track genre classification results are cached locally in an SQLite database (default: `data/genre_cache.db`). On subsequent runs, cached classifications are reused with zero Gemini token cost, and token cost reduction percentages are reported in the CLI output.
- **`--refresh-genres`:** Forces Gemini to re-classify all tracks in your library from scratch, ignoring existing cached entries in SQLite. Note: this parameter is token-expensive depending on your library size.
- Playlists are processed and synced in ascending track count order. This forces Tidal to list the largest playlists first when you sort the folder by "Updated date" descending in the Tidal client.
- Obsolete genre playlists (whose tracks have been removed from your library or moved to another playlist) are automatically deleted from Tidal.
- This command uses `GEMINI_API_KEY` and requires a stable connection capable of retrieving large libraries.

## Parameters

### `recommend` Parameters

| Option | Description | Default | Required |
| --- | --- | --- | --- |
| `--playlist-name` | Name for the new Tidal playlist. Use `{date}` for dynamic date. | `"Discovery {date}"` | No |
| `--gemini` | Use Gemini AI for recommendations instead of Last.fm. | `False` | No |
| `--num-tidal-tracks` | Number of random favorite tracks to select as seeds. | `10` | No |
| `--num-similar-tracks` | Number of similar tracks to retrieve per seed. | `5` | No |
| `--shuffle` | Changes recommendation behavior (deep cuts/variety). | `False` | No |
| `--exclude-favorites` | Exclude tracks already present in your Tidal favorites. | `False` | No |
| `--folder` | Tidal folder to place the playlist in. | — | No |

### `radio` Parameters

| Option | Description | Default | Required |
| --- | --- | --- | --- |
| `--artist` | Artist name of the seed track. | — | **Yes** |
| `--track` | Track title of the seed track. | — | **Yes** |
| `--playlist-name` | Custom name for the new Tidal playlist. Use `{date}` for dynamic date. | `"{artist} - {track} Radio"` | No |
| `--num-tracks` | Desired total number of tracks (1 seed at Track #1 + recommendations). | `50` | No |
| `--num-similar-tracks` | Alias for `--num-tracks`. | `50` | No |
| `--gemini` | Use Google Gemini AI for recommendations instead of Last.fm. | `False` | No |
| `--shuffle` | Deep cuts with Gemini AI or shuffle with Last.fm. | `False` | No |
| `--exclude-favorites` | Exclude tracks already present in your Tidal favorites. | `False` | No |
| `--folder` | Tidal folder to place the playlist in. | `Radio` | No |

### `organize` Parameters

These parameters apply identically to `organize` and its alias `genre-organizer`:

| Option | Description | Default | Required |
| --- | --- | --- | --- |
| `--folder` | Tidal folder name for the genre playlists. | `Genres` | No |
| `--min-genre-size` | Minimum tracks needed to generate a playlist. Tracks from smaller primary genres go into 'Others'; sub-genres with fewer tracks are omitted from playlist creation. | `5` | No |
| `--db-path` | Path to the SQLite database cache file. | `data/genre_cache.db` | No |
| `--refresh-genres` | Force Gemini to re-classify all tracks, bypassing local cache. Note: token-expensive depending on library size. | `False` | No |
| `--wipe-folder`, `--wipe` | Delete all existing playlists inside the target folder before synchronizing new playlists. | `False` | No |
| `--wipe-only` | Delete all existing playlists inside the target folder and terminate immediately. | `False` | No |
| `--yes`, `-y` | Skip interactive confirmation prompt when wiping playlists. | `False` | No |

## Troubleshooting

### Gemini Model Unavailable

**Symptoms:** The CLI logs an error mentioning the model name and a "not found" or "unavailable" failure category.

**Explanation:** The configured `GEMINI_MODEL` (or the built-in default) does not exist or is temporarily unavailable in the Gemini API. This is distinct from auth or quota errors — it means the specific model cannot be reached.

**Corrective action:**

1. Check the value of `GEMINI_MODEL` in your `.env` file or exported environment variable. Verify the model name is valid and currently available.
2. If you have `GEMINI_FALLBACK_MODEL` configured, the CLI will automatically attempt to use it. Verify that the fallback model name is also valid.
3. If neither model works, remove the `--gemini` flag to use Last.fm recommendations instead.
4. In `radio` mode, the CLI automatically falls back to Last.fm when Gemini is unavailable.

### `radio` Missing Required Options

**Symptoms:** The CLI exits with an error: `"Missing option '--artist'"` or `"Missing option '--track'"`.

**Explanation:** `radio` requires both `--artist` and `--track` to identify the seed track.

**Corrective action:** Provide both options together:

```bash
uv run python -m src.cli.main radio --artist "Lost Tribe" --track "Gamemaster"
```

### Authentication or Quota Failure

**Symptoms:** The CLI logs an error with a failure category of "auth", "permission", or "quota" — typically from the Gemini API or Tidal session.

**Explanation:** These errors indicate your API key is invalid, expired, or has exceeded its usage quota. Auth and quota errors do **not** trigger the Gemini fallback mechanism — they are treated as unrecoverable for the current run.

**Corrective action:**

1. **Gemini auth/quota:** Verify `GEMINI_API_KEY` in your `.env` file is correct and active. Check your [Google AI Studio](https://aistudio.google.com/apikey) dashboard for quota status.
2. **Tidal session expired:** Delete `tidal_session.json` and run the script interactively once to re-authenticate:

    ```bash
    rm tidal_session.json
    uv run python -m src.cli.main recommend
    ```

3. Retry the original command after resolving the credential or quota issue.

### Gemini Response Handling Failure

**Symptoms:** The CLI exits with an error mentioning `category='response-handling'` or indicates Gemini returned an unusable structured response after retry.

**Explanation:** The request reached Gemini, but the response was not usable for playlist generation (for example, empty parsed output or blocked terminal state). The CLI retries exactly once and then aborts to avoid misattributing the failure to `--exclude-favorites`.

**Corrective action:**

1. Retry the command once later (provider-side transient issues can recover).
2. Verify `GEMINI_MODEL` (and `GEMINI_FALLBACK_MODEL` if configured) are valid for your account.
3. If you are using `--exclude-favorites`, note that this failure occurs before favorites filtering runs.

### Favorites Exclusion Retrieval Failure

**Symptoms:** The CLI exits with an error indicating it could not retrieve the complete favorites list for `--exclude-favorites`.

**Explanation:** Exclusion mode requires a complete favorites snapshot. If favorites pagination fails after retries or returns incomplete data, the run aborts by design.

**Corrective action:**

1. Verify `tidal_session.json` is valid (re-authenticate if needed).
2. Check network connectivity and retry the same command.
3. If you must proceed immediately without exclusion, rerun without `--exclude-favorites`.

**Note:** Favorites exclusion data is held in memory for the current run only; no favorites cache file is written.

## Scheduling

You can schedule the script to run periodically using `cron` on Unix-like systems or Task Scheduler on Windows.

### cron

`cron` is a task scheduler for Unix-like systems. To set up a daily job:

1. Open your crontab file:

    ```bash
    crontab -e
    ```

2. Add a schedule line. Replace `/path/to/tidal-discovery-engine` with the absolute path to your project folder (run `pwd` from your project directory to get it):

    ```bash
    0 8 * * * cd /path/to/tidal-discovery-engine && /home/username/.local/bin/uv run python -m src.cli.main recommend --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}"
    ```

    This example runs the script every day at 8:00 AM.

3. Save and close the file. The new schedule is active immediately.

### Windows Task Scheduler

1. Open Task Scheduler.
2. Create a new task.
3. Set a trigger for when you want the task to run.
4. Set the action to "Start a program".
5. Set the program/script to your Python executable inside the `.venv` folder (e.g., `C:\path\to\tidal-discovery-engine\.venv\Scripts\python.exe`).
6. Set the arguments to `recommend --playlist-name "Daily Discovery"`.
7. Set the "Start in" directory to the root of the project (e.g., `C:\path\to\tidal-discovery-engine`).

---

## Project Structure

```text
tidal-discovery-engine/
├── docs/                       # Project documentation & bootstrap records
│   └── prompt/                 # Initial development prompts
├── scratch/                    # Local scratchpad for experiments & spikes (gitignored)
├── specs/                      # Spec Kit specifications & feature records (001–018)
├── src/                        # Main application source code
│   ├── cli/                    # Click CLI commands and entry points (main.py)
│   ├── lib/                    # Shared infrastructure (database helpers)
│   └── services/               # Core business logic
│       ├── gemini_service.py          # Google Gemini AI recommendations & classification
│       ├── genre_cache_service.py     # SQLite caching for library genre metadata
│       ├── genre_organizer_service.py # Multi-genre analysis & playlist sync
│       ├── lastfm_service.py          # Last.fm similar tracks discovery
│       └── tidal_service.py           # Tidal API session & playlist management
├── tests/                      # Automated test suite (all 122 tests pass)
├── data/                       # Local SQLite databases (gitignored runtime data)
├── .env.example                # Template for environment variables and API keys
├── pyproject.toml              # Dependencies and project metadata
└── README.md                   # Complete documentation and command reference
```

---

## Development Notes

This project was developed using a unique, AI-driven workflow inside Visual Studio Code, leveraging the **Spec Kit** methodology. The entire process, from initial idea to final implementation, was guided by a series of structured prompts and automated scripts.

The primary tools used were:

*   **GitHub Copilot:** Initially used as the core AI assistant for generating and refining code.
*   **Multiple AI Models, then Gemini:** Integrated for advanced reasoning and to help guide the development process.  
*   **Spec Kit:** A set of prompts and scripts that enforce a rigorous, specification-driven development process. This included generating a constitution, a detailed specification, a project plan, and a task list before any code was written.

This approach ensured that the project was well-defined, robust, and implemented efficiently, with the AI agents handling the heavy lifting of code generation and iteration.

---

## References

*   **APIs**
    *   [Last.fm API](https://www.last.fm/api) - Used for finding similar tracks.
    *   [Tidal API](https://developer.tidal.com/) - Used for accessing user favorites, searching catalog, and creating/syncing playlists.
    *   [Google Gemini API](https://ai.google.dev/) - Used for AI music recommendations and library genre classification.

*   **Libraries & Tools**
    *   [`google-genai`](https://github.com/googleapis/python-genai) - The official Python SDK for Google's Gemini API.
    *   [`tidalapi`](https://github.com/tamland/python-tidal) - A Python wrapper for the Tidal API.
    *   [`pylast`](https://github.com/pylast/pylast) - A Python wrapper for the Last.fm API.
    *   [`click`](https://click.palletsprojects.com/) - A Python package for creating command-line interfaces.
    *   [`python-dotenv`](https://github.com/theskumar/python-dotenv) - Reads key-value pairs from `.env` files.
    *   [`sqlite3`](https://docs.python.org/3/library/sqlite3.html) - Python's built-in database engine used for local caching of track genres.
    *   [`uv`](https://docs.astral.sh/uv/) - An extremely fast Python package and project manager.

