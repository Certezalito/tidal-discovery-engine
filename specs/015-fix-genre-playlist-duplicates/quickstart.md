# Quickstart & Validation: Fix Duplicate Genre Playlists

This guide provides scenarios to validate that duplicate genre playlists are no longer created and existing ones are correctly paginated and cleaned up.

## Prerequisites
- A Tidal account with favorite tracks populated.
- Gemini API key set in `.env` (or mock setup).

## Validation Scenario 1: Basic Idempotency
1. Run the sync command to generate initial playlists:
   ```bash
   uv run python main.py genre-playlist
   ```
2. Run the command a second time:
   ```bash
   uv run python main.py genre-playlist
   ```
3. **Verify**: Check the target folder in your Tidal client. There should be exactly one playlist per genre. The command output should state `0 playlists created` and `X playlists updated` on the second run.

## Validation Scenario 2: Duplicate Cleanup
1. Manually create a duplicate playlist in the target folder with the exact same name as an existing genre (e.g., two "Rock" playlists).
2. Run the sync command:
   ```bash
   uv run python main.py genre-playlist
   ```
3. **Verify**: The command output should indicate that `1 playlist deleted`. Check the Tidal client to confirm only one "Rock" playlist remains, and it contains the correct synced tracks.

## Validation Scenario 3: Deep Pagination
1. Create a large number of dummy playlists in the target folder (e.g., 60+ playlists) to exceed the default pagination limit of 50.
2. Run the sync command:
   ```bash
   uv run python main.py genre-playlist
   ```
3. **Verify**: The system should successfully fetch all 60+ playlists. It will delete any obsolete or duplicate dummy playlists and properly update existing ones without creating new duplicates for genres that were past the 50th item.
