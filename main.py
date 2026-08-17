"""
Main runner (FREE version -- no AI API calls).
Fetches candles for each configured pair, runs the confluence engine
(trend + zone + pattern + wick + Bollinger context), and writes a
plain-English signal to a JSON file the dashboard reads.

Run this on a schedule (e.g. every 1 minute) via GitHub Actions --
100% free, no paid API calls.
"""
import json
import os
from datetime import datetime, timezone
from src.data_feed import fetch_candles, REAL_PAIRS
from src.confluence import build_setup_summary, has_confluence

OUTPUT_FILE = "docs/signals.json"

def describe_signal(summary):
    """
    Rule-based judgment (free, no AI) using the same confluence logic
    from your notes: trend + zone + pattern + wick rejection.
    """
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
        return "BUY", f"Bullish pattern ({', '.join(found_bullish)}) at support zone, trend={trend}, wick shows {wick}."

    if found_bearish and at_resistance and (trend in ('bearish', 'sideways') or wick == 'upper_wick_rejection'):
        return "SELL", f"Bearish pattern ({', '.join(found_bearish)}) at resistance zone, trend={trend}, wick shows {wick}."

    return "WAIT", f"Pattern(s) found ({patterns}) but confluence incomplete (trend={trend}, at_support={at_support}, at_resistance={at_resistance})."

def run():
    results = []
    for symbol in REAL_PAIRS:
        try:
            df = fetch_candles(symbol, interval="1min", outputsize=50)
        except Exception as e:
            results.append({
                "symbol": symbol,
                "signal": "ERROR",
                "reasoning": str(e),
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

        signal, reasoning = describe_signal(summary)
        results.append({
            "symbol": symbol,
            "signal": signal,
            "reasoning": reasoning,
            "trend": summary["trend"],
            "current_price": summary["current_price"],
            "patterns_detected": summary["patterns_detected"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Wrote {len(results)} results to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()
