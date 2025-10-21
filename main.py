import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import json
load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("META_API_TOKEN")  # must match exactly what you entered in Meta dashboard

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)  # ✅ VERY IMPORTANT — return raw challenge
    else:
        return "Verification token mismatch", 403

@app.post("/webhook")
async def webhook_events(request: Request):
    data = await request.json()
    filename = data.get("field", "webhook")
    with open(f"{filename}.json", "w") as f:
        json.dump(data, f, indent=4)
    print("🔔 NEW WEBHOOK EVENT:", data)
    return {"status": "received"}
