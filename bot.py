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
MAX_RETRIES = 3
RETRY_DELAY = 10

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

# ----------------------------- Helper: Normalisierung -----------------------------
def normalize_message(message: str) -> str:
    """Normiert Meldungen für stabilen Vergleich im State-File."""
    if not message or not isinstance(message, str):
        return ""
    
    msg = message.lower().strip()

    # Unsichtbare Unicode-Zeichen entfernen
    msg = msg.replace("\u200b", "").replace("\xa0", " ")

    # Emojis und Symbole entfernen
    msg = "".join(ch for ch in msg if not unicodedata.category(ch).startswith("So"))

    # Erlaubte Zeichen (Buchstaben, Zahlen, Umlaute, Satzzeichen, Trenner)
    msg = re.sub(r"[^a-z0-9äöüß|,.:;\/\- ]+", " ", msg)

    # Mehrfach-Leerzeichen und Trenner vereinheitlichen
    msg = re.sub(r"\s+", " ", msg).strip()
    msg = msg.replace(" | ", "|")

    return msg

# ----------------------------- Backup-System -----------------------------
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

# ----------------------------- Selenium Scraper mit Retry-Logic -----------------------------
def get_viz_updates_with_retry():
    """Scraping mit mehreren Versuchen und Fallback."""
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔍 Scraping-Versuch {attempt + 1}/{MAX_RETRIES}")
            updates = get_viz_updates()
            if updates:  # Erfolg, wenn mindestens eine Meldung gefunden
                logger.info(f"✅ Scraping erfolgreich: {len(updates)} Meldungen")
                return updates
            else:
                logger.warning("⚠️ Keine Meldungen gefunden - könnte ein Problem sein")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"❌ Scraping-Fehler (Versuch {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    
    # Fallback-Scraper versuchen
    logger.info("🔄 Alle Selenium-Versuche fehlgeschlagen, versuche Fallback-Scraper...")
    try:
        fallback_updates = get_viz_updates_fallback()
        if fallback_updates:
            logger.info(f"✅ Fallback-Scraper erfolgreich: {len(fallback_updates)} Meldungen")
            return fallback_updates
    except Exception as e:
        logger.error(f"❌ Auch Fallback-Scraper fehlgeschlagen: {e}")
    
    logger.error("❌ Alle Scraping-Versuche (Selenium + Fallback) fehlgeschlagen")
    return []

