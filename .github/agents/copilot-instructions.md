# tidal-discovery-engine Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-19

## Active Technologies
- Python 3.12+ + click, python-dotenv, google-genai, pydantic (006-gemini-model-env)
- N/A (runtime env-based configuration only) (006-gemini-model-env)
- Python 3.12+ + click, tidalapi, pylast, python-dotenv, google-genai (007-gemini-mode3-support)
- N/A (runtime CLI orchestration with external APIs) (007-gemini-mode3-support)
- Markdown documentation for a Python 3.11 CLI project + Existing CLI behavior and options in `src/cli/main.py`; no new runtime dependencies (008-overhaul-feature-docs)
- N/A (repository markdown files only) (008-overhaul-feature-docs)
- Python 3.12+ + click, tidalapi, pylast, python-dotenv, google-genai; internal services in `src/services/` (010-exclude-favorite-tracks)
- In-memory exclusion snapshot only (no new persistent storage) (010-exclude-favorite-tracks)
- N/A; retry and classification state are in-memory only for a single CLI run (011-harden-gemini-responses)

- (003-custom-playlist-folder)

## Project Structure

```text
src/
tests/
```

## Commands

# Add commands for 

## Code Style

: Follow standard conventions

## Recent Changes
- 011-harden-gemini-responses: Added Python 3.12+ + click, tidalapi, pylast, python-dotenv, google-genai; internal services in `src/services/`
- 011-harden-gemini-responses: Added Python 3.12+ + click, tidalapi, pylast, python-dotenv, google-genai; internal services in `src/services/`
- 010-exclude-favorite-tracks: Added Python 3.12+ + click, tidalapi, pylast, python-dotenv, google-genai; internal services in `src/services/`


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
