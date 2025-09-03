import time, json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"

def get_viz_updates():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL)
    time.sleep(5)

    updates = []
    items = driver.find_elements(By.CSS_SELECTOR, "li.construction-sites-item")

    for li in items:
        try:
            title = li.find_element(By.TAG_NAME, "strong").text
            span_texts = [span.text for span in li.find_elements(By.TAG_NAME, "span")]
            desc = " ".join([t for t in span_texts if "Zeitraum" not in t and "Straße" not in t])
            period = next((t.replace("Zeitraum:", "").strip() for t in span_texts if "Zeitraum" in t), "")
            location = next((t.replace("Straße:", "").strip() for t in span_texts if "Straße" in t), "")
            updates.append(f"{title} | {desc} | {period} | {location}")
        except Exception:
            continue

    driver.quit()
    return updates

if __name__ == "__main__":
    updates = get_viz_updates()
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(updates, f, ensure_ascii=False, indent=2)
