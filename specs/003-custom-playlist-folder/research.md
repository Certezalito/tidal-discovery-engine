# Research Log: Custom Tidal Playlist Folders

## Research Task 1: Tidal API Error Handling

**Objective**: Determine the specific exceptions or error codes raised by `tidalapi` when:
1.  A folder cannot be created (e.g., limit reached).
2.  A playlist cannot be added to a folder.
3.  Authentication is insufficient for folder operations.

**Investigation**:
1.  Review `tidalapi` source code or documentation regarding `create_folder` and `create_playlist`.
2.  Test failure scenarios if possible (e.g., invalid names, limits).

**Outcome**:
-   **Findings**:
    1.  `tidalapi.user.User.create_folder` and `create_playlist` use `PUT` requests.
    2.  They raise `tidalapi.exceptions.ObjectNotFound` if the response body does not contain the expected data (e.g. `uuid` for playlist) despite a 200 OK status.
    3.  Underlying network/HTTP errors are raised via `requests.HTTPError` (caught in `tidalapi.request.Requests.request`).
    4.  `tidalapi.request` attempts to map `HTTPError` to specific `TidalAPIError` subclasses (e.g. `TooManyRequests`) via `http_error_to_tidal_error`. If no mapping exists, `requests.HTTPError` is re-raised.
-   **Action**: Update error handling logic in `tidal_service.py` to catch `ObjectNotFound`, `TidalAPIError`, and `requests.HTTPError`. Specifically handle `ObjectNotFound` for creation failures and `HTTPError` for permission/network issues.
