import os
import json
import time
import requests
import re
import unicodedata
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.support.ui import WebDriverWait
from selenium.webdriver.common.support import expected_conditions as EC
from selenium.webdriver.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from beautify import beautify_text
from bluesky import post_on_bluesky_thread

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
STATE_FILE = "data.json"

# ----------------------------- Helper: Normalisierung -----------------------------
def normalize_message(message: str) -> str:
    """Normiert Meldungen für stabilen Vergleich im State-File."""
    msg = message.lower().strip()

    # Unsichtbare Unicode-Zeichen entfernen
    msg = msg.replace("\u200b", "").replace("\xa0", " ")

    # Emojis und Symbole entfernen
    msg = "".join(ch for ch in msg if not unicodedata.category(ch).startswith("So"))

    # Erlaubte Zeichen (Buchstaben, Zahlen, Umlaute, Satzzeichen, Trenner)
    msg = re.sub(r"[^a-z0-9äöüß|,.:;\/\- ]+", " ", msg)

    # Mehrfach-Leerzeichen und Trenner vereinheitlichen
    msg = re.sub(r"\s+", " ", msg).strip()
    msg = msg.replace(" | ", "|")

    return msg

# ----------------------------- Selenium Scraper -----------------------------
def get_viz_updates():
    print("🔍 Scraper gestartet...")
    options = Options()
    # Stabilere Headless-Einstellungen für CI-Umgebungen
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(URL)
        # Warten, bis mindestens ein Eintrag geladen ist (max. 30 Sekunden)
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.construction-sites-item"))
        )
    except TimeoutException:
        print("⚠️ Timeout beim Laden der Meldungen – Seite konnte nicht vollständig geladen werden")
        driver.quit()
        return []

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
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = f.read().strip()
                if not data:  # Datei leer
                    return set()
                return set(json.loads(data))
        except (json.JSONDecodeError, ValueError):
            print("⚠️ Warnung: Konnte data.json nicht lesen – Datei wird zurückgesetzt.")
            return set()
    return set()


def save_state(state):
    """Speichert bereits normalisierte Meldungen"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(state)), f, ensure_ascii=False, indent=2)


# ----------------------------- Main -----------------------------
def main():
    print("🚀 Bot gestartet...")
    prev_state = load_state()
    print(f"📂 Bisher gespeicherte Meldungen: {len(prev_state)}")

    raw_updates = get_viz_updates()
    current_updates = set(normalize_message(u) for u in raw_updates)

    # Debug: zeige Beispiel Normalisierung
    print("🔎 Beispiel Normalisierung (erste 3 Meldungen):")
    for u in raw_updates[:3]:
        print("RAW :", u)
        print("NORM:", normalize_message(u))

    # Neue Meldungen
    new_items = current_updates - prev_state
    print(f"Neue Meldungen: {len(new_items)}")
    for norm_item in new_items:
        orig_item = next(u for u in raw_updates if normalize_message(u) == norm_item)
        parts = beautify_text(orig_item)
        print("➡ Neue Meldung:", parts)
        try:
            post_on_bluesky_thread(parts)
            print("✅ Erfolgreich auf Bluesky gepostet!")
            time.sleep(5)  # längere Pause gegen Rate-Limits
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
            time.sleep(5)
        except Exception as e:
            print("❌ Fehler beim Posten Behoben:", e)

    # Nur normalisierte Meldungen speichern
    save_state(current_updates)
    print("💾 State gespeichert.")


if __name__ == "__main__":
    main()
