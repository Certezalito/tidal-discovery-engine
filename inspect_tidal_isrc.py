import tidalapi
import inspect

print("--- Inspecting tidalapi ---")

# Check Session.search
if hasattr(tidalapi.Session, 'search'):
    print("\n[+] Session.search exists")
    sig = inspect.signature(tidalapi.Session.search)
    print(f"Signature: {sig}")
    print(f"Docstring: {tidalapi.Session.search.__doc__}")
else:
    print("\n[-] Session.search missing")

# Check for ISRC
print("\n[+] Searching for ISRC/isrc in dir(tidalapi) and subclasses...")
found = False

def check_obj(name, obj):
    global found
    for x in dir(obj):
        if 'isrc' in x.lower():
            print(f"Found: {name}.{x}")
            found = True

check_obj("tidalapi", tidalapi)
if hasattr(tidalapi, 'Session'):
    check_obj("tidalapi.Session", tidalapi.Session)
if hasattr(tidalapi, 'media'):
    check_obj("tidalapi.media", tidalapi.media)
    if hasattr(tidalapi.media, 'Track'):
        check_obj("tidalapi.media.Track", tidalapi.media.Track)

if not found:
    print("No obvious ISRC references found in top-level, Session, or media.Track")
