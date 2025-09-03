import os
from atproto import Client

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

def post_on_bluesky_thread(parts):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

    reply_ref = None
    for part in parts:
        post = client.send_post(text=part, reply_to=reply_ref)
        reply_ref = post