def get_viz_updates():
    """Scraping-Funktion mit verbesserter Fehlerbehandlung."""
    logger.info("🔍 Scraper gestartet...")
    
    options = Options()
    # Stabilere Headless-Einstellungen für CI-Umgebungen
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    
    driver = None
    try:
        # Robuste Driver-Installation mit System-ChromeDriver Präferenz
        driver_path = None
        
        # Zuerst System-ChromeDriver versuchen (von GitHub Actions installiert)
        system_chromedriver = "/usr/local/bin/chromedriver"
        if os.path.exists(system_chromedriver) and os.access(system_chromedriver, os.X_OK):
            driver_path = system_chromedriver
            logger.info(f"✅ Verwende System-ChromeDriver: {driver_path}")
        else:
            # Fallback: WebDriver Manager
            try:
                driver_path = ChromeDriverManager().install()
                logger.info(f"📁 ChromeDriver-Pfad von WebDriverManager: {driver_path}")
                
                # WebDriverManager-Pfad validieren und korrigieren
                if driver_path and os.path.exists(driver_path):
                    # Wenn es ein Verzeichnis ist, nach der chromedriver-Datei suchen
                    if os.path.isdir(driver_path):
                        for root, dirs, files in os.walk(driver_path):
                            for file in files:
                                if file == 'chromedriver' and not file.endswith('.chromedriver'):
                                    potential_driver = os.path.join(root, file)
                                    if os.access(potential_driver, os.X_OK):
                                        driver_path = potential_driver
                                        logger.info(f"🔧 Gefundener ausführbarer ChromeDriver: {driver_path}")
                                        break
                            if driver_path and not os.path.isdir(driver_path):
                                break
                    
                    # Ausführungsrechte setzen falls nötig
                    if not os.access(driver_path, os.X_OK):
                        import stat
                        os.chmod(driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
                        logger.info(f"🔧 Ausführungsrechte für ChromeDriver gesetzt")
                        
            except Exception as e:
                logger.warning(f"⚠️ WebDriverManager fehlgeschlagen: {e}")
                driver_path = None
        
        # Service erstellen - mit Fallback-Strategien
        service = None
        if driver_path and os.path.exists(driver_path) and os.access(driver_path, os.X_OK):
            service = Service(executable_path=driver_path)
            logger.info(f"📍 Service mit explizitem Pfad: {driver_path}")
        else:
            # Letzter Versuch: System-PATH durchsuchen
            for path_dir in os.environ.get('PATH', '').split(os.pathsep):
                chromedriver_path = os.path.join(path_dir, 'chromedriver')
                if os.path.exists(chromedriver_path) and os.access(chromedriver_path, os.X_OK):
                    service = Service(executable_path=chromedriver_path)
                    logger.info(f"📍 Service mit PATH-ChromeDriver: {chromedriver_path}")
                    break
            
            if not service:
                # Allerletzter Versuch ohne expliziten Pfad
                try:
                    service = Service()
                    logger.info("📍 Service ohne expliziten Pfad (System-Standard)")
                except Exception as e:
                    logger.error(f"❌ Kann keinen ChromeDriver-Service erstellen: {e}")
                    raise Exception("ChromeDriver-Service konnte nicht initialisiert werden")
        
        if not service:
            raise Exception("Kein funktionierender ChromeDriver gefunden")
            
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        
        logger.info(f"📡 Lade Seite: {URL}")
        driver.get(URL)
        
        # Warten auf Meldungen mit flexiblerem Selector
        try:
            WebDriverWait(driver, 45).until(
                EC.any_of(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.construction-sites-item")),
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".construction-sites-item")),
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[class*='construction']"))
                )
            )
        except TimeoutException:
            logger.warning("⚠️ Timeout beim Warten auf Meldungen - versuche trotzdem zu scrapen")
        
        # Mehrere Selektoren ausprobieren
        selectors = [
            "li.construction-sites-item",
            ".construction-sites-item", 
            "li[class*='construction']",
            ".item-container li"
        ]
        
        items = []
        for selector in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                logger.info(f"✅ {len(items)} Meldungen mit Selector '{selector}' gefunden")
                break
        
        if not items:
            logger.warning("⚠️ Keine Meldungen mit bekannten Selektoren gefunden")
            # Fallback: alle li-Elemente
            items = driver.find_elements(By.TAG_NAME, "li")
            logger.info(f"🔄 Fallback: {len(items)} li-Elemente gefunden")
        
        updates = []
        processed = 0
        
        for li in items:
            try:
                # Flexiblere Textextraktion
                text_content = li.get_attribute('textContent') or li.text
                if not text_content or len(text_content.strip()) < 10:
                    continue
                
                # Strukturierte Extraktion versuchen
                try:
                    title_elem = li.find_element(By.TAG_NAME, "strong")
                    title = title_elem.text.strip()
                except:
                    # Fallback: ersten Teil als Titel verwenden
                    title = text_content.strip().split('\n')[0][:100]
                
                try:
                    span_texts = [span.text.strip() for span in li.find_elements(By.TAG_NAME, "span")]
                    zeitraum = next((t.replace("Zeitraum:", "").strip() for t in span_texts if "Zeitraum" in t), "")
                    location = next((t.replace("Straße:", "").strip() for t in span_texts if "Straße" in t), "")
                    description = " | ".join([t for t in span_texts if "Zeitraum" not in t and "Straße" not in t])
                    
                    parts = [title, description, zeitraum, location]
                    message = " | ".join([p for p in parts if p])
                except:
                    # Fallback: ganzen Text verwenden
                    message = text_content.strip().replace('\n', ' | ')
                
                if message and len(message.strip()) > 5:
                    updates.append(message)
                    processed += 1
                    
            except Exception as e:
                logger.debug(f"Fehler beim Verarbeiten eines Eintrags: {e}")
                continue
        
        logger.info(f"✅ {processed} Meldungen erfolgreich verarbeitet")
        return updates
        
    except WebDriverException as e:
        logger.error(f"❌ WebDriver-Fehler: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unerwarteter Scraping-Fehler: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
                logger.debug("🔄 WebDriver beendet")
            except:
                pass

# ----------------------------- State Management mit Fehlerbehandlung -----------------------------
def load_state():
    """Lädt State mit Backup-Fallback."""
    for filepath in [STATE_FILE, BACKUP_FILE]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = f.read().strip()
                    if not data:  # Datei leer
                        continue
                    state = set(json.loads(data))
                    logger.info(f"✅ State aus {filepath} geladen: {len(state)} Einträge")
                    return state
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"⚠️ Konnte {filepath} nicht lesen: {e}")
                continue
            except Exception as e:
                logger.error(f"❌ Unerwarteter Fehler beim Laden von {filepath}: {e}")
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
        logger.error(f"❌ Fehler beim Speichern des States: {e}")
        restore_from_backup()
        return False

