import requests
from bs4 import BeautifulSoup

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"

def get_viz_updates():
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    updates = []

    items = soup.select("li.construction-sites-item")
    for li in items:
        text_div = li.select_one("div.text")
        if not text_div:
            continue

        strong_tag = text_div.select_one("strong")
        title = strong_tag.get_text(strip=True) if strong_tag else "Keine Überschrift"

        # Zeitraum
        span_tags = text_div.select("span")
        zeitraum = ""
        if span_tags:
            zeitraum_texts = [span.get_text(strip=True) for span in span_tags if "Zeitraum" not in span.get_text()]
            zeitraum = " ".join(zeitraum_texts)

        # Beschreibung
        description = ""
        for span in span_tags:
            if "Straße" in span.get_text() or "Zeitraum" in span.get_text():
                continue
            description += span.get_text(strip=True) + " "

        message = f"{title}\n{zeitraum}\n{description.strip()}"
        updates.append(message)

    return updates
