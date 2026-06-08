with open('src/services/tidal_service.py', 'r') as f:
    data = f.read()

data = data.replace('''    target_folder = folder_id
    
    for attempt in range(max_retries + 1):
        try:
            playlist = session.user.create_playlist(unique_name, description, parent_id=target_folder)
            if track_ids:
                playlist.add([str(x) for x in track_ids])
            return playlist
            
        except (HTTPError, ObjectNotFound) as e:
            is_404 = False
            if isinstance(e, HTTPError) and e.response is not None and e.response.status_code == 404:
                is_404 = True
            elif isinstance(e, ObjectNotFound):
                is_404 = True
                
            # If folder is missing, fallback to root immediately
            if is_404 and target_folder != "root":
                click.echo(f"Warning: Folder {folder_id} not found. Falling back to root.")
                target_folder = "root"
                # When falling back to root, we revert to original name as collision scope changes,
                # or we could keep unique_name. Simplest is to reset or keep. 
                # Let's keep unique_name to avoid confusion or reset to name?
                # The requirements don't specify, but resetting to 'name' seems safer as 'name (1)' might not exist in root.
                unique_name = name 
                continue

            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise''', '''    target_folder = folder_id
    created_playlist_id = None
    
    for attempt in range(max_retries + 1):
        try:
            if not created_playlist_id:
                playlist = session.user.create_playlist(unique_name, description, parent_id=target_folder)
            else:
                playlist = tidalapi.playlist.UserPlaylist(session, created_playlist_id)

            if track_ids:
                playlist.add([str(x) for x in track_ids])
            return playlist
            
        except (HTTPError, ObjectNotFound) as e:
            is_folder_404 = False
            
            if isinstance(e, ObjectNotFound):
                msg = str(e)
                match = re.search(r"Playlist with id (.*) not found", msg)
                if match:
                    created_playlist_id = match.group(1)
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                else:
                    is_folder_404 = True
            elif isinstance(e, HTTPError) and getattr(e, 'response', None) is not None and e.response.status_code == 404:
                if not created_playlist_id:
                    is_folder_404 = True
                    
            if is_folder_404 and target_folder != "root":
                click.echo(f"Warning: Folder {folder_id} not found. Falling back to root.")
                target_folder = "root"
                unique_name = name 
                continue

            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise''')

with open('src/services/tidal_service.py', 'w') as f:
    f.write(data)
