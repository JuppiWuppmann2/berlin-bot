import requests
import os
import datetime
import textwrap

BSKY_API = "https://bsky.social/xrpc"

def get_session():
    handle = os.getenv("BSKY_HANDLE")
    app_password = os.getenv("BSKY_APP_PASSWORD")

    res = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
    )
    res.raise_for_status()
    return res.json()["accessJwt"]

def post_on_bluesky(text):
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

def split_into_posts(text, max_length=300):
    parts = textwrap.wrap(text, width=max_length-10, break_long_words=False)
    posts = []
    for i, part in enumerate(parts, start=1):
        if len(parts) > 1:
            posts.append(f"{part} ({i}/{len(parts)})")
        else:
            posts.append(part)
    return posts

def post_on_bluesky_thread(text):
    posts = split_into_posts(text)
    results = []
    for post in posts:
        results.append(post_on_bluesky(post))
    return results

