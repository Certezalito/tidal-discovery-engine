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
    - `GEMINI_MODEL` is optional. Resolution order: exported environment variable → `.env` value → built-in default (`gemini-2.0-flash`).
    - `GEMINI_FALLBACK_MODEL` is optional. Used only when the primary model is unavailable or not found.

4. Run the script once interactively to authenticate with Tidal:

    ```bash
    uv run python -m src.cli.main recommend --playlist-name "Test"
    ```

    This creates a `tidal_session.json` file in the project root, which is reused for all future non-interactive runs.

## Commands

The CLI supports three commands: `recommend`, `radio`, and `genre-playlist`. Each command has its own set of options.

### `recommend`

Generates a new Tidal playlist with recommended tracks based on a selection of your favorite tracks.

**Quick start** — generate a playlist from your Tidal favorites using Last.fm recommendations:

```bash
uv run python -m src.cli.main recommend --playlist-name "TDE {date}"
```

To exclude tracks you already saved in Tidal favorites from the resulting playlist:

```bash
uv run python -m src.cli.main recommend --playlist-name "TDE {date}" --exclude-favorites
```

#### Last.fm Path (Default)

Selects random tracks from your Tidal favorites and finds similar music through Last.fm.

**Without `--shuffle`** — returns the top similar tracks per seed:

```bash
uv run python -m src.cli.main recommend --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist with up to 50 tracks (5 seeds × 10 similar each) of popular similar music.

**With `--shuffle`** — fetches a large pool (up to 1000 per seed) and randomly selects from it for deeper cuts:

```bash
uv run python -m src.cli.main recommend --shuffle --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist with up to 50 tracks randomly drawn from a much larger pool, producing more varied and unexpected recommendations.

#### Gemini AI Path

Uses Google Gemini AI instead of Last.fm to generate recommendations. Requires `GEMINI_API_KEY`.

**Without `--shuffle`** — generates popular, highly relevant suggestions:

```bash
uv run python -m src.cli.main recommend --gemini --playlist-name "TDE Gemini Hits" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of AI-curated tracks that are well-known and closely related to your favorites.

**With `--shuffle`** — generates deep cuts, underground, and lesser-known tracks:

```bash
uv run python -m src.cli.main recommend --gemini --shuffle --playlist-name "TDE Gemini Underground" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of lesser-known, underground tracks selected by AI for a more adventurous listening experience.

### `radio`

Generates a dedicated track radio playlist seeded with a specific song. The seed track is placed at **Track #1** on Tidal, followed by recommendations up to the requested total count (default **50 tracks**: 1 seed + 49 recommendations).

**Quick start** — generate a track radio playlist with defaults:

```bash
uv run python -m src.cli.main radio --artist "Underworld" --track "Born Slippy"
```

Expected outcome:
- Playlist named `"Underworld - Born Slippy Radio"` containing 50 tracks total.
- Track #1 is `"Born Slippy"` by Underworld.
- Tracks #2–#50 are 49 recommendations from Last.fm.
- Playlist description includes seed metadata: `"Seed track: Born Slippy by Underworld • Total tracks: 50"`.
- Playlist is organized inside the `"Radio"` folder on Tidal by default.

#### Dynamic Date in Playlist Name

Use `{date}` to automatically insert today's date (`YYYYMMDD`):

```bash
uv run python -m src.cli.main radio --artist "Underworld" --track "Born Slippy" --playlist-name "Born Slippy Radio {date}"
```

#### Gemini AI Recommendations

Use Google Gemini AI instead of Last.fm for recommendations:

```bash
uv run python -m src.cli.main radio --artist "Burial" --track "Archangel" --gemini
```

- **With `--shuffle`**: Instructs Gemini to discover deep cuts, underground gems, and lesser-known adjacent tracks.
- **Graceful fallback**: If the configured Gemini model is unavailable, the command automatically falls back to Last.fm recommendations with a warning.

#### Advanced Options & Organization

Exclude existing Tidal favorites and file the playlist into a custom folder (overriding the default `"Radio"` folder):

```bash
uv run python -m src.cli.main radio \
  --artist "Burial" \
  --track "Archangel" \
  --gemini \
  --shuffle \
  --exclude-favorites \
  --folder "Electronic Stations" \
  --num-tracks 30
```

