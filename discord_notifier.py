import os
import requests

def send_to_discord(message: str, webhook_url: str = None) -> bool:
    \"\"\"Send a plain text message to Discord via webhook. Returns True on success.\"\"\"
    if webhook_url is None:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False
    payload = {"content": message}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code in (200, 204)
    except Exception:
        return False
