import os
from atproto import Client

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")


def post_on_bluesky_thread(parts):
    """
    Postet die Teile eines Threads auf Bluesky:
    - Jeder Teil ist ein eigener Post
    - reply_to sorgt dafür, dass ein Thread entsteht
    """
    if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
        print("❌ BLUESKY_HANDLE oder BLUESKY_PASSWORD nicht gesetzt!")
        return

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

        reply_ref = None
        for idx, part in enumerate(parts):
            # Optional: Nummerierung für Thread-Teile
            thread_part = f"{part}" if len(parts) == 1 else f"{part} ({idx+1}/{len(parts)})"
            post = client.send_post(text=thread_part, reply_to=reply_ref)
            reply_ref = post  # Nächstes Teil antwortet auf diesen Post
        print(f"✅ Thread mit {len(parts)} Teilen erfolgreich gepostet!")
    except Exception as e:
        print("❌ Fehler beim Posten auf Bluesky:", e)
