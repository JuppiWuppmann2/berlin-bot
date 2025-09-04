import os
import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from beautify import beautify_text
from bluesky import post_on_bluesky_thread

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
STATE_FILE = "data.json"

# ----------------------------- Selenium Scraper -----------------------------
def get_viz_updates():
    """Scrapt die aktuelle Baustellenliste von viz.berlin."""
    print("🔍 Scraper gestartet...")
    res = requests.get(URL, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    updates = []
    items = soup.select("li.construction-sites-item")
    print(f"Gefundene Meldungen insgesamt: {len(items)}")

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

            # nur nicht-leere Teile behalten → keine \n mehr
            parts = [title, description.strip(), zeitraum, location]
            message = " ".join([p for p in parts if p])  # Leerzeichen statt \n
            message = " ".join(message.split())  # Mehrfache Leerzeichen entfernen

            updates.append(message)
        except Exception as e:
            print("Fehler beim Parsen eines Eintrags:", e)
            continue

    return updates

# ----------------------------- State Management -----------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)

# ----------------------------- Main -----------------------------
def main():
    print("🚀 Bot gestartet...")
    prev_state = load_state()
    current_updates = set(get_viz_updates())

    # Neue Meldungen
    new_items = current_updates - prev_state
    print(f"Neue Meldungen: {len(new_items)}")
    for item in new_items:
        parts = beautify_text(item)
        print("➡ Neue Meldung:", parts)
        try:
            post_on_bluesky_thread(parts)
            print("✅ Erfolgreich auf Bluesky gepostet!")
        except Exception as e:
            print("❌ Fehler beim Posten auf Bluesky:", e)

    # Behobene Meldungen
    resolved_items = prev_state - current_updates
    print(f"Behobene Meldungen: {len(resolved_items)}")
    for item in resolved_items:
        parts = beautify_text(f"✅ Behoben: {item}")
        print("⬅ Behoben:", parts)
        try:
            post_on_bluesky_thread(parts)
            print("✅ Behoben auf Bluesky gepostet!")
        except Exception as e:
            print("❌ Fehler beim Posten Behoben:", e)

    save_state(current_updates)
    print("💾 State gespeichert.")

if __name__ == "__main__":
    main()