# ----------------------------- Verbesserte Post-Logik -----------------------------
def post_updates_safely(items, resolved=False):
    """Postet Updates mit Fehlerbehandlung pro Item."""
    successful_posts = 0
    failed_posts = 0
    
    for norm_item in items:
        try:
            if resolved:
                parts = beautify_text(f"✅ Behoben: {norm_item}", resolved=True)
            else:
                # Original-Text für neue Meldungen rekonstruieren (vereinfacht)
                parts = beautify_text(norm_item)
            
            logger.info(f"📤 Poste: {parts[0][:50]}...")
            post_on_bluesky_thread(parts)
            successful_posts += 1
            logger.info("✅ Erfolgreich gepostet!")
            
            # Pause zwischen Posts
            time.sleep(8)
            
        except BlueskyError as e:
            logger.error(f"❌ Bluesky-Fehler: {e}")
            failed_posts += 1
            # Bei Rate-Limit länger warten
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                logger.info("⏳ Rate-Limit erreicht, warte 60 Sekunden...")
                time.sleep(60)
        except Exception as e:
            logger.error(f"❌ Unerwarteter Post-Fehler: {e}")
            failed_posts += 1
    
    logger.info(f"📊 Post-Statistik: {successful_posts} erfolgreich, {failed_posts} fehlgeschlagen")
    return successful_posts, failed_posts

# ----------------------------- Main mit verbesserter Fehlerbehandlung -----------------------------
def main():
    """Hauptfunktion mit umfassender Fehlerbehandlung."""
    logger.info("🚀 Bot gestartet...")
    
    try:
        # State laden
        prev_state = load_state()
        logger.info(f"📂 Bisher gespeicherte Meldungen: {len(prev_state)}")

        # Updates scrapen mit Retry-Logic
        raw_updates = get_viz_updates_with_retry()
        
        if not raw_updates:
            logger.warning("⚠️ Keine Updates erhalten - Bot beendet sich ohne Änderungen")
            return
        
        # Normalisierung mit Fehlerbehandlung
        current_updates = set()
        for update in raw_updates:
            try:
                normalized = normalize_message(update)
                if normalized:  # Nur non-empty hinzufügen
                    current_updates.add(normalized)
            except Exception as e:
                logger.error(f"❌ Fehler bei Normalisierung von '{update[:50]}...': {e}")

        logger.info(f"🔄 {len(raw_updates)} raw → {len(current_updates)} normalisierte Updates")

        # Debug: Beispiel-Normalisierung
        if raw_updates:
            logger.info("🔎 Beispiel-Normalisierung:")
            for i, u in enumerate(raw_updates[:2]):
                logger.info(f"  RAW {i+1}: {u[:100]}...")
                logger.info(f"  NORM{i+1}: {normalize_message(u)[:100]}...")

        # Neue und behobene Meldungen identifizieren
        new_items = current_updates - prev_state
        resolved_items = prev_state - current_updates
        
        logger.info(f"📈 Neue Meldungen: {len(new_items)}")
        logger.info(f"📉 Behobene Meldungen: {len(resolved_items)}")

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

        # State nur bei erfolgreichem Scraping aktualisieren
        if save_state(current_updates):
            logger.info("💾 State erfolgreich gespeichert")
        else:
            logger.error("❌ State-Speicherung fehlgeschlagen")

        # Zusammenfassung
        logger.info(f"🎯 Bot-Lauf beendet: {total_successful} Posts erfolgreich, {total_failed} fehlgeschlagen")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot durch Benutzer gestoppt")
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler in main(): {e}")
        # Versuche State zu retten
        try:
            restore_from_backup()
            logger.info("🔄 Backup-State wiederhergestellt")
        except:
            logger.error("❌ Auch Backup-Wiederherstellung fehlgeschlagen")
        raise

if __name__ == "__main__":
    main()
