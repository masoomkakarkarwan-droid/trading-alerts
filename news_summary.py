import requests
import os
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def get_news(query, count=3):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": count,
        "apiKey": NEWS_API_KEY
    }
    try:
        r = requests.get(url, params=params).json()
        return r.get("articles", [])
    except:
        return []

def get_economic_calendar():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/calendar/economic"
    params = {
        "from": today,
        "to": tomorrow,
        "token": FINNHUB_API_KEY
    }
    try:
        r = requests.get(url, params=params).json()
        events = r.get("economicCalendar", [])
        important = [e for e in events if e.get("impact") in ["high", "medium"]]
        return important[:5]
    except:
        return []

def daily_summary():
    msg = "📰 DAILY MARKET BRIEFING\n"
    msg += "=" * 28 + "\n\n"

    # Gold news
    msg += "🥇 GOLD NEWS\n"
    for a in get_news("gold price XAU", 2):
        msg += f"• {a['title']}\n  ({a['source']['name']})\n"
    msg += "\n"

    # Forex news
    msg += "💱 FOREX NEWS\n"
    for a in get_news("EUR USD forex currency", 2):
        msg += f"• {a['title']}\n  ({a['source']['name']})\n"
    msg += "\n"

    # CPI & macro news
    msg += "📊 MACRO / CPI NEWS\n"
    for a in get_news("CPI inflation interest rate Fed", 2):
        msg += f"• {a['title']}\n  ({a['source']['name']})\n"
    msg += "\n"

    # Pakistan economy news
    msg += "🇵🇰 PAKISTAN ECONOMY\n"
    for a in get_news("Pakistan economy rupee PKR", 2):
        msg += f"• {a['title']}\n  ({a['source']['name']})\n"
    msg += "\n"

    # Economic calendar
    msg += "📅 ECONOMIC EVENTS TODAY\n"
    events = get_economic_calendar()
    if events:
        for e in events:
            impact = e.get("impact", "").upper()
            country = e.get("country", "")
            event_name = e.get("event", "")
            time = e.get("time", "")
            msg += f"• [{impact}] {country} — {event_name} at {time}\n"
    else:
        msg += "• No major events today\n"

    send_telegram(msg)

daily_summary()
