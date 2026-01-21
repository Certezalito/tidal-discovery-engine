import tidalapi
import inspect

try:
    # Usually create_playlist is on the User object or Playlist object.
    # In recent tidalapi, it might be on User.
    
    # Let's inspect the User class
    print("Inspecting tidalapi.User...")
    if hasattr(tidalapi.User, 'create_playlist'):
        print("\n--- create_playlist docstring ---")
        print(inspect.getdoc(tidalapi.User.create_playlist))
        print("\n--- create_playlist source ---")
        try:
            print(inspect.getsource(tidalapi.User.create_playlist))
        except Exception as e:
            print(f"Could not get source: {e}")
    else:
        print("tidalapi.User.create_playlist not found")

    if hasattr(tidalapi.User, 'create_folder'):
        print("\n--- create_folder docstring ---")
        print(inspect.getdoc(tidalapi.User.create_folder))
        print("\n--- create_folder source ---")
        try:
            print(inspect.getsource(tidalapi.User.create_folder))
        except Exception as e:
            print(f"Could not get source: {e}")
    else:
        print("tidalapi.User.create_folder not found")

except Exception as e:
    print(f"Error: {e}")
