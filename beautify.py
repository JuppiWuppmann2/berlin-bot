def beautify_text(text):
    base_tags = "#Berlin #Verkehr #Baustelle #Störung"

    emojis = ""
    text_lower = text.lower()
    if "gesperrt" in text_lower or "sperrung" in text_lower:
        emojis += "⛔🚧 "
    elif "bau" in text_lower:
        emojis += "🚧 "
    elif "störung" in text_lower:
        emojis += "⚠️ "
    elif "verspätung" in text_lower:
        emojis += "⏰ "

    hashtags = [base_tags]
    if "U-Bahn" in text or "S-Bahn" in text:
        hashtags.append("#ÖPNV")
    if "Bus" in text:
        hashtags.append("#Bus")
    if "A100" in text or "Autobahn" in text:
        hashtags.append("#Autobahn")

    return f"{emojis}{text}\n\n{' '.join(hashtags)}"
