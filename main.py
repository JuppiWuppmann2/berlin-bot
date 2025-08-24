from fastapi import FastAPI, Request, HTTPException
import os
from tweet import send_tweet

app = FastAPI()
API_KEY = os.getenv("TWEET_API_KEY")

@app.get("/health")
def healthcheck():
    return {"status": "ok"}

@app.post("/tweet")
async def tweet(request: Request):
    auth = request.headers.get("Authorization")
    if not API_KEY or not auth or auth != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    text = data.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    await send_tweet(text)
    return {"status": "sent"}
