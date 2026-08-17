"""
Confluence engine: combines trend + S/R zone + candlestick pattern + wick
rejection into ONE setup summary. This is what gets handed to the signal
logic -- patterns never trigger a signal alone, only as part of full
confluence, per your framework:

  Trend + Key Levels + Candlestick Psychology + Reaction + Confirmation -> Entry
"""
from . import patterns as pat
from . import structure as struct

def build_setup_summary(df, window=3):
    """
    Returns a dict describing the current market state.
    Returns None if there isn't enough data yet.
    """
    if len(df) < window * 2 + 3:
        return None

    curr = df.iloc[-1]
    trend = struct.classify_trend(df, window)
    support_zones, resistance_zones = struct.get_key_levels(df, window)

    in_support = struct.price_in_zone(curr['close'], support_zones)
    in_resistance = struct.price_in_zone(curr['close'], resistance_zones)

    detected_patterns = pat.detect_all_patterns(df)
    wick_context = struct.wick_rejection_strength(curr)
    bb_signal = struct.bollinger_signal(df)

    if not detected_patterns:
        return None

    summary = {
        "trend": trend,
        "current_price": float(curr['close']),
        "at_support_zone": in_support,
        "at_resistance_zone": in_resistance,
        "patterns_detected": detected_patterns,
        "wick_rejection": wick_context,
        "bollinger_signal": bb_signal,
        "last_5_candles": df.tail(5)[['open', 'high', 'low', 'close']].to_dict('records'),
    }
    return summary

def has_confluence(summary):
    """
    Quick pre-filter: only pass setups through that have at least
    trend + a zone + a pattern together, matching your rule that
    patterns alone never trigger.
    """
    if summary is None:
        return False
    trend_known = summary['trend'] in ('bullish', 'bearish', 'sideways')
    near_zone = summary['at_support_zone'] is not None or summary['at_resistance_zone'] is not None
    has_pattern = len(summary['patterns_detected']) > 0
    return trend_known and near_zone and has_pattern
