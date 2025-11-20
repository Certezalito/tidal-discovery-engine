import pylast
from src.lib.auth import get_lastfm_api_key

def get_network():
    return pylast.LastFMNetwork(api_key=get_lastfm_api_key())

def get_similar_tracks(network, track, num_tracks):
    """Gets similar tracks for a Last.fm track object."""
    similar = track.get_similar(limit=num_tracks)
    return [item.item for item in similar]

def get_top_tags_for_artist(network, artist_name, limit=3):
    """Gets the top tags for an artist."""
    artist = network.get_artist(artist_name)
    top_tags = artist.get_top_tags(limit=limit)
    return [tag.item.name for tag in top_tags]
