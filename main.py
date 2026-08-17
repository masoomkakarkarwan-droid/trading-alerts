"""
Main runner: fetches candles for each configured pair, checks for
confluence setups, and if found, asks the AI to judge it, then writes
results to a JSON file the dashboard reads.

Run this on a schedule (e.g. every 1 minute) via GitHub Actions.
"""
import json
import os
from datetime import datetime, timezone
from src.data_feed import fetch_candles, REAL_PAIRS
from src.confluence import build_setup_summary, has_confluence
from src.ai_judge import judge_setup

OUTPUT_FILE = "docs/signals.json"

def run():
    results = []
    for symbol in REAL_PAIRS:
        try:
            df = fetch_candles(symbol, interval="1min", outputsize=50)
        except Exception as e:
            results.append({
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            continue

        summary = build_setup_summary(df)

        if not has_confluence(summary):
            results.append({
                "symbol": symbol,
                "signal": "WAIT",
                "reasoning": "No confluence setup detected (missing trend/zone/pattern alignment).",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            continue

        try:
            ai_response = judge_setup(summary, symbol)
        except Exception as e:
            ai_response = f"AI judge error: {e}"

        results.append({
            "symbol": symbol,
            "setup": summary,
            "ai_response": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Wrote {len(results)} results to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()
