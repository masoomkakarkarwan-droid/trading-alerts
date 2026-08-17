import json
import os
import requests
from datetime import datetime, timezone
from src.data_feed import fetch_candles, REAL_PAIRS
from src.confluence import build_setup_summary, has_confluence

OUTPUT_FILE = "docs/signals.json"

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

def describe_signal(summary):
    patterns = summary['patterns_detected']
    trend = summary['trend']
    at_support = summary['at_support_zone'] is not None
    at_resistance = summary['at_resistance_zone'] is not None
    wick = summary['wick_rejection']

    bullish_patterns = {'hammer', 'bullish_engulfing', 'bullish_harami',
                         'piercing_line', 'morning_star', 'three_white_soldiers',
                         'bullish_liquidity_sweep', 'marubozu_bull'}
    bearish_patterns = {'shooting_star', 'bearish_engulfing', 'bearish_harami',
                         'dark_cloud_cover', 'evening_star', 'three_black_crows',
                         'bearish_liquidity_sweep', 'marubozu_bear'}

    found_bullish = [p for p in patterns if p in bullish_patterns]
    found_bearish = [p for p in patterns if p in bearish_patterns]

    if found_bullish and at_support and (trend in ('bullish', 'sideways') or wick == 'lower_wick_rejection'):
        return "BUY", f"Bullish pattern ({', '.join(found_bullish)}) at support zone, trend={trend}."
    if found_bearish and at_resistance and (trend in ('bearish', 'sideways') or wick == 'upper_wick_rejection'):
        return "SELL", f"Bearish pattern ({', '.join(found_bearish)}) at resistance zone, trend={trend}."
    return "WAIT", f"No clear setup (trend={trend})."

def run():
    results = []
    for symbol in REAL_PAIRS:
        try:
            df = fetch_candles(symbol, interval="1min", outputsize=50)
        except Exception as e:
            results.append({"symbol": symbol, "signal": "ERROR", "reasoning": str(e),
                             "timestamp": datetime.now(timezone.utc).isoformat()})
            continue

        summary = build_setup_summary(df)
        if not has_confluence(summary):
            results.append({"symbol": symbol, "signal": "WAIT",
                             "reasoning": "No confluence setup detected.",
                             "timestamp": datetime.now(timezone.utc).isoformat()})
            continue

        signal, reasoning = describe_signal(summary)
        results.append({
            "symbol": symbol, "signal": signal, "reasoning": reasoning,
            "trend": summary["trend"], "current_price": summary["current_price"],
            "patterns_detected": summary["patterns_detected"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        if signal in ("BUY", "SELL"):
            direction = "GREEN (bullish)" if signal == "BUY" else "RED (bearish)"
            msg = (f"⚡ {symbol}\nNext 1-min candle likely: {direction}\n"
                   f"Price: {summary['current_price']}\nReason: {reasoning}\n"
                   f"(Not 100% — confirm before entry)")
            send_telegram(msg)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Wrote {len(results)} results")

if __name__ == "__main__":
    run()
