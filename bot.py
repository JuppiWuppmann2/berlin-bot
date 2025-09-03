import os
import json
import time
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
            title = li.find_element(By.TAG_NAME, "strong").text

            span_texts = [span.text for span in li.find_elements(By.TAG_NAME, "span")]
            zeitraum = next((t.replace("Zeitraum:", "").strip() for t in span_texts if "Zeitraum" in t), "")
            location = next((t.replace("Straße:", "").strip() for t in span_texts if "Straße" in t), "")
            description = " ".join([t for t in span_texts if "Zeitraum" not in t and "Straße" not in t])

            message = f"{title}\n{description}\n{zeitraum}\n{location}"
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
