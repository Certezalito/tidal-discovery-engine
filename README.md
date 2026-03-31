# Tidal Discovery Engine

A command-line tool that generates Tidal playlists with recommended tracks using Last.fm similarity data or Google Gemini AI, seeded from your favorite tracks or a specific song.

## Setup

1. Clone the repository:

    ```bash
    git clone https://github.com/Certezalito/tidal-discovery-engine.git && cd tidal-discovery-engine
    ```

2. Create a virtual environment and install dependencies:

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
    - `GEMINI_MODEL` is optional. Resolution order: exported environment variable → `.env` value → built-in default.
    - `GEMINI_FALLBACK_MODEL` is optional. Used only when the primary model is unavailable or not found.

4. Run the script once interactively to authenticate with Tidal:

    ```bash
    uv run python -m src.cli.main --playlist-name "Test"
    ```

    This creates a `tidal_session.json` file in the project root, which is reused for all future non-interactive runs.

## Modes

The CLI supports three modes of operation. Each mode can be combined with `--shuffle` to change recommendation behavior, and with `--folder` to organize playlists into a Tidal folder.

**Quick start** — generate a playlist from your Tidal favorites using Last.fm recommendations:

```bash
uv run python -m src.cli.main --playlist-name "TDE {date}"
```

### Mode 1: Last.fm Recommendations (Default)

Selects random tracks from your Tidal favorites and finds similar music through Last.fm.

**Without `--shuffle`** — returns the top similar tracks per seed:

```bash
uv run python -m src.cli.main --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist with up to 50 tracks (5 seeds × 10 similar each) of popular similar music.

**With `--shuffle`** — fetches a large pool (up to 1000 per seed) and randomly selects from it for deeper cuts:

```bash
uv run python -m src.cli.main --shuffle --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist with up to 50 tracks randomly drawn from a much larger pool, producing more varied and unexpected recommendations.

### Mode 2: Gemini AI Recommendations

Uses Google Gemini AI instead of Last.fm to generate recommendations from your Tidal favorites.

**Without `--shuffle`** — generates popular, highly relevant suggestions:

```bash
uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini Hits" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of AI-curated tracks that are well-known and closely related to your favorites.

**With `--shuffle`** — generates deep cuts, underground, and lesser-known tracks:

```bash
uv run python -m src.cli.main --gemini --shuffle --playlist-name "TDE Gemini Underground" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of lesser-known, underground tracks selected by AI for a more adventurous listening experience.

**Runtime model override** — temporarily use a different Gemini model:

```bash
export GEMINI_MODEL=gemini-2.0-flash
uv run python -m src.cli.main --gemini --playlist-name "TDE Gemini Override" --folder "Tidal Discovery Engine"
```

**Model configuration notes:**

- Missing or blank `GEMINI_MODEL` logs one warning per run and uses the built-in default model.
- Fallback is attempted only when the primary model is unavailable or not found **and** `GEMINI_FALLBACK_MODEL` is configured.
- Auth, quota, and permission failures do **not** trigger fallback.

### Mode 3: Single Seed Track

Generates a playlist based on one specific song. Both `--artist` and `--track` must be provided together.

**Last.fm path:**

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --num-similar-tracks 1000 --playlist-name "Gamemaster Vibes" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of up to 1000 tracks similar to "Gamemaster" by Lost Tribe, sourced via Last.fm.

**Gemini path:**

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --num-similar-tracks 20 --playlist-name "Gamemaster Gemini" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of 20 AI-recommended tracks based on "Gamemaster" by Lost Tribe.

