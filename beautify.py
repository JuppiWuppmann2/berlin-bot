POST_MAX_LEN = 280

def beautify_text(message):
    message = message.replace("Baustelle", "🚧 Baustelle")
    message = message.replace("Sperrung", "⛔ Sperrung")
    message = message.replace("Gefahr", "⚠️ Gefahr")

    hashtags = " #Berlin #Verkehr #Baustelle #Sperrung #Störung"
    message += "\n" + hashtags

    parts = []
    while len(message) > POST_MAX_LEN:
        split_idx = message.rfind("\n", 0, POST_MAX_LEN)
        if split_idx == -1:
            split_idx = POST_MAX_LEN
        parts.append(message[:split_idx].strip())
        message = message[split_idx:].strip()
    parts.append(message.strip())
    return parts
