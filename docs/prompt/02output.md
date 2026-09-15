Below is a comprehensive AI Spec Kit designed to guide the development of your music discovery and playlisting project. This kit is divided into three sections: a Constitution outlining the project's core principles, a Specification detailing the technical requirements, and a Plan providing a roadmap for implementation.

### Constitution

**Project Title:** Tidal Discovery Engine

**Mission:** To create a personalized music discovery tool that seamlessly integrates with a user's Tidal library, leverages Last.fm's recommendation engine, and automates the creation of new playlists to enrich the user's listening experience.

**Core Principles:**

*   **User-Centricity:** The project will prioritize a simple and intuitive command-line interface (CLI) that allows for easy configuration and operation.
*   **Automation:** The core value lies in automating the process of finding new music and creating playlists, saving the user time and effort.
*   **Personalization:** By starting with the user's favorite tracks, the generated playlists will be tailored to their specific musical tastes.
*   **Extensibility:** The project will be built with a modular design to potentially accommodate other music services or recommendation engines in the future.
*   **Reliability:** The application will be robust, with proper error handling and logging to ensure consistent and predictable behavior, especially when running as a scheduled task.

### Specification

**1. Core Functionality:**

*   **Tidal Library Integration:**
    *   The application will securely connect to the user's Tidal account.
    *   It will fetch a user-specified number of random tracks from their "Favorite Tracks".
*   **Last.fm Similar Tracks:**
    *   For each of the selected Tidal tracks, the application will query the Last.fm API to find similar tracks.
    *   The number of similar tracks to retrieve per Tidal track will be configurable by the user, with a sensible default if not provided.
*   **Tidal Playlist Creation:**
    *   The application will create a new playlist in the user's Tidal account.
    *   The name of the playlist will be specified by the user as a command-line argument.
*   **Playlist Metadata:**
    *   Upon creation, the playlist's description will be automatically populated with the date of the run and other relevant details (e.g., the number of seed tracks, the number of similar tracks fetched per seed).
*   **Playlist Organization (Best Effort):**
    *   The application will attempt to place the newly created playlist into a user-specified folder name within Tidal. *Note: The feasibility of this feature depends on the capabilities of the Tidal API, and it should be considered a "nice-to-have" feature that may require further investigation during development.*
*   **Track Addition:**
    *   The tracks retrieved from Last.fm will be searched for on Tidal and added to the newly created playlist.

**2. Technical Specifications:**

*   **Development Language:** Python
*   **Dependency Management:** The project will use `uv` for managing Python packages and virtual environments.
*   **Command-Line Interface (CLI):**
    *   The application will be built as a CLI tool using the `click` library.
    *   The CLI will accept the following arguments/options:
        *   `--num-tidal-tracks`: The number of random favorite tracks to select from Tidal.
        *   `--num-similar-tracks`: The number of similar tracks to retrieve from Last.fm for each Tidal track.
        *   `--playlist-name`: The name for the new Tidal playlist.
        *   `--playlist-folder`: (Optional) The name of the folder to place the playlist in.
*   **Authentication and Credentials:**
    *   All sensitive credentials (Tidal and Last.fm API keys/secrets) will be stored in a `.env` file and loaded into the application's environment.
    *   The application will only use the necessary credentials for each API. For instance, Last.fm API calls for similar tracks may not require user authentication, only an API key.
    *   The application must support a non-interactive authentication flow to allow for periodic execution by a scheduler. This will likely involve an initial interactive login to obtain and store refreshable tokens.
*   **Logging:**
    *   The application will implement comprehensive logging using Python's built-in `logging` module.
    *   Logs will be output to both the console (stdout) and a dedicated log file (`project.log`).
    *   Logged information will include:
        *   The tracks retrieved from Tidal.
        *   The similar tracks retrieved from Last.fm.
        *   The name of the created playlist and its URL.
        *   The tracks successfully added to the playlist.
        *   Any errors that occur during the process.
*   **Documentation:**
    *   A `README.md` file will be created and maintained. It will be updated as features are added or changed.
    *   The `README.md` will include:
        *   A clear description of the project and its purpose.
        *   Instructions on how to set up the project, including installing dependencies with `uv` and configuring the `.env` file.
        *   Detailed usage instructions for the CLI, including all available options and arguments.

**3. Scheduling:**

*   The project is intended to be run periodically as a scheduled task.
*   Documentation will be provided on how to schedule the script to run using:
    *   `cron` on Unix-like operating systems.
    *   Task Scheduler on Windows.

### Plan

**Phase 1: Foundation and Core Logic (1-2 weeks)**

*   **Objective:** Set up the project structure and implement the core functionality of retrieving tracks and creating a basic playlist.
*   **Tasks:**
    1.  Initialize the project with `uv` and set up the basic file structure (`main.py`, `README.md`, `.gitignore`, `.env.example`).
    2.  Implement the CLI skeleton using `click` with placeholders for the required options.
    3.  Set up the `.env` file for storing credentials and implement the logic to load them.
    4.  Implement the authentication flow for the Tidal API. Focus on an initial interactive login that can store credentials for later use.
    5.  Implement the function to connect to Tidal and retrieve a specified number of random favorite tracks.
    6.  Implement the function to connect to the Last.fm API and retrieve similar tracks for a given track.
    7.  Implement the basic functionality to create a new playlist in Tidal with a user-specified name.
    8.  Implement the logic to add the retrieved Last.fm tracks to the new Tidal playlist.

**Phase 2: Refinement and User Experience (1 week)**

*   **Objective:** Enhance the core functionality with better metadata, logging, and documentation.
*   **Tasks:**
    1.  Implement the logic to update the created playlist's description with the run date and other details.
    2.  Set up the logging framework to log to both the console and a file, capturing all specified events.
    3.  Thoroughly document the CLI in the `README.md` file, explaining all the options and providing usage examples.
    4.  Refine the error handling to provide clear and informative messages to the user.

**Phase 3: Automation and Deployment (1 week)**

*   **Objective:** Finalize the non-interactive authentication and document the scheduling process.
*   **Tasks:**
    1.  Implement and test the non-interactive authentication flow to ensure the script can run without user input after the initial setup.
    2.  Write clear and concise instructions in the `README.md` for scheduling the script on both `cron` and Windows Task Scheduler.
    3.  (Optional) Investigate and, if feasible, implement the functionality to create the playlist within a specified folder.
    4.  Perform final testing of the end-to-end workflow.
    5.  Review and finalize all documentation.