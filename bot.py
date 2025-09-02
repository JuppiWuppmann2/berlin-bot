import os
import time
import threading
from flask import Flask
from playwright.sync_api import sync_playwright
from viz import get_viz_updates
from bluesky import get_bluesky_posts

# Flask Webserver für UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot läuft!"

def run_webserver():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_webserver).start()


def post_on_x(text):
    username = os.getenv("X_USERNAME")
    password = os.getenv("X_PASSWORD")

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

        # Text ins Postfeld tippen
        page.click('div[aria-label="Was gibt’s Neues?"]')
        page.keyboard.type(text)

        # Tweet-Button klicken
        page.click('div[data-testid="tweetButtonInline"]')

        browser.close()


def main_loop():
    seen_viz = set()
    seen_bluesky = set()

    while True:
        # VIZ prüfen
        for update in get_viz_updates():
            if update not in seen_viz:
                print(f"Poste VIZ: {update}")
                post_on_x(update)
                seen_viz.add(update)

        # Bluesky prüfen
        for post in get_bluesky_posts():
            if post not in seen_bluesky:
                print(f"Poste Bluesky: {post}")
                post_on_x(post)
                seen_bluesky.add(post)

        time.sleep(300)  # alle 5 Minuten


if __name__ == "__main__":
    main_loop()
