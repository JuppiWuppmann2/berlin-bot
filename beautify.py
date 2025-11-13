import re
from datetime import datetime

POST_MAX_LEN = 280

EMOJI_MAP = {
    "unfall": "🚨 Unfall",
    "baustelle": "🚧 Baustelle",
    "sperrung": "⚠️ Sperrung",
    "stau": "🛑 Stau",
    "gefahr": "⚠️ Gefahr",
    "brücke": "🌉 Brücke",
    "fahrbahn": "🛣️ Fahrbahn",
    "ampel": "🚦 Ampel",
}

def _normalize_whitespace(s: str) -> str:
    return re.sub(r'\\s+', ' ', s).strip()

def _preserve_highway_tokens(s: str) -> str:
    # Ensure tokens like A100, B2 remain uppercase
    return re.sub(r'\\b(a|b)(\\d+)\\b', lambda m: m.group(1).upper()+m.group(2), s, flags=re.IGNORECASE)

def _apply_capitalization(s: str) -> str:
    s = s.lower()
    # capitalize after sentence boundaries or line starts
    parts = re.split('([\\.\\!\\?]\\s+)', s)
    parts = [p.capitalize() for p in parts]
    s = ''.join(parts)
    # also capitalize road tokens (e.g., 'a100' -> 'A100')
    s = _preserve_highway_tokens(s)
    return s

def beautify_text(message: str, add_time: bool = True) -> list:
    \"\"\"Return list of post parts (for splitting long posts).\"\"\"
    if not message:
        return [message]

    text = _normalize_whitespace(message)
    text = re.sub(r'[_\\|/]+', ' ', text)
    text = _apply_capitalization(text)

    # Insert emoji prefixes if keyword present at start or overall
    lowered = text.lower()
    prefix = None
    for k, v in EMOJI_MAP.items():
        if k in lowered:
            prefix = v
            break

    if prefix:
        # If text already starts with the word, avoid duplicate: "Unfall auf..." -> keep as "🚨 Unfall auf..."
        if not text.lower().startswith(prefix.split()[1].lower()):
            text = f\"{prefix} {text}\"
        else:
            text = f\"{prefix} {text}\"

    # Add current time line optionally
    if add_time:
        now = datetime.now().strftime('%H:%M')
        text = f\"{text}\\n⏰ Stand: {now}\"

    # Ensure not exceeding POST_MAX_LEN; if too long, split on sentence boundaries
    if len(text) <= POST_MAX_LEN:
        return [text.strip()]

    # split smartly
    sentences = re.split(r'(?<=[\\.!?])\\s+', text)
    parts = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= POST_MAX_LEN:
            current = (current + " " + s).strip()
        else:
            if current:
                parts.append(current.strip())
            if len(s) <= POST_MAX_LEN:
                current = s.strip()
            else:
                # fallback hard split
                for i in range(0, len(s), POST_MAX_LEN):
                    parts.append(s[i:i+POST_MAX_LEN].strip())
                current = ""
    if current:
        parts.append(current.strip())

    return parts
