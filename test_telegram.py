import os
import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat = os.environ["TELEGRAM_CHAT_ID"]

resp = httpx.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat, "text": "✓ DEX Agent test — Telegram is connected!"},
    timeout=15.0,
)
print("Status:", resp.status_code)
print("Response:", resp.text)
