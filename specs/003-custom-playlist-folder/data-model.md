# Data Model: Custom Tidal Playlist Folders

## Folder
*Conceptual entity managed via Tidal API.*

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique identifier from Tidal. |
| `name` | `str` | Display name of the folder. |
| `created` | `datetime` | Creation timestamp (used for resolving duplicates). |

## Playlist (Updated)
*Extends existing playlist concept.*

| Field | Type | Description |
| :--- | :--- | :--- |
| `parent_id` | `str` | (Optional) ID of the folder containing this playlist. |
