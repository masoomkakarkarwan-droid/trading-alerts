import requests
import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": "✅ Test message — if you see this, the connection works!"})
print(r.status_code, r.text)
