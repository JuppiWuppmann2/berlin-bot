import requests
from bs4 import BeautifulSoup

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"

def get_viz_updates():
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    updates = []

    # Selektiere alle relevanten Meldungen
    items = soup.select(
        "li.construction-sites-item.filter-baustelle, "
        "li.construction-sites-item.filter-sperrung, "
        "li.construction-sites-item.filter-sonstige"
    )
    print(f"Gefundene Meldungen: {len(items)}")  # Debug

    for li in items:
        text_div = li.select_one("div.text")
        if not text_div:
            print("Kein Text-Div gefunden, überspringe Element")  # Debug
            continue

        # Titel
        strong_tag = text_div.select_one("strong")
        title = strong_tag.get_text(strip=True) if strong_tag else "Keine Überschrift"

        # Zeitraum
        span_tags = text_div.select("span")
        zeitraum = ""
        for span in span_tags:
            if "Zeitraum" in span.get_text():
                zeitraum = span.get_text(strip=True).replace("Zeitraum:", "").strip()
                break

        # Straße / Beschreibung
        description_lines = []
        for span in span_tags:
            text = span.get_text(strip=True)
            if "Straße:" in text or "Leitungsbauarbeiten" in text or "Bau" in text or "Vollsperrung" in text or "Gefahr" in text:
                description_lines.append(text)

        description = " ".join(description_lines).strip()

        # Fertige Meldung
        message = f"{title}\n{zeitraum}\n{description}"
        updates.append(message)

    return updates
