import re
msg = "Playlist with id 2a81e97a-cf8a-4d1e-b317-f940258b142e not found"
match = re.search(r"Playlist with id (.*) not found", msg)
print(match.group(1) if match else "None")
