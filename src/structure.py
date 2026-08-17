"""
Market structure detection: trend (HH/HL vs LH/LL), support/resistance zones,
change of polarity, and Bollinger Bands (period 10, deviation 2) per your notes.
"""
import pandas as pd
import numpy as np

def find_swing_points(df, window=3):
    """
    Identify swing highs and swing lows using a simple rolling window comparison.
    A swing high = local max over `window` candles on each side.
    A swing low = local min over `window` candles on each side.
    """
    highs = df['high']
    lows = df['low']
    swing_highs = []
    swing_lows = []
    for i in range(window, len(df) - window):
        if highs.iloc[i] == highs.iloc[i-window:i+window+1].max():
            swing_highs.append((i, highs.iloc[i]))
        if lows.iloc[i] == lows.iloc[i-window:i+window+1].min():
            swing_lows.append((i, lows.iloc[i]))
    return swing_highs, swing_lows

def classify_trend(df, window=3):
    """
    Classify trend using swing structure:
    - Bullish: higher highs AND higher lows (most recent two swings each)
    - Bearish: lower highs AND lower lows
    - Sideways/ranging: otherwise
    """
    swing_highs, swing_lows = find_swing_points(df, window)
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "insufficient_data"

    last_two_highs = [h[1] for h in swing_highs[-2:]]
    last_two_lows = [l[1] for l in swing_lows[-2:]]

    higher_high = last_two_highs[-1] > last_two_highs[-2]
    higher_low = last_two_lows[-1] > last_two_lows[-2]
    lower_high = last_two_highs[-1] < last_two_highs[-2]
    lower_low = last_two_lows[-1] < last_two_lows[-2]

    if higher_high and higher_low:
        return "bullish"
    elif lower_high and lower_low:
        return "bearish"
    else:
        return "sideways"

def get_key_levels(df, window=3, zone_pct=0.0005):
    """
    Return recent support/resistance ZONES (not exact lines), each as
    (level_price, zone_low, zone_high), built from swing highs/lows.
    zone_pct = the +/- buffer around the swing point that counts as "in the zone".
    """
    swing_highs, swing_lows = find_swing_points(df, window)
    resistance_zones = [
        (price, price * (1 - zone_pct), price * (1 + zone_pct))
        for _, price in swing_highs[-5:]
    ]
    support_zones = [
        (price, price * (1 - zone_pct), price * (1 + zone_pct))
        for _, price in swing_lows[-5:]
    ]
    return support_zones, resistance_zones

def price_in_zone(price, zones):
    """Check if price currently sits inside any given S/R zone list."""
    for level, low, high in zones:
        if low <= price <= high:
            return level
    return None

def detect_change_of_polarity(df, broken_level, was_support, window=3):
    """
    Per your notes: when a support level breaks, it becomes resistance (and
    vice versa). This checks if price has since returned to retest that
    flipped level, which is a classic confirmation signal.
    """
    curr = df.iloc[-1]
    tolerance = broken_level * 0.0005
    near_level = abs(curr['close'] - broken_level) <= tolerance
    if not near_level:
        return None
    if was_support:
        return "retest_as_resistance"
    else:
        return "retest_as_support"

def bollinger_bands(df, period=10, deviation=2):
    """
    Your specified setting: period=10, deviation=2.
    Returns dataframe with 'bb_mid', 'bb_upper', 'bb_lower' columns.
    """
    mid = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = mid + deviation * std
    lower = mid - deviation * std
    out = df.copy()
    out['bb_mid'] = mid
    out['bb_upper'] = upper
    out['bb_lower'] = lower
    return out

def bollinger_signal(df, period=10, deviation=2):
    """
    Per your notes: break of upper band -> expect retrace down.
    Break of lower band -> expect retrace up.
    """
    bb = bollinger_bands(df, period, deviation)
    curr = bb.iloc[-1]
    if pd.isna(curr['bb_upper']) or pd.isna(curr['bb_lower']):
        return None
    if curr['close'] > curr['bb_upper']:
        return "above_upper_band_expect_retrace_down"
    elif curr['close'] < curr['bb_lower']:
        return "below_lower_band_expect_retrace_up"
    return None

def wick_rejection_strength(c):
    """
    Per your notes: long upper wick = weakness/rejection at highs,
    long lower wick = weakness/rejection at lows. Returns a simple
    description used as context for the AI reasoning layer.
    """
    b = abs(c['close'] - c['open'])
    upper = c['high'] - max(c['close'], c['open'])
    lower = min(c['close'], c['open']) - c['low']
    if b == 0:
        b = 1e-9
    if upper > b * 1.5:
        return "upper_wick_rejection"
    if lower > b * 1.5:
        return "lower_wick_rejection"
    return "no_significant_rejection"
