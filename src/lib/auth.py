import os
from dotenv import load_dotenv

load_dotenv()

def get_lastfm_api_key():
    return os.getenv("LASTFM_API_KEY")
