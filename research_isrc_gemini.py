import tidalapi
import inspect

print("TidalAPI Version:", getattr(tidalapi, '__version__', 'unknown'))

print("\n--- Inspecting tidalapi.Session.search ---")
try:
    if hasattr(tidalapi.Session, 'search'):
        sig = inspect.signature(tidalapi.Session.search)
        print(f"Signature: {sig}")
        print(inspect.getdoc(tidalapi.Session.search))
    else:
        print("tidalapi.Session.search not found.")
except Exception as e:
    print(f"Error inspecting search: {e}")

print("\n--- Checking google-generativeai ---")
try:
    import google.generativeai as genai
    print("google.generativeai imported successfully.")
    print("Version:", getattr(genai, '__version__', 'unknown'))
except ImportError:
    print("google.generativeai NOT installed.")
except Exception as e:
    print(f"Error importing google.generativeai: {e}")
