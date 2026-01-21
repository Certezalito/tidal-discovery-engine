# Quickstart: Custom Tidal Playlist Folders

## Feature Overview
Allows users to specify a destination folder for generated playlists, keeping their collection organized.

## Usage

### Command Line Interface

To generate a playlist and place it in a specific folder:

```bash
python src/cli/main.py --folder "My AI Mixes"
```

### Behavior
- If "My AI Mixes" exists, the playlist is added there.
- If it doesn't exist, it is created.
- Case-insensitive matching is used ("my ai mixes" == "My AI Mixes").
- If the playlist name already exists in the folder, a counter is appended (e.g., "Playlist (1)").

## Troubleshooting

- **Folder not created**: Ensure your Tidal account has permission to create folders.
- **Duplicate folders**: The system uses the most recently created folder if duplicates exist.
