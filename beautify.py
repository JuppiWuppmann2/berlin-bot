POST_MAX_LEN = 280

HASHTAGS = ["#Berlin", "#Verkehr", "#Baustelle", "#Sperrung", "#Störung", "#Straße"]

def beautify_text(message, resolved: bool = False):
    """Formatiert den Post-Text mit Emojis, Hashtags und Splits."""

    # Emojis für Schlüsselbegriffe ersetzen
    replacements = {
        "Baustelle": "🚧 Baustelle",
        "Sperrung": "⛔ Sperrung",
        "Gefahr": "⚠️ Gefahr",
        "Fahrbahn": "🛣️ Fahrbahn",
        "Ampel": "🚦 Ampel",
    }
    for word, emoji in replacements.items():
        message = message.replace(word, emoji)

    # Falls behoben → Prefix hinzufügen
    if resolved:
        message = f"✅ Behoben: {message}"

    # Hashtags erst NACH dem Split anhängen (damit sie immer ganz bleiben)
    hashtags_text = " ".join(HASHTAGS)
    full_text = f"{message}\n{hashtags_text}"

    parts = []
    while len(full_text) > POST_MAX_LEN:
        # nicht mitten in einem Wort oder Hashtag trennen
        split_idx = full_text.rfind(" ", 0, POST_MAX_LEN)
        while split_idx > 0 and full_text[split_idx - 1] == "#":
            split_idx = full_text.rfind(" ", 0, split_idx - 1)

        if split_idx == -1:
            split_idx = POST_MAX_LEN

        parts.append(full_text[:split_idx].strip())
        full_text = full_text[split_idx:].strip()

    parts.append(full_text.strip())

    return parts
