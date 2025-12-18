import os
import json
import time
import requests
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

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL = "https://viz.berlin.de/verkehr-in-berlin/baustellen-sperrungen-und-sonstige-storungen/"
STATE_FILE = "data.json"
BACKUP_FILE = "data_backup.json"
MAX_RETRIES = 2  # Reduziert von 3
RETRY_DELAY = 5   # Reduziert von 10
SELENIUM_TIMEOUT = 30  # Reduziert von 60

BERLIN_INDICATORS = [
    'berlin', 'a100', 'a111', 'a113', 'a115', 'stadtring',
    'charlottenburg', 'neukölln', 'friedrichshain', 'kreuzberg', 
    'prenzlauer berg', 'mitte', 'wedding', 'tiergarten', 'moabit',
    'tempelhof', 'schöneberg', 'wilmersdorf', 'zehlendorf', 'steglitz',
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
    
    return False

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
            logger.warning(f"⚠️ Backup konnte nicht erstellt werden: {e}")

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
    """Scraping-Funktion mit optimierten Timeouts."""
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
    options.add_argument("--disable-javascript")  # Oft nicht nötig für statische Inhalte
    options.page_load_strategy = 'eager'  # Nicht auf vollständiges Laden warten
    
    driver = None
    try:
        # WebDriver Manager - lässt Chrome automatisch herunterladen
        logger.info("📥 ChromeDriver wird vorbereitet...")
        service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(SELENIUM_TIMEOUT)
        driver.set_script_timeout(SELENIUM_TIMEOUT)
        
        logger.info(f"📡 Lade Seite: {URL}")
        driver.get(URL)
        
        # Kürzeres Warten auf Elemente
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.construction-sites-item"))
            )
        except TimeoutException:
            logger.warning("⚠️ Timeout beim Warten auf Elemente")
        
        # Mehrere Selektoren probieren
        selectors = [
            "li.construction-sites-item",
            ".construction-sites-item",
            "li[class*='construction']",
        ]
        
        items = []
        for selector in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                logger.info(f"✅ {len(items)} Elemente mit '{selector}' gefunden")
                break
        
        if not items:
            logger.warning("⚠️ Keine Elemente gefunden, versuche alle li-Elemente")
            items = driver.find_elements(By.TAG_NAME, "li")
        
        updates = []
        processed = 0
        
        for li in items[:100]:  # Limitiere auf 100 Elemente für Performance
            try:
                text_content = li.get_attribute('textContent') or li.text
                if not text_content or len(text_content.strip()) < 10:
                    continue
                
                # Vereinfachte Extraktion
                message = text_content.strip().replace('\n', ' | ')
                message = re.sub(r'\s+', ' ', message)
                
                if message and len(message.strip()) > 5:
                    updates.append(message)
                    processed += 1
                    
            except Exception as e:
                logger.debug(f"Fehler bei Element: {e}")
                continue
        
        logger.info(f"✅ {processed} Meldungen verarbeitet")
        return updates
        
    except WebDriverException as e:
        logger.error(f"❌ WebDriver-Fehler: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Scraping-Fehler: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
                logger.debug("🔄 WebDriver beendet")
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
                logger.warning(f"⚠️ Konnte {filepath} nicht lesen: {e}")
                continue
    
    logger.info("📝 Neuer State erstellt")
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
    
    # Limitiere auf maximal 5 Posts pro Lauf
    items_to_post = list(items)[:5]
    if len(items) > 5:
        logger.info(f"⚠️ {len(items)} Updates vorhanden, poste nur die ersten 5")
    
    for norm_item in items_to_post:
        try:
            parts = beautify_text(norm_item, resolved=resolved)
            
            logger.info(f"📤 Poste: {parts[0][:50]}...")
            post_on_bluesky_thread(parts)
            successful_posts += 1
            logger.info("✅ Erfolgreich gepostet")
            
            # Kürzere Pause
            time.sleep(5)
            
        except BlueskyError as e:
            logger.error(f"❌ Bluesky-Fehler: {e}")
            failed_posts += 1
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                logger.info("⏳ Rate-Limit, breche ab")
                break
        except Exception as e:
            logger.error(f"❌ Post-Fehler: {e}")
            failed_posts += 1
    
    logger.info(f"📊 Posts: {successful_posts} erfolgreich, {failed_posts} fehlgeschlagen")
    return successful_posts, failed_posts

def main():
    """Hauptfunktion mit Timeout-Schutz."""
    start_time = time.time()
    MAX_RUNTIME = 300  # 5 Minuten Maximum
    
    logger.info("🚀 Bot gestartet...")
    
    try:
        # Timeout-Check
        if time.time() - start_time > MAX_RUNTIME:
            logger.error("⏱️ Runtime-Limit erreicht")
            return
        
        prev_state = load_state()
        logger.info(f"📂 Gespeicherte Meldungen: {len(prev_state)}")

        # Timeout-Check
        if time.time() - start_time > MAX_RUNTIME:
            logger.error("⏱️ Runtime-Limit erreicht")
            return
        
        raw_updates = get_viz_updates_with_retry()
        
        if not raw_updates:
            logger.warning("⚠️ Keine Updates - Bot beendet sich")
            return
        
        # Normalisierung
        current_updates = set()
        for update in raw_updates:
            try:
                normalized = normalize_message(update)
                if normalized:
                    current_updates.add(normalized)
            except Exception as e:
                logger.error(f"❌ Normalisierungs-Fehler: {e}")

        logger.info(f"🔄 {len(raw_updates)} raw → {len(current_updates)} normalisiert")

        new_items = current_updates - prev_state
        resolved_items = prev_state - current_updates
        
        logger.info(f"📈 Neue: {len(new_items)}, Behoben: {len(resolved_items)}")

        # Timeout-Check vor Posts
        if time.time() - start_time > MAX_RUNTIME - 60:
            logger.error("⏱️ Nicht genug Zeit für Posts")
            save_state(current_updates)
            return
        
        total_successful = 0
        total_failed = 0
        
        if new_items:
            logger.info("📤 Poste neue Meldungen...")
            success, failed = post_updates_safely(new_items, resolved=False)
            total_successful += success
            total_failed += failed

        if resolved_items and time.time() - start_time < MAX_RUNTIME - 30:
            logger.info("📤 Poste behobene Meldungen...")
            success, failed = post_updates_safely(resolved_items, resolved=True)
            total_successful += success
            total_failed += failed

        save_state(current_updates)

        runtime = time.time() - start_time
        logger.info(f"🎯 Fertig in {runtime:.1f}s: {total_successful} Posts erfolgreich")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot gestoppt")
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler: {e}")
        try:
            restore_from_backup()
        except:
            pass
        raise

if __name__ == "__main__":
    main()
