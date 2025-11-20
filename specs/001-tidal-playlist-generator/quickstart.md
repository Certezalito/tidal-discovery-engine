# Quickstart: Tidal Playlist Generator

## Setup

1.  Clone the repository.
2.  Install dependencies with `uv`: `uv pip install -r requirements.txt`
3.  Create a `.env` file and add your Tidal and Last.fm API credentials.

## Usage

Run the CLI tool with the following command:

```bash
python src/cli/main.py --num-tidal-tracks 10 --num-similar-tracks 5 --playlist-name "My Awesome Playlist"
```
