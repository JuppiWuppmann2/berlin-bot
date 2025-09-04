POST_MAX_LEN = 280

# Standard-Hashtags, die immer angehängt werden
HASHTAGS = ["#Berlin", "#Verkehr", "#Baustelle", "#Sperrung", "#Störung", "#Straße"]

def beautify_text(message):
    # Emojis für Schlüsselbegriffe ersetzen
    message = message.replace("Baustelle", "🚧 Baustelle")
    message = message.replace("Sperrung", "⛔ Sperrung")
    message = message.replace("Gefahr", "⚠️ Gefahr")
    message = message.replace("Fahrbahn", "🛣️ Fahrbahn")
    message = message.replace("Ampel", "🚦 Ampel")

    # Am Ende standardisierte Hashtags hinzufügen
    hashtags_text = " ".join(HASHTAGS)
    message += "\n" + hashtags_text

    # Thread-Split (für Posts > 280 Zeichen)
    parts = []
    while len(message) > POST_MAX_LEN:
        split_idx = message.rfind("\n", 0, POST_MAX_LEN)
        if split_idx == -1:
            split_idx = POST_MAX_LEN
        parts.append(message[:split_idx].strip())
        message = message[split_idx:].strip()
    parts.append(message.strip())

    # Hashtags im Text korrigieren (z.B. "# Berlin" → "#Berlin")
    parts = [part.replace("# ", "#") for part in parts]

    return parts
