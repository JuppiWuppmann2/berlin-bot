from bskypy import Client
import os

client = Client()
client.login(os.getenv("BLUESKY_HANDLE"), os.getenv("BLUESKY_PASSWORD"))

def post_on_bluesky_thread(message_parts):
    for part in message_parts:
        try:
            client.post_create(text=part)
            print(f"[Bluesky] gepostet: {part}")
        except Exception as e:
            print(f"Fehler beim Posten auf Bluesky: {e}")
