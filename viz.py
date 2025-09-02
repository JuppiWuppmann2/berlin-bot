import requests
from bs4 import BeautifulSoup

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"

def get_viz_updates():
    res = requests.get(URL)
    soup = BeautifulSoup(res.text, "html.parser")

    updates = []
    for item in soup.select("ul.list-unstyled li"):
        title = item.select_one("h3")
        desc = item.select_one("p")
        if title:
            text = title.get_text(strip=True)
            if desc:
                text += " – " + desc.get_text(strip=True)
            updates.append(text)

    return updates[:5]