**Gemini deep cuts path:**

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --gemini --shuffle --num-similar-tracks 20 --playlist-name "Gamemaster Gemini Deep Cuts" --folder "Tidal Discovery Engine"
```

Expected outcome: A playlist of 20 underground, lesser-known tracks inspired by "Gamemaster" by Lost Tribe.

**Mode 3 notes:**

- `--artist` and `--track` must be provided together. Providing only one produces an error.
- `--num-similar-tracks` must be a positive integer.
- If the Gemini model is unavailable or not found in Mode 3, the CLI falls back to Last.fm for the same seed.
- Auth, quota, and permission Gemini failures do **not** trigger fallback and return actionable errors.
- Tidal tracks that cannot be resolved are skipped with a warning showing the skipped count and a preview of up to 5 names.
- If zero tracks can be inserted after resolution, the run fails.

## All Parameters

| Option | Description | Default | Required |
| --- | --- | --- | --- |
| `--num-tidal-tracks` | Number of random favorite tracks to select as seeds. Used in Mode 1 and Mode 2. | `10` | No |
| `--num-similar-tracks` | Number of similar tracks to retrieve per seed. Used in all modes. | `5` | No |
| `--gemini` | Use Gemini AI for recommendations instead of Last.fm. Activates Mode 2, or Mode 3 when combined with `--artist`/`--track`. Requires `GEMINI_API_KEY`. | `False` | No |
| `--shuffle` | Changes recommendation behavior. Last.fm: fetches a large pool and randomly selects. Gemini: requests deep cuts and underground tracks. Used in all modes. | `False` | No |
| `--artist` | Artist name for single-seed mode (Mode 3). **Must be used with `--track`**. | — | No |
| `--track` | Track title for single-seed mode (Mode 3). **Must be used with `--artist`**. | — | No |
| `--playlist-name` | Name for the new Tidal playlist. Use `{date}` to insert the current date (YYYYMMDD format). | — | **Yes** |
| `--folder` | Tidal folder to place the playlist in. Created automatically if it does not exist. | — | No |

**Constraints:**

- `--artist` and `--track` must be provided together. Providing only one produces an error.
- `--num-similar-tracks` must be a positive integer.
- `--gemini` requires the `GEMINI_API_KEY` environment variable to be set.

## Troubleshooting

### Gemini Model Unavailable

**Symptoms:** The CLI logs an error mentioning the model name and a "not found" or "unavailable" failure category.

**Explanation:** The configured `GEMINI_MODEL` (or the built-in default) does not exist or is temporarily unavailable in the Gemini API. This is distinct from auth or quota errors — it means the specific model cannot be reached.

**Corrective action:**

1. Check the value of `GEMINI_MODEL` in your `.env` file or exported environment variable. Verify the model name is valid and currently available.
2. If you have `GEMINI_FALLBACK_MODEL` configured, the CLI will automatically attempt to use it. Verify that the fallback model name is also valid.
3. If neither model works, remove the `--gemini` flag to use Last.fm recommendations instead.
4. In Mode 3, the CLI automatically falls back to Last.fm when the Gemini model is unavailable — no manual action is needed.

### Mode 3 Missing Required Options

**Symptoms:** The CLI exits with an error: `"Both --artist and --track are required together for single-seed mode."`

**Explanation:** Mode 3 requires both `--artist` and `--track` to identify the seed song. Providing only one of them is invalid.

**Corrective action:** Provide both options together:

```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --num-similar-tracks 20 --playlist-name "Seed Playlist"
```

### Authentication or Quota Failure

**Symptoms:** The CLI logs an error with a failure category of "auth", "permission", or "quota" — typically from the Gemini API or Tidal session.

**Explanation:** These errors indicate your API key is invalid, expired, or has exceeded its usage quota. Auth and quota errors do **not** trigger the Gemini fallback mechanism — they are treated as unrecoverable for the current run.

**Corrective action:**

1. **Gemini auth/quota:** Verify `GEMINI_API_KEY` in your `.env` file is correct and active. Check your [Google AI Studio](https://aistudio.google.com/apikey) dashboard for quota status.
2. **Tidal session expired:** Delete `tidal_session.json` and run the script interactively once to re-authenticate:

    ```bash
    rm tidal_session.json
    uv run python -m src.cli.main --playlist-name "Re-auth"
    ```

3. Retry the original command after resolving the credential or quota issue.

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
    0 8 * * * cd /path/to/tidal-discovery-engine && /home/username/.local/bin/uv run python -m src.cli.main --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}"
    ```

    This example runs the script every day at 8:00 AM.

3. Save and close the file. The new schedule is active immediately.

### Windows Task Scheduler

1. Open Task Scheduler.
2. Create a new task.
3. Set a trigger for when you want the task to run.
4. Set the action to "Start a program".
5. Set the program/script to your Python executable inside the `.venv` folder (e.g., `C:\path\to\tidal-discovery-engine\.venv\Scripts\python.exe`).
6. Set the arguments to `-m src.cli.main --playlist-name "Daily Discovery"`.
7. Set the "Start in" directory to the root of the project (e.g., `C:\path\to\tidal-discovery-engine`).

---

## Development Notes

This project was developed using a unique, AI-driven workflow inside Visual Studio Code, leveraging the **Spec Kit** methodology. The entire process, from initial idea to final implementation, was guided by a series of structured prompts and automated scripts.

The primary tools used were:

*   **GitHub Copilot:** Used as the core AI assistant for generating and refining code.
*   **Gemini 2.5/3.0 Pro:** Integrated for advanced reasoning and to help guide the development process.  Followup branches could be any AI available within GitHub Copilot
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

