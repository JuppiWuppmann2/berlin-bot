import os, time, subprocess, json
from bluesky import post_on_bluesky_thread
from beautify import beautify_text

STATE_FILE = "state.json"

def git_pull():
    subprocess.run(["git", "pull"], check=False)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(state), f, ensure_ascii=False, indent=2)

def main_loop():
    prev_state = load_state()

    while True:
        git_pull()
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                current_updates = set(json.load(f))
        except Exception as e:
            print("Fehler beim Laden:", e)
            time.sleep(300)
            continue

        # Neue Meldungen
        new_items = current_updates - prev_state
        for item in new_items:
            msg = beautify_text(item)
            print("Neue Meldung:", msg)
            post_on_bluesky_thread(msg)

        # Behobene Meldungen
        resolved_items = prev_state - current_updates
        for item in resolved_items:
            msg = beautify_text(f"✅ Behoben: {item}")
            print("Behoben:", msg)
            post_on_bluesky_thread(msg)

        prev_state = current_updates
        save_state(prev_state)
        time.sleep(300)

if __name__ == "__main__":
    main_loop()
