def beautify_text(text):
    """Veredelt die Meldungen mit Emojis + Hashtags."""
    base_tags = "#Berlin #Verkehr #Baustelle #Störung"

    emojis = ""
    if "gesperrt" in text.lower() or "sperrung" in text.lower():
        emojis += "⛔🚧 "
    elif "bau" in text.lower():
        emojis += "🚧 "
    elif "störung" in text.lower():
        emojis += "⚠️ "
    elif "verspätung" in text.lower():
        emojis += "⏰ "

    hashtags = [base_tags]
    if "U-Bahn" in text or "S-Bahn" in text:
        hashtags.append("#ÖPNV")
    if "Bus" in text:
        hashtags.append("#Bus")
    if "A100" in text or "Autobahn" in text:
        hashtags.append("#Autobahn")

    return f"{emojis}{text}\n\n{' '.join(hashtags)}"
