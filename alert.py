import requests
import os

TWELVE_DATA_API_KEY = os.environ["TWELVE_DATA_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PAIRS = ["XAU/USD", "EUR/USD"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def get_rsi(symbol):
    url = "https://api.twelvedata.com/rsi"
    params = {
        "symbol": symbol,
        "interval": "15min",
        "apikey": TWELVE_DATA_API_KEY
    }
    r = requests.get(url, params=params).json()
    try:
        return float(r["values"][0]["rsi"])
    except:
        return None

def check_alerts():
    for pair in PAIRS:
        rsi = get_rsi(pair)
        if rsi is None:
            continue
        if rsi > 70:
            send_telegram(f"⚠️ {pair} RSI = {rsi:.2f} -> OVERBOUGHT (possible SELL)")
        elif rsi < 30:
            send_telegram(f"⚠️ {pair} RSI = {rsi:.2f} -> OVERSOLD (possible BUY)")
        else:
            print(f"{pair}: RSI = {rsi:.2f} (normal)")

check_alerts()
