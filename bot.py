import os
import time
import threading
import textwrap
from flask import Flask
from playwright.sync_api import sync_playwright
from viz import get_viz_updates
from bluesky import post_on_bluesky

# Basis-Hashtags (immer gleich)
BASE_HASHTAGS = "#Berlin #Verkehr #Baustelle #Störung"

# Keywords → extra Emojis/Hashtags
KEYWORD_MAP = {
    "Bus": {"emoji": "🚌", "hashtags": "#ÖPNV"},
    "U-Bahn": {"emoji": "🚇", "hashtags": "#ÖPNV"},
    "S-Bahn": {"emoji": "🚆", "hashtags": "#ÖPNV"},
    "Straße": {"emoji": "🚧", "hashtags": "#Baustelle"},
    "Autobahn": {"emoji": "🛣️", "hashtags": "#Autobahn"},
    "Störung": {"emoji": "⚠️", "hashtags": "#Störung"},
    "Sperrung": {"emoji": "⛔", "hashtags": "#Sperrung"},
}

# Flask Webserver für UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot läuft!"

def run_webserver():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_webserver).start()


def beautify_text(text: str) -> str:
    """Fügt Emojis & feste Hashtags hinzu, erkennt Keywords."""
    emojis = []
    extra_tags = []

    for key, val in KEYWORD_MAP.items():
        if key.lower() in text.lower():
            emojis.append(val["emoji"])
            extra_tags.append(val["hashtags"])

    # Falls keine speziellen Emojis erkannt → Standard
    if not emojis:
        emojis = ["ℹ️"]

    all_hashtags = f"{BASE_HASHTAGS} {' '.join(set(extra_tags))}".strip()
    return f"{' '.join(emojis)} {text}\n\n{all_hashtags}"


def split_into_tweets(text, max_length=280):
    """Splittet lange Texte in mehrere Tweets (Thread)."""
    parts = textwrap.wrap(text, width=max_length-10, break_long_words=False)
    tweets = []
    for i, part in enumerate(parts, start=1):
        if len(parts) > 1:
            tweets.append(f"{part} ({i}/{len(parts)})")
        else:
            tweets.append(part)
    return tweets


def post_on_x(text):
    username = os.getenv("X_USERNAME")
    password = os.getenv("X_PASSWORD")

    tweets = split_into_tweets(text)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Login
        page.goto("https://x.com/login")
        page.fill('input[name="text"]', username)
        page.keyboard.press("Enter")
        page.wait_for_selector('input[name="password"]')
        page.fill('input[name="password"]', password)
        page.keyboard.press("Enter")

        # Eingabefeld abwarten
        page.wait_for_selector('div[aria-label="Was gibt’s Neues?"]')

        # Ersten Tweet schreiben
        page.click('div[aria-label="Was gibt’s Neues?"]')
        page.keyboard.type(tweets[0])
        page.click('div[data-testid="tweetButtonInline"]')
        page.wait_for_timeout(2000)

        # Falls Thread notwendig → weitere Tweets anhängen
        for t in tweets[1:]:
            page.click('div[data-testid="reply"]')
            page.wait_for_selector('div[aria-label="Was gibt’s Neues?"]')
            page.click('div[aria-label="Was gibt’s Neues?"]')
            page.keyboard.type(t)
            page.click('div[data-testid="tweetButtonInline"]')
            page.wait_for_timeout(2000)

        browser.close()


def main_loop():
    seen_viz = set()

    while True:
        for update in get_viz_updates():
            if update not in seen_viz:
                message = beautify_text(update)
                print(f"Poste VIZ: {message}")

                try:
                    post_on_x(message)          # auf X posten
                except Exception as e:
                    print(f"Fehler beim Posten auf X: {e}")

                try:
                    post_on_bluesky(message)    # auf Bluesky posten
                except Exception as e:
                    print(f"Fehler beim Posten auf Bluesky: {e}")

                seen_viz.add(update)

        time.sleep(300)  # alle 5 Minuten


if __name__ == "__main__":
    main_loop()
