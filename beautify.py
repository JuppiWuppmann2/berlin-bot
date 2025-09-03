POST_MAX_LEN = 280

def beautify_text(message):
    """
    Verschönert Meldungen für Bluesky:
    - Emojis passend zu Art der Meldung
    - Hashtags
    - Teilt lange Meldungen in Thread-Teile
    """
    # Emojis für Meldungen
    message = message.replace("Baustelle", "🚧 Baustelle")
    message = message.replace("Sperrung", "⛔ Sperrung")
    message = message.replace("Gefahr", "⚠️ Gefahr")
    message = message.replace("Behoben", "✅ Behoben")

    # Zusätzliche dekorative Emojis
    message = "📢 " + message

    # Hashtags passend zur Meldung
    hashtags = " #Berlin #Verkehr #Baustelle #Sperrung #Störung #Straße #Achtung"
    message += "\n" + hashtags

    # Thread-Split für lange Nachrichten
    parts = []
    while len(message) > POST_MAX_LEN:
        # Am letzten Zeilenumbruch vor POST_MAX_LEN trennen
        split_idx = message.rfind("\n", 0, POST_MAX_LEN)
        if split_idx == -1:
            split_idx = POST_MAX_LEN
        parts.append(message[:split_idx].strip())
        message = message[split_idx:].strip()
    parts.append(message.strip())

    return parts
