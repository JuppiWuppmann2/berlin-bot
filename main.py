from fastapi import FastAPI, Request, HTTPException
import os
from tweet import send_tweet

app = FastAPI()
API_KEY = os.getenv("API_KEY")

@app.post("/tweet")
async def tweet(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = await request.json()
    text = data.get("text")
    if not text:
        return {"error": "No text provided"}
    await send_tweet(text)
    return {"status": "Tweet sent"}

