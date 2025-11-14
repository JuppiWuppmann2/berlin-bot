import os
import json
import time
import re
import unicodedata
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from beautify import beautify_text
from bluesky import post_on_bluesky_thread, BlueskyError
from fallback import get_viz_updates_fallback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
STATE_FILE = "data.json"
BACKUP_FILE = "data_backup.json"
MAX_RETRIES = 2  # Reduziert für schnellere Durchläufe
RETRY_DELAY = 5

# Berlin-Filter: Begriffe, die auf Berlin hinweisen
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
    
    # Direkte Prüfung auf Berlin-Begriffe
    for indicator in BERLIN_INDICATORS:
        if indicator in msg_lower:
            return True
    
    # Prüfe auf typische Berlin-Straßen-Muster
    if 'berlin,' in msg_lower or msg_lower.startswith('berlin'):
        return True
    
    # Filter out: Bundesstraßen außerhalb Berlins, Kreis-/Landstraßen
    non_berlin_patterns = [
        r'kreis\s+(barnim|oberhavel|märkisch-oderland|dahme-spreewald|teltow-fläming|potsdam-mittelmark|havelland|oder-spree|uckermark)',
        r'od\s+[a-zäöü]+',  # "od xyz" = Ortsdurchfahrt außerhalb Berlins
        r'ou\s+[a-zäöü]+',  # "ou xyz" = Ortsumgehung
        r'l\d{2,3},',  # Landstraßen ohne Berlin-Kontext
        r'k\d{4,5},',  # Kreisstraßen
        r'b\d+[,\s]+(od|ou|zwischen).+?(elsterwerda|cottbus|spremberg|brandenburg|potsdam|neuruppin|wittenberge|eberswalde|fürstenberg|bad belzig|zossen|königs wusterhausen)',
    ]
    
    for pattern in non_berlin_patterns:
        if re.search(pattern, msg_lower):
            logger.debug(f"Gefiltert (außerhalb Berlin): {message[:50]}...")
            return False
    
    return True

