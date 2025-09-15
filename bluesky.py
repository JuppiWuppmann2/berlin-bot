from atproto import Client
from atproto.exceptions import AtProtocolError
import os
import time
import logging

logger = logging.getLogger(__name__)

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

class BlueskyError(Exception):
    """Custom exception für Bluesky-spezifische Fehler."""
    pass

class BlueskyClient:
    def __init__(self):
        self.client = None
        self.authenticated = False
        
    def authenticate(self):
        """Authentifizierung mit Retry-Logic."""
        if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
            raise BlueskyError("BLUESKY_HANDLE oder BLUESKY_PASSWORD nicht gesetzt")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.client = Client()
                logger.info(f"🔐 Authentifizierung bei Bluesky (Versuch {attempt + 1}/{max_retries})")
                self.client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
                self.authenticated = True
                logger.info("✅ Bluesky-Authentifizierung erfolgreich")
                return
            except AtProtocolError as e:
                logger.error(f"❌ Bluesky-Authentifizierungsfehler: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    raise BlueskyError(f"Authentifizierung nach {max_retries} Versuchen fehlgeschlagen: {e}")
            except Exception as e:
                logger.error(f"❌ Unerwarteter Authentifizierungsfehler: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    raise BlueskyError(f"Unerwarteter Fehler bei Authentifizierung: {e}")
    
    def post_with_retry(self, text, reply_to=None, max_retries=3):
        """Post mit Retry-Logic."""
        for attempt in range(max_retries):
            try:
                if not self.authenticated:
                    raise BlueskyError("Nicht authentifiziert")
                
                logger.debug(f"📤 Poste (Versuch {attempt + 1}/{max_retries}): {text[:50]}...")
                post = self.client.post(text=text, reply_to=reply_to)
                logger.debug(f"✅ Post erfolgreich: {post.uri}")
                return post
                
            except AtProtocolError as e:
                error_msg = str(e).lower()
                
                # Rate-Limit-Behandlung
                if "rate" in error_msg or "limit" in error_msg or "too many" in error_msg:
                    wait_time = 60 * (attempt + 1)  # 60, 120, 180 Sekunden
                    logger.warning(f"⏳ Rate-Limit erreicht, warte {wait_time} Sekunden...")
                    time.sleep(wait_time)
                    continue
                
                # Authentifizierungs-Fehler
                elif "auth" in error_msg or "unauthorized" in error_msg or "forbidden" in error_msg:
                    logger.warning("🔐 Authentifizierung verloren, versuche Neuanmeldung...")
                    self.authenticated = False
                    try:
                        self.authenticate()
                        continue  # Nochmal versuchen nach Neuanmeldung
                    except Exception:
                        raise BlueskyError(f"Neuanmeldung fehlgeschlagen: {e}")
                
                # Sonstige AT-Protocol-Fehler
                else:
                    logger.error(f"❌ AT-Protocol-Fehler (Versuch {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(10)  # Kurze Pause vor nächstem Versuch
                    else:
                        raise BlueskyError(f"Post-Fehler nach {max_retries} Versuchen: {e}")
                        
            except Exception as e:
                logger.error(f"❌ Unerwarteter Post-Fehler (Versuch {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    raise BlueskyError(f"Unerwarteter Post-Fehler: {e}")
        
        raise BlueskyError(f"Post nach {max_retries} Versuchen fehlgeschlagen")

# Global client instance
_bluesky_client = None

def get_client():
    """Lazy-Loading des Bluesky-Clients."""
    global _bluesky_client
    if _bluesky_client is None:
        _bluesky_client = BlueskyClient()
        _bluesky_client.authenticate()
    return _bluesky_client

def post_on_bluesky_thread(parts):
    """Postet eine Nachricht oder Thread auf Bluesky mit verbesserter Fehlerbehandlung."""
    if not parts or not isinstance(parts, list):
        raise BlueskyError("Ungültige parts für Thread-Post")
    
    client = get_client()
    reply_to = None
    posted_parts = 0
    
    logger.info(f"📝 Starte Thread-Post mit {len(parts)} Teilen")
    
    for i, part in enumerate(parts):
        if not part or not part.strip():
            logger.warning(f"⚠️ Überspringe leeren Teil {i+1}")
            continue
            
        try:
            logger.debug(f"📤 Poste Teil {i+1}/{len(parts)}: {len(part)} Zeichen")
            post = client.post_with_retry(text=part, reply_to=reply_to)
            reply_to = post.uri
            posted_parts += 1
            
            # Pause zwischen Thread-Posts
            if i < len(parts) - 1:  # Nicht nach dem letzten Post warten
                time.sleep(2)
                
        except BlueskyError:
            logger.error(f"❌ Teil {i+1} konnte nicht gepostet werden")
            raise
        except Exception as e:
            logger.error(f"❌ Unerwarteter Fehler bei Teil {i+1}: {e}")
            raise BlueskyError(f"Thread-Post fehlgeschlagen bei Teil {i+1}: {e}")
    
    logger.info(f"✅ Thread erfolgreich gepostet: {posted_parts}/{len(parts)} Teile")
    
    if posted_parts == 0:
        raise BlueskyError("Kein Teil des Threads konnte gepostet werden")
    
    return posted_parts
