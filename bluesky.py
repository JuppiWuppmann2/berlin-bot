from atproto import Client
import os

BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

client = Client()
client.login(BSKY_HANDLE, BSKY_PASSWORD)

def post_on_bluesky_thread(text: str):
    client.send_post(text)
