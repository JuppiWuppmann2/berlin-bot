import os
from atproto import Client

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

def post_on_bluesky_thread(parts):
    """Postet die Teile eines Threads auf Bluesky."""
    if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
        print("❌ BLUESKY_HANDLE oder BLUESKY_PASSWORD nicht gesetzt!")
        return

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        reply_ref = None
        for part in parts:
            post = client.send_post(text=part, reply_to=reply_ref)
            reply_ref = post
    except Exception as e:
        print("❌ Fehler beim Bluesky Post:", e)
