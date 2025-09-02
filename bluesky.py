from bskypy import Client
import os

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
    raise Exception("Bluesky Handle oder Passwort nicht gesetzt! Setze BLUESKY_HANDLE und BLUESKY_PASSWORD als Umgebungsvariablen.")

client = Client()
try:
    client.login(identifier=BLUESKY_HANDLE, password=BLUESKY_PASSWORD)
    print(f"[Bluesky] Eingeloggt als {BLUESKY_HANDLE}")
except Exception as e:
    raise Exception(f"Fehler beim Einloggen auf Bluesky: {e}")

def post_on_bluesky_thread(message_parts):
    for part in message_parts:
        try:
            client.post_create(text=part)
            print(f"[Bluesky] gepostet: {part}")
        except Exception as e:
            print(f"Fehler beim Posten auf Bluesky: {e}")
