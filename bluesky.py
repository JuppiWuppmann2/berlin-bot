import os
from atproto import Client

USERNAME = os.getenv("BLUESKY_USERNAME")
PASSWORD = os.getenv("BLUESKY_PASSWORD")

def post_on_bluesky_thread(messages):
    """messages = Liste von Textteilen (wegen 280 Zeichen Split)"""
    if not USERNAME or not PASSWORD:
        print("⚠️ Bluesky Zugangsdaten fehlen! Bitte Environment Variables setzen.")
        return

    client = Client()
    try:
        client.login(USERNAME, PASSWORD)
        root = None
        for msg in messages:
            root = client.send_post(msg, reply_to=root)
        print("✅ Auf Bluesky gepostet:", messages)
    except Exception as e:
        print("❌ Fehler beim Posten auf Bluesky:", e)
