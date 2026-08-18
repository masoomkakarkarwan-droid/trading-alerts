"""
Main runner: multi-timeframe (M15 -> M5 -> M3) confluence scanner.
Targets ~20-25 quality signals/day by requiring a 75+ confluence score.
"""
import json
import os
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from src.data_feed_mtf import fetch_m15, fetch_m5, fetch_m3_and_forming, REAL_PAIRS
from src.confluence_mtf import score_setup, THRESHOLD

OUTPUT_FILE = "docs/signals.json"
COOLDOWN_MINUTES = 20
_last_signal_file = "docs/last_signal_times.json"

def load_cooldowns():
    try:
        with open(_last_signal_file) as f:
            return json.load(f)
    except Exception:
        return {}

def save_cooldowns(data):
    os.makedirs(os.path.dirname(_last_signal_file), exist_ok=True)
    with open(_last_signal_file, "w") as f:
        json.dump(data, f)

def in_cooldown(symbol, cooldowns):
    last = cooldowns.get(symbol)
    if not last:
        return False
    last_time = datetime.fromisoformat(last)
    elapsed = (datetime.now(timezone.utc) - last_time).total_seconds() / 60
    return elapsed < COOLDOWN_MINUTES

def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")

def run():
    results = []
    cooldowns = load_cooldowns()

    for symbol in REAL_PAIRS:
        try:
            df15 = fetch_m15(symbol)
            df5 = fetch_m5(symbol)
            m3_closed, m3_forming = fetch_m3_and_forming(symbol)
        except Exception as e:
            results.append({"symbol": symbol, "signal": "ERROR", "reasoning": str(e),
                             "timestamp": datetime.now(timezone.utc).isoformat()})
            continue

        if m3_forming is None:
            results.append({"symbol": symbol, "signal": "WAIT",
                             "reasoning": "No forming M3 candle available yet this cycle.",
                             "timestamp": datetime.now(timezone.utc).isoformat()})
            continue

        score, direction, breakdown = score_setup(df15, df5, m3_closed, m3_forming)

        if direction is None or in_cooldown(symbol, cooldowns):
            reason = "Below confluence threshold" if direction is None else "In cooldown after recent signal"
            results.append({"symbol": symbol, "signal": "WAIT", "score": score,
                             "reasoning": reason, "breakdown": breakdown,
                             "timestamp": datetime.now(timezone.utc).isoformat()})
            continue

        results.append({
            "symbol": symbol, "signal": direction, "score": score,
            "reasoning": f"Confluence score {score}/100 (threshold {THRESHOLD})",
            "breakdown": breakdown, "current_price": float(df5['close'].iloc[-1]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        direction_word = "GREEN (bullish)" if direction == "BUY" else "RED (bearish)"
        current_price = float(df5['close'].iloc[-1])

        now_utc = datetime.now(timezone.utc)
        minutes_to_next = 3 - (now_utc.minute % 3)
        if minutes_to_next == 0:
            minutes_to_next = 3
        next_candle_utc = (now_utc + timedelta(minutes=minutes_to_next)).replace(second=0, microsecond=0)
        next_candle_pkt = next_candle_utc.astimezone(ZoneInfo("Asia/Karachi"))

        msg = (f"⚡ {symbol} — Score {score}/100\n"
               f"Current price: {current_price}\n"
               f"Next M3 candle likely: {direction_word}\n"
               f"Candle opens at: {next_candle_pkt.strftime('%I:%M:%S %p')} PKT\n"
               f"M15 trend: {breakdown.get('m15_trend')}\n"
               f"(Validated probability, not guaranteed — manage risk)")
        send_telegram(msg)

        cooldowns[symbol] = datetime.now(timezone.utc).isoformat()

    save_cooldowns(cooldowns)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Wrote {len(results)} results")

if __name__ == "__main__":
    run()
