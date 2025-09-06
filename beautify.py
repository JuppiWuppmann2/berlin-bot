POST_MAX_LEN = 280 
HASHTAGS = ["#Berlin", "#Verkehr", "#Baustelle", "#Sperrung", "#Störung", "#Straße"] 
def beautify_text(message): 
    # Emojis für Schlüsselbegriffe ersetzen
    replacements = { 
        "Baustelle": "🚧 Baustelle",
        "Sperrung": "⛔ Sperrung",
        "Gefahr": "⚠️ Gefahr", 
        "Fahrbahn": "🛣️ Fahrbahn", 
        "Ampel": "🚦 Ampel",
    } for word, emoji in replacements.items(): 
        message = message.replace(word, emoji) 

        # Hashtags anhängen 
        hashtags_text = " ".join(HASHTAGS)
        message = f"{message}\n{hashtags_text}"
        
        parts = []
        while len(message) > POST_MAX_LEN: 
            # Sicherstellen, dass wir nicht mitten in einem Hashtag splitten 
            split_idx = message.rfind(" ", 0, POST_MAX_LEN) 
            while split_idx > 0 and message[split_idx - 1] == "#":
                split_idx = message.rfind(" ", 0, split_idx - 1)
                
            if split_idx == -1:
                split_idx = POST_MAX_LEN
                
            parts.append(message[:split_idx].strip())
            message = message[split_idx:].strip()
            
            parts.append(message.strip()) 

            # Hashtags im Text korrigieren 
            parts = [part.replace("# ", "#") for part in parts]
            
            return parts
