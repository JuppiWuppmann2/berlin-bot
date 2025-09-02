import requests
import os
import base64
import datetime

BSKY_API = "https://bsky.social/xrpc"

def get_session():
    """Erstellt eine Session mit Bluesky (JWT holen)."""
    handle = os.getenv("BSKY_HANDLE")
    app_password = os.getenv("BSKY_APP_PASSWORD")

    res = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
    )
    res.raise_for_status()
    return res.json()["accessJwt"]

def post_on_bluesky(text):
    """Postet einen Text auf Bluesky."""
    jwt = get_session()
    headers = {"Authorization": f"Bearer {jwt}"}

    data = {
        "collection": "app.bsky.feed.post",
        "repo": os.getenv("BSKY_HANDLE"),
        "record": {
            "text": text,
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
            "$type": "app.bsky.feed.post",
        },
    }

    res = requests.post(f"{BSKY_API}/com.atproto.repo.createRecord", json=data, headers=headers)
    res.raise_for_status()
    return res.json()
