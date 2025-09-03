import os
import json
import time
import requests
from bs4 import BeautifulSoup
from beautify import beautify_text
from bluesky import post_on_bluesky_thread

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
STATE_FILE = "data.json"


def get_viz_updates():
    """Scrapt die aktuelle Baustellenliste von viz.berlin."""
    res = requests.get(URL, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    updates = []
    items = soup.select("li.construction-sites-item")

    for li in items:
        try:
            title = li.select_one("strong").get_text(strip=True)
            span_tags = li.select("span")
            zeitraum = ""
            location = ""
            description = ""

            for span in span_tags:
                text = span.get_text(strip=True)
                if text.startswith("Zeitraum:"):
                    zeitraum = text.replace("Zeitraum:", "").strip()
                elif text.startswith("Straße:"):
                    location = text.replace("Straße:", "").strip()
                else:
                    description += text + " "

            message = f"{title}\n{description.strip()}\n{zeitraum}\n{location}"
            updates.append(message)
        except Exception as e:
            print("Fehler beim Parsen:", e)
            continue

    return updates


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)


def main():
    prev_state = load_state()
    current_updates = set(get_viz_updates())

    # Neue Meldungen
    new_items = current_updates - prev_state
    for item in new_items:
        parts = beautify_text(item)
        print("Neue Meldung:", parts)
        post_on_bluesky_thread(parts)

    # Behobene Meldungen
    resolved_items = prev_state - current_updates
    for item in resolved_items:
        parts = beautify_text(f"✅ Behoben: {item}")
        print("Behoben:", parts)
        post_on_bluesky_thread(parts)

    save_state(current_updates)


if __name__ == "__main__":
    main()
