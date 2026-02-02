# Quickstart: Gemini Suggestions

## Prerequisites
- **Gemini API Key**: You must have a Google Cloud project with the Gemini API enabled.
- **Environment Variable**: Set `GEMINI_API_KEY` in your `.env` file or shell.

```bash
export GEMINI_API_KEY="AIza..."
```

## Usage

### Standard Suggestions (Popular/Relevant)
To generate suggestions based on a Tidal playlist, use the `--gemini` flag:

```bash
python -m src.cli.main playlist --gemini -n 20 "My Source Playlist"
```
*This will generate 20 suggestions using the Gemini API based on the source playlist.*

### Deep Cuts (Shuffle Mode)
To ask the AI for less common, "underground", or deep-cut tracks, add the `--shuffle` flag:

```bash
python -m src.cli.main playlist --gemini --shuffle "My Source Playlist"
```

## Troubleshooting
- **Error: "API Key not found"**: Ensure `GEMINI_API_KEY` is set.
- **Warning: "Could not find track..."**: The AI suggested a song that could not be found in Tidal's database using the provided ISRC. This is normal behavior for some fuzzy matches.
