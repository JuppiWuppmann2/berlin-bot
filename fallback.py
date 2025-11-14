import requests
import time
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

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
    """
    Fallback-Scraper mit requests + BeautifulSoup
    Falls Selenium komplett fehlschlägt.
    """
    logger.info("🔄 Fallback-Scraper (requests + BeautifulSoup) gestartet...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.8,en;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache',
    }
    
    url = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
    
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        logger.info(f"📡 Lade Seite: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        logger.info(f"📄 Antwort erhalten: {len(response.content)} Bytes, Status: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Debug: HTML-Struktur analysieren
        logger.info("🔍 Analysiere HTML-Struktur...")
        
        # Zuerst schauen, ob überhaupt Content da ist
        body_text = soup.get_text(strip=True)[:500]
        logger.info(f"🔍 Body-Text (erste 500 Zeichen): {body_text}")
        
        # Nach verschiedenen möglichen Container-Strukturen suchen
        selectors_to_try = [
            'li.construction-sites-item',
            '.construction-sites-item',
            'li[class*="construction"]',
            '.item-container li',
            '.construction-item',
            '.traffic-item',
            '.disruption-item',
            'article',
            '.entry',
            '.post',
            '[class*="baustelle"]',
            '[class*="sperrung"]',
            '[class*="störung"]',
            '[class*="traffic"]',
            '[class*="item"]'
        ]
        
        items = []
        found_selector = None
        
        for selector in selectors_to_try:
            items = soup.select(selector)
            if items:
                found_selector = selector
                logger.info(f"✅ {len(items)} Elemente mit Selector '{selector}' gefunden")
                break
            else:
                logger.debug(f"❌ Kein Element mit Selector '{selector}' gefunden")
        
        if not items:
            logger.info("🔍 Keine spezifischen Selektoren erfolgreich, versuche generische Suche...")
            
            # Fallback: Alle Elemente mit genug Text und relevanten Keywords
            all_elements = soup.find_all(['div', 'li', 'article', 'section'])
            keywords = ['baustelle', 'sperrung', 'störung', 'verkehr', 'straße', 'autobahn', 'umleit']
            
            for elem in all_elements:
                text = elem.get_text(strip=True).lower()
                if (len(text) > 30 and 
                    any(keyword in text for keyword in keywords) and
                    not elem.find_parent(['script', 'style', 'nav', 'header', 'footer'])):
                    items.append(elem)
            
            logger.info(f"🔄 Keyword-basierte Suche: {len(items)} relevante Elemente gefunden")
        
        if not items:
            # Letzte Fallback-Strategie: Alle li-Elemente mit substantiellem Inhalt
            all_lis = soup.find_all('li')
            items = []
            for li in all_lis:
                text = li.get_text(strip=True)
                # Mindestens 20 Zeichen, aber nicht nur Navigation/Footer-Content
                if (len(text) > 20 and 
                    not text.lower().startswith(('home', 'kontakt', 'impressum', 'datenschutz')) and
                    not li.find_parent(['nav', 'footer', 'header'])):
                    items.append(li)
            
            logger.info(f"🔄 Generische li-Suche: {len(items)} Elemente gefunden")
        
        updates = []
        processed = 0
        
        for item in items:
            try:
                text_content = item.get_text(separator=' ', strip=True)
                
                # Filter für zu kurze oder irrelevante Inhalte
                if (not text_content or 
                    len(text_content) < 15 or
                    text_content.lower().startswith(('cookie', 'datenschutz', 'impressum', 'kontakt'))):
                    continue
                
                # Strukturierte Extraktion versuchen
                title = ""
                description = ""
                zeitraum = ""
                location = ""
                
                # Title aus strong, h1-h6, oder erstem Satz extrahieren
                title_candidates = (item.find_all(['strong', 'b', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or
                                  [item])
                if title_candidates:
                    title = title_candidates[0].get_text(strip=True)
                    if len(title) > 100:  # Zu lang für Titel
                        title = title[:97] + "..."
                
                # Spans für strukturierte Daten durchsuchen
                spans = item.find_all(['span', 'div', 'p'])
                for span in spans:
                    span_text = span.get_text(strip=True)
                    if not span_text:
                        continue
                        
                    if any(word in span_text.lower() for word in ['zeitraum:', 'datum:', 'zeit:']):
                        zeitraum = span_text.replace('Zeitraum:', '').replace('Datum:', '').strip()
                    elif any(word in span_text.lower() for word in ['straße:', 'ort:', 'bereich:']):
                        location = span_text.replace('Straße:', '').replace('Ort:', '').replace('Bereich:', '').strip()
                    elif len(span_text) > 10 and span_text != title:
                        if not description:
                            description = span_text
                        elif len(description) < 200:  # Beschreibung erweitern
                            description += " | " + span_text
                
                # Fallback: gesamten Text als Description verwenden
                if not description:
                    description = text_content
                    # Title aus erstem Teil extrahieren
                    if not title and len(description) > 30:
                        sentences = description.split('.')
                        if sentences:
                            title = sentences[0].strip()[:100]
                            description = '. '.join(sentences[1:]).strip()
                
                # Message zusammenbauen
                parts = []
                if title and title != description[:len(title)]:
                    parts.append(title)
                if description:
                    parts.append(description)
                if zeitraum:
                    parts.append(f"Zeitraum: {zeitraum}")
                if location:
                    parts.append(f"Ort: {location}")
                
                if parts:
                    message = " | ".join(parts)
                    # Nachricht begrenzen
                    if len(message) > 500:
                        message = message[:497] + "..."
                    
                    updates.append(message)
                    processed += 1
                    
                    # Debug für erste paar Nachrichten
                    if processed <= 3:
                        logger.info(f"📋 Extrahierte Nachricht {processed}: {message[:100]}...")
                
            except Exception as e:
                logger.debug(f"Fehler beim Verarbeiten eines Fallback-Eintrags: {e}")
                continue
        
        logger.info(f"✅ Fallback-Scraper: {processed} von {len(items)} Elementen verarbeitet")
        
        # Debug: Wenn keine Updates gefunden wurden
        if not updates and items:
            logger.warning("⚠️ Elemente gefunden, aber keine Updates extrahiert")
            for i, item in enumerate(items[:3]):
                sample_text = item.get_text(strip=True)[:100]
                logger.info(f"📋 Beispiel-Element {i+1}: {sample_text}...")
        
        return updates
        
    except requests.RequestException as e:
        logger.error(f"❌ Fallback-Scraper HTTP-Fehler: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Fallback-Scraper unerwarteter Fehler: {e}")
        return []