### `genre-playlist`

> ⚠️ **DESTRUCTIVE OPERATION**: The `genre-playlist` command strictly owns the folder it targets. **Any playlists in the target folder that do not match the expected generated genres (including manually created playlists) will be permanently deleted.** Do not point this command at a folder containing your personal manual playlists.


Reads your entire Tidal library, uses Gemini to classify each track by genre, and creates or syncs one playlist per genre inside a dedicated folder. This mode helps you organize your entire library automatically.

**First Run & Syncing** — organize your library into a folder named "Genres" (the default folder name) with the default minimum genre size (10 tracks):

```bash
uv run python -m src.cli.main genre-playlist
```

**Custom Folder, Threshold & Database Path** — organize into a specific folder, group genres with fewer than 10 tracks into an "Others" playlist, and specify a custom SQLite database cache file:

```bash
uv run python -m src.cli.main genre-playlist --folder "My Music Styles" --min-genre-size 10 --db-path "data/genre_cache.db"
```

Expected outcome: A folder is created (or reused), containing playlists for each genre identified in your library that meets the minimum track threshold. Tracks with highly niche genres (falling below the threshold) are consolidated into an "Others" playlist. Tracks with ambiguous or unidentifiable genres are placed into an "Unknown" playlist.

**`genre-playlist` notes:**
- Re-running the command syncs the existing playlists by adding new tracks and removing tracks that are no longer in your library, without creating duplicates.
- **SQLite Caching:** Track genre classification results are cached locally in an SQLite database (default: `data/genre_cache.db`). On subsequent runs, cached classifications are reused with zero Gemini token cost, and token cost reduction percentages are reported in the CLI output.
- The command groups genres with fewer tracks than `--min-genre-size` into an "Others" playlist to limit playlist sprawl. The default threshold is 10 (so genres with 9 or fewer tracks go to "Others").
- Playlists are processed and synced in ascending track count order. This forces Tidal to list the largest playlists first when you sort the folder by "Updated date" descending in the Tidal client.
- Obsolete genre playlists (whose tracks have been removed from your library or moved to another playlist) are automatically deleted from Tidal.
- This command uses `GEMINI_API_KEY` and requires a stable connection capable of retrieving large libraries.

## Parameters

### `recommend` Parameters

| Option | Description | Default | Required |
| --- | --- | --- | --- |
| `--playlist-name` | Name for the new Tidal playlist. Use `{date}` for dynamic date. | — | **Yes** |
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

### `genre-playlist` Parameters

| Option | Description | Default | Required |
| --- | --- | --- | --- |
| `--folder` | Tidal folder name for the genre playlists. | `Genres` | No |
| `--min-genre-size` | Min tracks for a genre playlist; else grouped into 'Others'. | `10` | No |
| `--db-path` | Path to the SQLite database cache file. | `data/genre_cache.db` | No |

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
    uv run python -m src.cli.main recommend --playlist-name "Re-auth"
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

## Development Notes

This project was developed using a unique, AI-driven workflow inside Visual Studio Code, leveraging the **Spec Kit** methodology. The entire process, from initial idea to final implementation, was guided by a series of structured prompts and automated scripts.

The primary tools used were:

*   **GitHub Copilot:** Used as the core AI assistant for generating and refining code.
*   **Multiple AI Models:** Integrated for advanced reasoning and to help guide the development process.  Followup branches could be any AI available within GitHub Copilot
*   **Spec Kit:** A set of prompts and scripts that enforce a rigorous, specification-driven development process. This included generating a constitution, a detailed specification, a project plan, and a task list before any code was written.

This approach ensured that the project was well-defined, robust, and implemented efficiently, with the AI agents handling the heavy lifting of code generation and iteration.

---

## References

*   **APIs**
    *   [Last.fm API](https://www.last.fm/api) - Used for finding similar tracks.
    *   [Tidal API](https://developer.tidal.com/) - Used for accessing user favorites and creating playlists.

*   **Libraries**
    *   [`tidalapi`](https://github.com/tamland/python-tidal) - A Python wrapper for the Tidal API.
    *   [`pylast`](https://github.com/pylast/pylast) - A Python wrapper for the Last.fm API.
    *   [`click`](https://click.palletsprojects.com/) - A Python package for creating beautiful command-line interfaces.

