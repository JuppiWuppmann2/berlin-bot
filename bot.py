import os
import time
import threading
from flask import Flask
from viz import get_viz_updates
from bluesky import post_on_bluesky_thread
from post_x import post_on_x
from beautify import beautify_text
import json

STATE_FILE = "/data/data.json"  # Persistente Speicherung auf Render Disk

# Flask für Render + UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot läuft!"

def run_webserver():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_webserver).start()


def load_state():
    """Lädt bekannten Zustand (alle Meldungen)."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_state(state):
    """Speichert aktuellen Zustand."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)


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
