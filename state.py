import json
import os

STATE_FILE = "data.json"

def load_state():
    """Lädt bekannten Zustand (alle Meldungen)."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_state(state):
    """Speichert aktuellen Zustand."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)
