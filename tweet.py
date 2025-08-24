import os
from pathlib import Path
from twikit import Client

COOKIE_FILE = Path("cookies.json")
client = Client("de-DE")

async def ensure_login():
    if COOKIE_FILE.exists():
        try:
            await client.load_cookies(str(COOKIE_FILE))
            await client.get_user_by_screen_name(os.getenv("TWIKIT_USERNAME"))
            return
        except Exception:
            pass
    await client.login(
        auth_info_1=os.getenv("TWIKIT_USERNAME"),
        auth_info_2=os.getenv("TWIKIT_EMAIL"),
        password=os.getenv("TWIKIT_PASSWORD")
    )
    client.save_cookies(str(COOKIE_FILE))

async def send_tweet(text: str):
    await ensure_login()
    await client.create_tweet(text)
    client.save_cookies(str(COOKIE_FILE))
