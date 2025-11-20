# Data Model: Tidal Playlist Generator

## Entities

### Track

-   **title**: string
-   **artist**: string
-   **album**: string

### Playlist

-   **name**: string
-   **description**: string
-   **tracks**: list of Track objects

### User

-   **tidal_session**: file (`tidal_session.json`)
-   **lastfm_api_key**: string
