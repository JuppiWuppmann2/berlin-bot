from fastapi import FastAPI, Request
from tweet import send_tweet

app = FastAPI()

@app.post("/tweet")
async def tweet(request: Request):
    data = await request.json()
    text = data.get("text")
    if not text:
        return {"error": "No text provided"}
    await send_tweet(text)
    return {"status": "Tweet sent"}
