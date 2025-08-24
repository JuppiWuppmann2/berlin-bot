import os
from twikit import Client

client = Client("de-DE")

async def send_tweet(text: str):
    await client.login(
        auth_info_1=os.getenv("TWIKIT_USERNAME"),
        auth_info_2=os.getenv("TWIKIT_EMAIL"),
        password=os.getenv("TWIKIT_PASSWORD")
    )
    await client.create_tweet(text)

