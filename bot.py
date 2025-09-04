import os
import json
import time
import requests
import re
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

# ----------------------------- Helper: Normalisierung -----------------------------
def normalize_message(message: str) -> str:
    """Normiert Meldungen für stabilen Vergleich im State-File."""
    msg = message.lower().strip()
    msg = re.sub(r"\s+", " ", msg)  # Mehrfach-Leerzeichen → einfaches Leerzeichen
    msg = msg.replace(" | ", "|")   # Trenner vereinheitlichen
    return msg

# ----------------------------- Selenium Scraper -----------------------------
def get_viz_updates():
    print("🔍 Scraper gestartet...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL)
    time.sleep(5)  # JS laden lassen

    updates = []
    items = driver.find_elements(By.CSS_SELECTOR, "li.construction-sites-item")
    print(f"Gefundene Meldungen insgesamt: {len(items)}")

    for li in items:
        try:
            title = li.find_element(By.TAG_NAME, "strong").text.strip()
            span_texts = [span.text.strip() for span in li.find_elements(By.TAG_NAME, "span")]

            zeitraum = next((t.replace("Zeitraum:", "").strip() for t in span_texts if "Zeitraum" in t), "")
            location = next((t.replace("Straße:", "").strip() for t in span_texts if "Straße" in t), "")
            description = " | ".join([t for t in span_texts if "Zeitraum" not in t and "Straße" not in t])

            # Nachricht zusammenbauen
            parts = [title, description, zeitraum, location]
            message = " | ".join([p for p in parts if p])

            updates.append(message)
        except Exception as e:
            print("Fehler beim Verarbeiten eines Eintrags:", e)
            continue

    driver.quit()
    return updates


# ----------------------------- State Management -----------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # direkt normalisieren
            return set(normalize_message(item) for item in data)
    return set()


def save_state(state):
    """Speichert bereits normalisierte Meldungen"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(state)), f, ensure_ascii=False, indent=2)


# ----------------------------- Main -----------------------------
def main():
    print("🚀 Bot gestartet...")
    prev_state = load_state()

    raw_updates = get_viz_updates()
    current_updates = set(normalize_message(u) for u in raw_updates)

    # Neue Meldungen
    new_items = current_updates - prev_state
    print(f"Neue Meldungen: {len(new_items)}")
    for norm_item in new_items:
        # Ursprünglichen Text finden (für Beautify)
        orig_item = next(u for u in raw_updates if normalize_message(u) == norm_item)
        parts = beautify_text(orig_item)
        print("➡ Neue Meldung:", parts)
        try:
            post_on_bluesky_thread(parts)
            print("✅ Erfolgreich auf Bluesky gepostet!")
            time.sleep(2)  # etwas längere Pause gegen Rate-Limits
        except Exception as e:
            print("❌ Fehler beim Posten auf Bluesky:", e)

    # Behobene Meldungen
    resolved_items = prev_state - current_updates
    print(f"Behobene Meldungen: {len(resolved_items)}")
    for norm_item in resolved_items:
        parts = beautify_text(f"✅ Behoben: {norm_item}")
        print("⬅ Behoben:", parts)
        try:
            post_on_bluesky_thread(parts)
            print("✅ Behoben auf Bluesky gepostet!")
            time.sleep(2)
        except Exception as e:
            print("❌ Fehler beim Posten Behoben:", e)

    # Nur normalisierte Meldungen speichern
    save_state(current_updates)
    print("💾 State gespeichert.")


if __name__ == "__main__":
    main()
