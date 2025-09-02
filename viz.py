import requests
from bs4 import BeautifulSoup

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"

def get_viz_updates():
    """Scraped aktuelle Baustellen/Störungen von viz.berlin.de"""
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    updates = []
    for item in soup.select("div.teaser, li"):  # je nach HTML-Struktur
        text = item.get_text(strip=True)
        if text and len(text) > 10:
            updates.append(text)

    return updates
