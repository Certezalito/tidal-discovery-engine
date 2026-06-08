with open('src/services/genre_playlist_service.py', 'r') as f:
    data = f.read()

# Replace genres array with single genre
data = data.replace('genres = result.get("genres", [])', 'genre = result.get("genre")')
data = data.replace('''            if key:
                genre_cache[key] = genres
                
            if not genres:
                unknown_track_ids.append(track.id)
                summary.unknown_tracks += 1
            else:
                summary.classified_tracks += 1
                for genre in genres:
                    # Normalize genre string for consistent keys
                    genre_key = genre.strip()
                    if genre_key not in genre_groups:
                        genre_groups[genre_key] = []
                    genre_groups[genre_key].append(track.id)''', '''            if not genre:
                unknown_track_ids.append(track.id)
                summary.unknown_tracks += 1
            else:
                # Save to cache only on hit
                if key:
                    genre_cache[key] = genre

                summary.classified_tracks += 1
                genre_key = genre.strip()
                if genre_key not in genre_groups:
                    genre_groups[genre_key] = []
                genre_groups[genre_key].append(track.id)''')

data = data.replace('genres = genre_cache[key]', 'genre = genre_cache[key]')
data = data.replace('''            if not genres:
                unknown_track_ids.append(t.id)
                summary.unknown_tracks += 1
            else:
                summary.classified_tracks += 1
                for genre in genres:
                    genre_key = genre.strip()
                    if genre_key not in genre_groups:
                        genre_groups[genre_key] = []
                    genre_groups[genre_key].append(t.id)''', '''            if not genre:
                unknown_track_ids.append(t.id)
                summary.unknown_tracks += 1
            else:
                summary.classified_tracks += 1
                genre_key = genre.strip()
                if genre_key not in genre_groups:
                    genre_groups[genre_key] = []
                genre_groups[genre_key].append(t.id)''')

with open('src/services/genre_playlist_service.py', 'w') as f:
    f.write(data)
