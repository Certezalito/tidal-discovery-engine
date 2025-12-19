# Tidal Discovery Engine

A command-line tool that generates a new Tidal playlist with Last.fm recommended tracks based on a selection of your favorite tracks from Tidal.

## Setup

1.  Clone the repository.
2.  Install dependencies with `uv`: `uv pip install -e .`
3.  Create a `.env` file and add your Last.fm API key. You can get one from your [Last.fm API account page](https://www.last.fm/api/account/create).

    ```
    LASTFM_API_KEY=your_api_key
    ```

4.  Run the script once interactively to authenticate with Tidal. This will create a `tidal_session.json` file in the root of the project, which will be used for all future non-interactive runs.

## Usage

This tool has two main modes of operation and a shuffle modifier that can be combined with either mode.

### Mode 1: Generate from Your Favorite Tracks

This is the default mode. The script will select a random number of tracks from your "Favorite Tracks" on Tidal and use them as seeds to find similar music.

**Example:**
```bash
uv run python -m src.cli.main --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}"
```

### Mode 2: Generate from a Single Seed Track

You can also generate a playlist based on a single, specific song. This is perfect for exploring the sound of a track you've just discovered.

**Example:**
```bash
uv run python -m src.cli.main --artist "Lost Tribe" --track "Gamemaster" --num-similar-tracks 1000 --playlist-name "Gamemaster Vibes"
```

### Modifier: Adding Variety with Shuffle

For either of the modes above, you can add the `--shuffle` flag. This tells the script to fetch a large pool of similar tracks (up to 1000 per seed) and then randomly select the number specified by `--num-similar-tracks`. This is a great way to discover less obvious recommendations.

**Example (with Mode 1):**
```bash
uv run python -m src.cli.main --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE Shuffle {date}" --shuffle
```

### All Parameters

| Option                 | Description                                                                                                | Default | Required |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- | ------- | -------- |
| `--num-tidal-tracks`   | (Mode 1) The number of random favorite tracks to select from Tidal to use as seeds.                          | `10`    | No       |
| `--num-similar-tracks` | The number of similar tracks to retrieve from Last.fm for each seed track.                                 | `5`     | No       |
| `--shuffle`            | If enabled, fetches a large pool of similar tracks (1000) and randomly selects from it to increase variety.         | `False` | No       |
| `--artist`             | (Mode 2) The artist of a specific track to use as a seed. Must be used with `--track`.                       |         | No       |
| `--track`              | (Mode 2) The title of a specific track to use as a seed. Must be used with `--artist`.                      |         | No       |
| `--playlist-name`      | The name for the new Tidal playlist. You can use `{date}` to automatically insert the current date (`YYYYMMDD`). |         | Yes      |


## Scheduling

You can schedule the script to run periodically using `cron` on Unix-like systems or Task Scheduler on Windows.

### cron

`cron` is a task scheduler for Unix-like systems. To set up a daily job, you need to edit your user's `crontab` file.

1.  **Open your crontab file** by running the following command in your terminal:
    ```bash
    crontab -e
    ```

2.  **Add the schedule line.** Go to the end of the file and add the following line. **Important:** You must replace `/path/to/tidal-discovery-engine` with the absolute path to your project folder (you can get this by running `pwd` from your project directory).

    The following example will run the script every day at 8:00 AM.
    ```bash
    0 8 * * * cd /path/to/tidal-discovery-engine && /home/username/.local/bin/uv run python -m src.cli.main --num-tidal-tracks 5 --num-similar-tracks 10 --playlist-name "TDE {date}"
    ```

3.  **Save and close the file.** The new schedule will be active immediately.

### Windows Task Scheduler

1.  Open Task Scheduler.
2.  Create a new task.
3.  Set a trigger for when you want the task to run.
4.  Set the action to "Start a program".
5.  Set the program/script to your Python executable inside the `.venv` folder (e.g., `C:\path\to\tidal-discovery-engine\.venv\Scripts\python.exe`).
6.  Set the arguments to `-m src.cli.main --playlist-name "Daily Discovery"`.
7.  Set the "Start in" directory to the root of the project (e.g., `C:\path\to\tidal-discovery-engine`).

---

## Development Notes

This project was developed using a unique, AI-driven workflow inside Visual Studio Code, leveraging the **Spec Kit** methodology. The entire process, from initial idea to final implementation, was guided by a series of structured prompts and automated scripts.

The primary tools used were:

*   **GitHub Copilot:** Used as the core AI assistant for generating and refining code.
*   **Gemini 2.5 Pro:** Integrated for advanced reasoning and to help guide the development process.
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

