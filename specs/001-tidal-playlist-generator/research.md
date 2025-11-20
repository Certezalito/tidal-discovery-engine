# Research: Tidal Playlist Generator

## Tidal API Library

**Decision**: Use the `tidalapi` library.
**Rationale**: It is a well-maintained and popular library for interacting with the Tidal API from Python. It supports the necessary functionality for this project, including authentication and playlist creation.
**Alternatives considered**: Writing a custom API wrapper. This was rejected due to the time and effort required.

## Last.fm API Library

**Decision**: Use the `pylast` library.
**Rationale**: It is a popular and easy-to-use Python wrapper for the Last.fm API. It provides a simple interface for accessing the "get similar tracks" endpoint.
**Alternatives considered**: Making direct HTTP requests to the Last.fm API. This was rejected because `pylast` provides a more convenient and robust solution.
