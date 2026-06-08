import re

with open('specs/012-genre-playlists/tasks.md', 'r') as f:
    content = f.read()

# Fix the lack of hyphen in the checkboxes so it properly renders as markdown checkboxes
content = re.sub(r'^\[([ x])\] ', r'- [\1] ', content, flags=re.MULTILINE)

# Add T001b
content = content.replace('- [x] T001 Add genre-playlist CLI options and command path in src/cli/main.py', '- [x] T001 Add genre-playlist CLI options and command path in src/cli/main.py\n- [ ] T001b Add `--min-genre-size` CLI option with default of 2 in src/cli/main.py')

# Update US1 Goal & Independent Test
content = re.sub(r'\*\*Goal\*\*: Build genre playlists from the full Tidal library using Gemini, enforcing a single best-match genre per track, handling Unknown fallback, and caching classifications locally while bypassing Unknowns\.', '**Goal**: Build genre playlists from the full Tidal library using Gemini, enforcing a single best-match genre per track, handling Unknown fallback, grouping niche genres into "Others", sorting by ascending track count, and caching classifications locally while bypassing Unknowns.', content)
content = re.sub(r'\*\*Independent Test\*\*: Run the genre-playlist command against a test library and verify folder creation, genre playlists, single-genre placement per track, local cache creation, and Unknown handling\.', '**Independent Test**: Run the genre-playlist command against a test library and verify folder creation, genre playlists, single-genre placement per track, local cache creation, Unknown handling, "Others" grouping threshold, and ascending track count processing order.', content)

# Add T010b, T011d
content = content.replace('- [x] T010 [P] [US1] Add CLI test for first-run folder and genre playlist creation in tests/test_cli.py', '- [x] T010 [P] [US1] Add CLI test for first-run folder and genre playlist creation in tests/test_cli.py\n- [ ] T010b [P] [US1] Add CLI test for `--min-genre-size` threshold grouping into "Others" in tests/test_cli.py')
content = content.replace('- [x] T011c [P] [US1] Add service test verifying local JSON/DB cache write on classification hit and bypass on Unknown miss in tests/test_genre_playlist_service.py', '- [x] T011c [P] [US1] Add service test verifying local JSON/DB cache write on classification hit and bypass on Unknown miss in tests/test_genre_playlist_service.py\n- [ ] T011d [P] [US1] Add service test verifying playlist orchestration executes in ascending track count order in tests/test_genre_playlist_service.py')

# Add T012c, T012d
content = content.replace('- [x] T012b [US1] Implement local cache read/write adapter (file or DB) for Gemini classifications in src/services/genre_playlist_service.py', '- [x] T012b [US1] Implement local cache read/write adapter (file or DB) for Gemini classifications in src/services/genre_playlist_service.py\n- [ ] T012c [US1] Implement "Others" grouping logic for genre groups below the `--min-genre-size` threshold in src/services/genre_playlist_service.py\n- [ ] T012d [US1] Implement sorting of genre groups by ascending track count prior to playlist processing in src/services/genre_playlist_service.py')

# Update US2 Goal
content = re.sub(r'\*\*Goal\*\*: Re-run the command and sync existing genre playlists by adding new library tracks and removing tracks no longer in the library\.', '**Goal**: Re-run the command and sync existing genre playlists by adding new library tracks and removing tracks no longer in the library, processing in ascending track count order.', content)

# Add T023b
content = content.replace('- [x] T023 Update end-user usage and behavior notes for genre workflow in README.md', '- [x] T023 Update end-user usage and behavior notes for genre workflow in README.md\n- [ ] T023b Update README.md to document `--min-genre-size` usage, "Others" grouping, and "Updated date" sorting behavior')

with open('specs/012-genre-playlists/tasks.md', 'w') as f:
    f.write(content)