def normalize_message(message: str) -> str:
    """Normiert Meldungen für stabilen Vergleich im State-File."""
    if not message or not isinstance(message, str):
        return ""
    
    msg = message.lower().strip()
    msg = msg.replace("\u200b", "").replace("\xa0", " ")
    msg = "".join(ch for ch in msg if not unicodedata.category(ch).startswith("So"))
    msg = re.sub(r"[^a-z0-9äöüß|,.:;\/\- ]+", " ", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    msg = msg.replace(" | ", "|")
    
    return msg

def create_backup():
    """Erstellt ein Backup der aktuellen State-Datei."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as src:
                with open(BACKUP_FILE, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.info("✅ Backup erstellt")
        except Exception as e:
            logger.warning(f"⚠️ Backup-Fehler: {e}")

def restore_from_backup():
    """Stellt State-Datei aus Backup wieder her."""
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, 'r', encoding='utf-8') as src:
                with open(STATE_FILE, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.info("✅ State aus Backup wiederhergestellt")
            return True
        except Exception as e:
            logger.error(f"❌ Backup-Wiederherstellung fehlgeschlagen: {e}")
    return False

def get_viz_updates_with_retry():
    """Scraping mit mehreren Versuchen und Fallback."""
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔍 Scraping-Versuch {attempt + 1}/{MAX_RETRIES}")
            updates = get_viz_updates()
            if updates:
                logger.info(f"✅ Scraping erfolgreich: {len(updates)} Meldungen")
                return updates
            else:
                logger.warning("⚠️ Keine Meldungen gefunden")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"❌ Scraping-Fehler (Versuch {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    
    # Fallback-Scraper
    logger.info("🔄 Versuche Fallback-Scraper...")
    try:
        fallback_updates = get_viz_updates_fallback()
        if fallback_updates:
            logger.info(f"✅ Fallback erfolgreich: {len(fallback_updates)} Meldungen")
            return fallback_updates
    except Exception as e:
        logger.error(f"❌ Fallback fehlgeschlagen: {e}")
    
    logger.error("❌ Alle Scraping-Versuche fehlgeschlagen")
    return []

def get_viz_updates():
    """Optimierte Scraping-Funktion mit Berlin-Filter."""
    logger.info("🔍 Scraper gestartet...")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    
    # Performance-Optimierungen
    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = None
    try:
        # Webdriver-Manager macht ChromeDriver-Verwaltung einfach
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        logger.info(f"📡 Lade Seite: {URL}")
        driver.get(URL)
        
        # Warte auf Meldungen
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.construction-sites-item"))
            )
        except TimeoutException:
            logger.warning("⚠️ Timeout beim Warten - versuche trotzdem zu scrapen")
        
        # Mehrere Selektoren ausprobieren
        selectors = [
            "li.construction-sites-item",
            ".construction-sites-item",
            "li[class*='construction']"
        ]
        
        items = []
        for selector in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                logger.info(f"✅ {len(items)} Elemente mit '{selector}' gefunden")
                break
        
        if not items:
            items = driver.find_elements(By.TAG_NAME, "li")
            logger.info(f"🔄 Fallback: {len(items)} li-Elemente")
        
        updates = []
        berlin_filtered = 0
        
        for li in items:
            try:
                text_content = li.get_attribute('textContent') or li.text
                if not text_content or len(text_content.strip()) < 10:
                    continue
                
                # Berlin-Filter anwenden VOR der Verarbeitung
                if not is_berlin_related(text_content):
                    berlin_filtered += 1
                    continue
                
                # Strukturierte Extraktion
                try:
                    title_elem = li.find_element(By.TAG_NAME, "strong")
                    title = title_elem.text.strip()
                except:
                    title = text_content.strip().split('\n')[0][:100]
                
                try:
                    span_texts = [span.text.strip() for span in li.find_elements(By.TAG_NAME, "span")]
                    zeitraum = next((t.replace("Zeitraum:", "").strip() for t in span_texts if "Zeitraum" in t), "")
                    location = next((t.replace("Straße:", "").strip() for t in span_texts if "Straße" in t), "")
                    description = " | ".join([t for t in span_texts if "Zeitraum" not in t and "Straße" not in t])
                    
                    parts = [title, description, zeitraum, location]
                    message = " | ".join([p for p in parts if p])
                except:
                    message = text_content.strip().replace('\n', ' | ')
                
                if message and len(message.strip()) > 5:
                    updates.append(message)
                    
            except Exception as e:
                logger.debug(f"Fehler beim Verarbeiten: {e}")
                continue
        
        logger.info(f"✅ {len(updates)} Berlin-Meldungen verarbeitet ({berlin_filtered} gefiltert)")
        return updates
        
    except Exception as e:
        logger.error(f"❌ Scraping-Fehler: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def load_state():
    """Lädt State mit Backup-Fallback."""
    for filepath in [STATE_FILE, BACKUP_FILE]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = f.read().strip()
                    if not data:
                        continue
                    state = set(json.loads(data))
                    logger.info(f"✅ State aus {filepath} geladen: {len(state)} Einträge")
                    return state
            except Exception as e:
                logger.warning(f"⚠️ Fehler beim Laden von {filepath}: {e}")
                continue
    
    logger.info("📝 Neuer State wird erstellt")
    return set()

def save_state(state):
    """Speichert State mit Backup."""
    if not isinstance(state, (set, list)):
        logger.error("❌ Ungültiger State-Typ")
        return False
    
    try:
        create_backup()
        
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(state)), f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 State gespeichert: {len(state)} Einträge")
        return True
    except Exception as e:
        logger.error(f"❌ Fehler beim Speichern: {e}")
        restore_from_backup()
        return False

def post_updates_safely(items, resolved=False):
    """Postet Updates mit Fehlerbehandlung."""
    successful_posts = 0
    failed_posts = 0
    
    for norm_item in items:
        try:
            if resolved:
                parts = beautify_text(f"✅ Behoben: {norm_item}", resolved=True)
            else:
                parts = beautify_text(norm_item)
            
            logger.info(f"📤 Poste: {parts[0][:50]}...")
            post_on_bluesky_thread(parts)
            successful_posts += 1
            logger.info("✅ Post erfolgreich!")
            
            time.sleep(5)  # Kürzere Pause zwischen Posts
            
        except BlueskyError as e:
            logger.error(f"❌ Bluesky-Fehler: {e}")
            failed_posts += 1
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                logger.info("⏳ Rate-Limit, warte 60 Sekunden...")
                time.sleep(60)
        except Exception as e:
            logger.error(f"❌ Post-Fehler: {e}")
            failed_posts += 1
    
    logger.info(f"📊 {successful_posts} erfolgreich, {failed_posts} fehlgeschlagen")
    return successful_posts, failed_posts

def main():
    """Hauptfunktion mit Berlin-Filter."""
    logger.info("🚀 Bot gestartet...")
    
    try:
        prev_state = load_state()
        logger.info(f"📂 Gespeicherte Meldungen: {len(prev_state)}")

        raw_updates = get_viz_updates_with_retry()
        
        if not raw_updates:
            logger.warning("⚠️ Keine Updates - Bot beendet ohne Änderungen")
            return
        
        # Normalisierung mit Berlin-Filter
        current_updates = set()
        filtered_out = 0
        
        for update in raw_updates:
            try:
                # Nochmal Berlin-Check (doppelte Sicherheit)
                if not is_berlin_related(update):
                    filtered_out += 1
                    continue
                    
                normalized = normalize_message(update)
                if normalized:
                    current_updates.add(normalized)
            except Exception as e:
                logger.error(f"❌ Normalisierungsfehler: {e}")

        logger.info(f"🔄 {len(raw_updates)} raw → {len(current_updates)} Berlin-Updates ({filtered_out} gefiltert)")

        # Neue und behobene Meldungen
        new_items = current_updates - prev_state
        resolved_items = prev_state - current_updates
        
        logger.info(f"📈 Neu: {len(new_items)} | 📉 Behoben: {len(resolved_items)}")

        # Posts senden
        total_successful = 0
        total_failed = 0
        
        if new_items:
            logger.info("📤 Poste neue Meldungen...")
            success, failed = post_updates_safely(new_items, resolved=False)
            total_successful += success
            total_failed += failed

        if resolved_items:
            logger.info("📤 Poste behobene Meldungen...")
            success, failed = post_updates_safely(resolved_items, resolved=True)
            total_successful += success
            total_failed += failed

        # State speichern
        if save_state(current_updates):
            logger.info("💾 State gespeichert")
        else:
            logger.error("❌ State-Speicherung fehlgeschlagen")

        logger.info(f"🎯 Bot beendet: {total_successful} Posts erfolgreich, {total_failed} fehlgeschlagen")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot gestoppt")
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler: {e}")
        try:
            restore_from_backup()
            logger.info("🔄 Backup wiederhergestellt")
        except:
            logger.error("❌ Backup-Wiederherstellung fehlgeschlagen")
        raise

if __name__ == "__main__":
    main()
