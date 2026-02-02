# Data Model: Gemini Suggestions

## Entities

### Song (Value Object)
Represents a text-based song suggestion from the AI, containing minimal identification data.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `artist` | string | Yes | The name of the artist. |
| `title` | string | Yes | The title of the track. |
| `isrc` | string | Yes | The International Standard Recording Code (unique identifier). |

## Relationships
- **Input**: A list of `Song` (from Tidal) is sent to the AI.
- **Output**: A list of `Song` is returned by the AI.
- **Resolution**: Each `Song` returned is resolved to a Tidal Track ID via `TidalService`.

## Constraints
- ISRC Format: strict alphanumeric code (usually 12 chars), but we treat as opaque string for passing to Tidal API.
- JSON Schema: The AI output MUST strictly adhere to the `Song` structure.
