import requests
import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def get_headlines(query, count=3):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": count,
        "apiKey": NEWS_API_KEY
    }
    r = requests.get(url, params=params).json()
    return r.get("articles", [])

def daily_summary():
    msg = "📰 DAILY MARKET NEWS\n\n"
    for label, query in [("GOLD", "gold price"), ("EUR/USD", "euro dollar forex")]:
        msg += f"— {label} —\n"
        articles = get_headlines(query)
        for a in articles:
            msg += f"• {a['title']} ({a['source']['name']})\n"
        msg += "\n"
    send_telegram(msg)

daily_summary()
