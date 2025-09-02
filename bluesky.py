import requests

def get_bluesky_posts():
    url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
    params = {"actor": "vizberlin.bsky.social"}
    res = requests.get(url, params=params)
    data = res.json()

    posts = []
    for post in data.get("feed", []):
        text = post["post"]["record"].get("text", "")
        if text:
            posts.append(text)

    return posts[:5]
