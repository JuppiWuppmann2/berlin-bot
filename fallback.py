import requests
import time
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

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
    }
    
    url = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Verschiedene Selektoren ausprobieren
        selectors = [
            'li.construction-sites-item',
            '.construction-sites-item',
            'li[class*="construction"]',
            '.item-container li'
        ]
        
        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.info(f"✅ {len(items)} Meldungen mit Selector '{selector}' gefunden")
                break
        
        if not items:
            # Fallback: alle li-Elemente mit ausreichend Text
            all_lis = soup.find_all('li')
            items = [li for li in all_lis if li.get_text(strip=True) and len(li.get_text(strip=True)) > 20]
            logger.info(f"🔄 Fallback: {len(items)} li-Elemente mit Text gefunden")
        
        updates = []
        for li in items:
            try:
                text_content = li.get_text(strip=True)
                if not text_content or len(text_content) < 10:
                    continue
                
                # Strukturierte Extraktion versuchen
                strong_tag = li.find('strong')
                title = strong_tag.get_text(strip=True) if strong_tag else ""
                
                spans = li.find_all('span')
                span_texts = [span.get_text(strip=True) for span in spans if span.get_text(strip=True)]
                
                zeitraum = ""
                location = ""
                description_parts = []
                
                for text in span_texts:
                    if "Zeitraum:" in text:
                        zeitraum = text.replace("Zeitraum:", "").strip()
                    elif "Straße:" in text:
                        location = text.replace("Straße:", "").strip()
                    else:
                        description_parts.append(text)
                
                description = " | ".join(description_parts)
                
                # Nachricht zusammenbauen
                parts = [p for p in [title, description, zeitraum, location] if p]
                if parts:
                    message = " | ".join(parts)
                    updates.append(message)
                
            except Exception as e:
                logger.debug(f"Fehler beim Verarbeiten eines Fallback-Eintrags: {e}")
                continue
        
        logger.info(f"✅ Fallback-Scraper erfolgreich: {len(updates)} Meldungen")
        return updates
        
    except requests.RequestException as e:
        logger.error(f"❌ Fallback-Scraper HTTP-Fehler: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Fallback-Scraper unerwarteter Fehler: {e}")
        return []
