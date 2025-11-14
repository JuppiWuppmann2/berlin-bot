import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

# Berlin-Indikator-Liste (gleich wie in bot.py)
BERLIN_INDICATORS = [
    'berlin', 'a100', 'a111', 'a113', 'a115', 'stadtring',
    'charlottenburg', 'neukölln', 'friedrichshain', 'kreuzberg', 
    'prenzlauer berg', 'mitte', 'wedding', 'tiergarten', 'moabit',
    'tempelhof', 'schöneberg', 'wilmersdorf', 'zehlendorf', 'steglitz',
    'lichterfelde', 'lankwitz', 'mariendorf', 'marzahn', 'hellersdorf',
    'köpenick', 'treptow', 'lichtenberg', 'pankow', 'reinickendorf',
    'spandau', 'friedrichsfelde', 'karlshorst', 'weißensee', 'buch',
    'wittenau', 'tegel', 'siemensstadt', 'hakenfelde', 'kladow',
    'dahlem', 'grunewald', 'westend', 'wannsee', 'nikolassee',
    'friedrichshagen', 'rahnsdorf', 'schmöckwitz', 'rudow', 'buckow',
    'britz', 'johannisthal', 'adlershof', 'alt-treptow', 'plänterwald',
    'oberschöneweide', 'niederschöneweide', 'baumschulenweg', 'wuhlheide',
    'fennpfuhl', 'rummelsburg', 'alt-hohenschönhausen', 'neu-hohenschönhausen',
    'malchow', 'französisch buchholz', 'rosenthal', 'wilhelmsruh',
    'gesundbrunnen', 'hansaviertel', 'hansa', 'falkenhagener feld',
    'staaken', 'gatow', 'pichelsdorf', 'charlottenburg-nord'
]

def is_berlin_related(message: str) -> bool:
    """Prüft, ob eine Meldung Berlin-bezogen ist."""
    if not message:
        return False
    
    msg_lower = message.lower()
    
    for indicator in BERLIN_INDICATORS:
        if indicator in msg_lower:
            return True
    
    if 'berlin,' in msg_lower or msg_lower.startswith('berlin'):
        return True
    
    # Filter für Nicht-Berlin
    non_berlin_patterns = [
        r'kreis\s+(barnim|oberhavel|märkisch-oderland|dahme-spreewald|teltow-fläming|potsdam-mittelmark|havelland|oder-spree|uckermark)',
        r'od\s+[a-zäöü]+',
        r'ou\s+[a-zäöü]+',
        r'l\d{2,3},',
        r'k\d{4,5},',
    ]
    
    for pattern in non_berlin_patterns:
        if re.search(pattern, msg_lower):
            return False
    
    return True

def get_viz_updates_fallback():
    """Fallback-Scraper mit Berlin-Filter und verbesserter Extraktion."""
    logger.info("🔄 Fallback-Scraper gestartet...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    url = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
    
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        logger.info(f"📡 Lade Seite: {url}")
        response = session.get(url, timeout=20)
        response.raise_for_status()
        
        logger.info(f"📄 Antwort erhalten: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Primäre Selektoren
        selectors = [
            'li.construction-sites-item',
            '.construction-sites-item',
            'li[class*="construction"]',
        ]
        
        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.info(f"✅ {len(items)} Elemente mit '{selector}' gefunden")
                break
        
        # Fallback: Alle LI mit relevanten Keywords
        if not items:
            logger.info("🔍 Verwende Keyword-Suche...")
            all_lis = soup.find_all('li')
            keywords = ['baustelle', 'sperrung', 'störung', 'verkehr', 'berlin', 'straße']
            
            for li in all_lis:
                text = li.get_text(strip=True).lower()
                if (len(text) > 20 and 
                    any(keyword in text for keyword in keywords) and
                    not li.find_parent(['nav', 'footer', 'header'])):
                    items.append(li)
            
            logger.info(f"🔄 Keyword-Suche: {len(items)} Elemente")
        
        updates = []
        processed = 0
        berlin_filtered = 0
        
        for item in items:
            try:
                text_content = item.get_text(separator=' ', strip=True)
                
                if not text_content or len(text_content) < 15:
                    continue
                
                # Berlin-Filter
                if not is_berlin_related(text_content):
                    berlin_filtered += 1
                    continue
                
                # Strukturierte Extraktion
                title = ""
                description = ""
                
                # Title aus strong/bold
                title_elem = item.find(['strong', 'b', 'h1', 'h2', 'h3'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 100:
                        title = title[:97] + "..."
                
                # Weitere Informationen aus spans/divs
                details = []
                for span in item.find_all(['span', 'div', 'p']):
                    span_text = span.get_text(strip=True)
                    if span_text and span_text != title and len(span_text) > 5:
                        details.append(span_text)
                
                # Message zusammenstellen
                if title:
                    message = title
                    if details:
                        description = " | ".join(details[:3])  # Max 3 Details
                        message += " | " + description
                else:
                    message = text_content
                
                # Bereinigen und kürzen
                message = re.sub(r'\s+', ' ', message).strip()
                if len(message) > 400:
                    message = message[:397] + "..."
                
                if len(message) > 15:
                    updates.append(message)
                    processed += 1
                    
            except Exception as e:
                logger.debug(f"Verarbeitungsfehler: {e}")
                continue
        
        logger.info(f"✅ Fallback: {processed} Berlin-Meldungen ({berlin_filtered} gefiltert)")
        return updates
        
    except requests.RequestException as e:
        logger.error(f"❌ Fallback HTTP-Fehler: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Fallback Fehler: {e}")
        return []
