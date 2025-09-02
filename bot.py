import os
import time
import threading
import json
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests

from bluesky import post_on_bluesky_thread
from beautify import beautify_text

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
STATE_FILE = "data.json"
POST_MAX_LEN = 280

# Optional: GitHub Gist für persistenten State
GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ----------------------------- Flask Webserver -----------------------------
app = Flask(__name__)
@app.route("/")
def home():
    return "Bluesky Bot läuft!"

def run_webserver():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_webserver).start()

# ----------------------------- Selenium Scraper -----------------------------
def get_viz_updates():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL)
    time.sleep(5)  # JS laden lassen

    updates = []
    items = driver.find_elements(By.CSS_SELECTOR, "li.construction-sites-item")
    print(f"Gefundene Meldungen: {len(items)}")

    for li in items:
        try:
            title = li.find_element(By.TAG_NAME, "strong").text
            span_texts = [span.text for span in li.find_elements(By.TAG_NAME, "span")]
            description = " ".join([t for t in span_texts if "Zeitraum" not in t and "Straße" not in t])
            period = next((t.replace("Zeitraum:", "").strip() for t in span_texts if "Zeitraum" in t), "")
            location = next((t.replace("Straße:", "").strip() for t in span_texts if "Straße" in t), "")
            message = f"{title}\n{description}\n{period}\n{location}"
            updates.append(message)
        except Exception as e:
            print("Fehler beim Verarbeiten:", e)
            continue

    driver.quit()
    return updates

# ----------------------------- State Management -----------------------------
def load_state():
    # zuerst lokal laden
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    # dann Gist laden falls gesetzt
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
    # lokal speichern
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)
    # optional Gist speichern
    if GIST_ID and GITHUB_TOKEN:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        url = f"https://api.github.com/gists/{GIST_ID}"
        data = {"files": {"data.json": {"content": json.dumps(list(state), ensure_ascii=False, indent=2)}}}
        requests.patch(url, headers=headers, json=data)

# ----------------------------- Main Loop -----------------------------
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
            parts = beautify_text(item)
            print(f"Neue Meldung: {parts}")
            post_on_bluesky_thread(parts)

        # Behobene Meldungen
        resolved_items = prev_state - current_updates
        for item in resolved_items:
            parts = beautify_text(f"✅ Behoben: {item}")
            print(f"Behoben: {parts}")
            post_on_bluesky_thread(parts)

        prev_state = current_updates
        save_state(prev_state)
        time.sleep(300)

if __name__ == "__main__":
    main_loop()

