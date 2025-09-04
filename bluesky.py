from atproto import Client
import os

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

client = Client()
client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

def post_on_bluesky_thread(parts):
    """Postet eine Nachricht oder Thread auf Bluesky."""
    reply_to = None
    for part in parts:
        post = client.post(text=part, reply_to=reply_to)
        reply_to = post.uri
