import os
import time
import requests
import threading
from flask import Flask
from viz import get_viz_updates
from bluesky import post_on_bluesky_thread
from post_x import post_on_x
from beautify import beautify_text
import json

GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# Lokale Speicherung im Projektverzeichnis
STATE_FILE = "data.json"

# Flask für Render + UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot läuft!"

def run_webserver():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_webserver).start()


def load_state():
    """Lädt state lokal oder von GitHub Gist."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    if GIST_ID and GITHUB_TOKEN:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        url = f"https://api.github.com/gists/{GIST_ID}"
        res = requests.get(url, headers=headers)
        if res.ok:
            files = res.json().get("files", {})
            if "data.json" in files:
                content = files["data.json"]["content"]
                return set(json.loads(content))
    return set()

def save_state(state):
    """Speichert state lokal und auf GitHub Gist."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)
    if GIST_ID and GITHUB_TOKEN:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        url = f"https://api.github.com/gists/{GIST_ID}"
        data = {"files": {"data.json": {"content": json.dumps(list(state), ensure_ascii=False, indent=2)}}}
        requests.patch(url, headers=headers, json=data)

def main_loop():
    prev_state = load_state()

    while True:
        try:
            current_updates = set(get_viz_updates())
        except Exception as e:
            print(f"Fehler beim Abrufen der VIZ-Daten: {e}")
            time.sleep(300)
            continue

        # Neue Meldungen
        new_items = current_updates - prev_state
        for item in new_items:
            message = beautify_text(item)
            print(f"Neue Meldung: {message}")

            try:
                post_on_x(message)
            except Exception as e:
                print(f"Fehler beim Posten auf X: {e}")

            try:
                post_on_bluesky_thread(message)
            except Exception as e:
                print(f"Fehler beim Posten auf Bluesky: {e}")

        # Verschwundene Meldungen -> "Behoben"
        resolved_items = prev_state - current_updates
        for item in resolved_items:
            message = f"✅ Behoben: {item}\n\n#Berlin #Verkehr #Baustelle #Störung"
            print(f"Behoben: {message}")

            try:
                post_on_x(message)
            except Exception as e:
                print(f"Fehler beim Posten auf X (behoben): {e}")

            try:
                post_on_bluesky_thread(message)
            except Exception as e:
                print(f"Fehler beim Posten auf Bluesky (behoben): {e}")

        prev_state = current_updates
        save_state(prev_state)

        time.sleep(300)  # alle 5 Minuten


if __name__ == "__main__":
    main_loop()
