"""
Candlestick pattern detection module.
Each function takes a pandas DataFrame of OHLC candles (most recent last)
and returns True/False or a signal dict if the pattern is detected on the
LAST completed candle (index -1), using prior candles for context.

Columns expected: ['open', 'high', 'low', 'close']
"""
import pandas as pd

def body(c):
    return abs(c['close'] - c['open'])

def range_(c):
    return c['high'] - c['low']

def is_bull(c):
    return c['close'] > c['open']

def is_bear(c):
    return c['close'] < c['open']

def upper_wick(c):
    return c['high'] - max(c['close'], c['open'])

def lower_wick(c):
    return min(c['close'], c['open']) - c['low']

# ---------- SINGLE CANDLE PATTERNS ----------

def is_hammer(c):
    b = body(c)
    r = range_(c)
    if r == 0: return False
    return (lower_wick(c) >= 2 * b) and (upper_wick(c) <= b * 0.3) and (b > 0)

def is_inverted_hammer(c):
    b = body(c)
    r = range_(c)
    if r == 0: return False
    return (upper_wick(c) >= 2 * b) and (lower_wick(c) <= b * 0.3) and (b > 0)

def is_shooting_star(c, prior_trend_up=True):
    return is_inverted_hammer(c) and prior_trend_up

def is_hanging_man(c, prior_trend_up=True):
    return is_hammer(c) and prior_trend_up

def is_doji(c, threshold=0.1):
    r = range_(c)
    if r == 0: return False
    return body(c) <= threshold * r

def is_marubozu(c, wick_threshold=0.05):
    r = range_(c)
    if r == 0: return False
    return (upper_wick(c) <= wick_threshold * r) and (lower_wick(c) <= wick_threshold * r)

# ---------- TWO CANDLE PATTERNS ----------

def is_bullish_engulfing(prev, curr):
    return (is_bear(prev) and is_bull(curr) and
            curr['open'] <= prev['close'] and curr['close'] >= prev['open'])

def is_bearish_engulfing(prev, curr):
    return (is_bull(prev) and is_bear(curr) and
            curr['open'] >= prev['close'] and curr['close'] <= prev['open'])

def is_bullish_harami(prev, curr):
    return (is_bear(prev) and is_bull(curr) and
            curr['open'] > prev['close'] and curr['close'] < prev['open'])

def is_bearish_harami(prev, curr):
    return (is_bull(prev) and is_bear(curr) and
            curr['open'] < prev['close'] and curr['close'] > prev['open'])

def is_piercing_line(prev, curr):
    if not (is_bear(prev) and is_bull(curr)):
        return False
    midpoint = (prev['open'] + prev['close']) / 2
    return curr['open'] < prev['close'] and curr['close'] > midpoint and curr['close'] < prev['open']

def is_dark_cloud_cover(prev, curr):
    if not (is_bull(prev) and is_bear(curr)):
        return False
    midpoint = (prev['open'] + prev['close']) / 2
    return curr['open'] > prev['close'] and curr['close'] < midpoint and curr['close'] > prev['open']

# ---------- THREE CANDLE PATTERNS ----------

def is_morning_star(c1, c2, c3):
    return (is_bear(c1) and body(c1) > 0 and
            body(c2) < body(c1) * 0.5 and
            is_bull(c3) and c3['close'] > (c1['open'] + c1['close']) / 2)

def is_evening_star(c1, c2, c3):
    return (is_bull(c1) and body(c1) > 0 and
            body(c2) < body(c1) * 0.5 and
            is_bear(c3) and c3['close'] < (c1['open'] + c1['close']) / 2)

def is_three_white_soldiers(c1, c2, c3):
    return (is_bull(c1) and is_bull(c2) and is_bull(c3) and
            c2['close'] > c1['close'] and c3['close'] > c2['close'] and
            c2['open'] > c1['open'] and c3['open'] > c2['open'])

def is_three_black_crows(c1, c2, c3):
    return (is_bear(c1) and is_bear(c2) and is_bear(c3) and
            c2['close'] < c1['close'] and c3['close'] < c2['close'] and
            c2['open'] < c1['open'] and c3['open'] < c2['open'])

# ---------- LIQUIDITY SWEEP / BREAK-RETEST ----------

def is_bullish_liquidity_sweep(df, lookback=10):
    """Price wicks below recent low then closes back above it (stop hunt then reverse up)."""
    if len(df) < lookback + 1:
        return False
    recent = df.iloc[-(lookback+1):-1]
    curr = df.iloc[-1]
    recent_low = recent['low'].min()
    return curr['low'] < recent_low and curr['close'] > recent_low and is_bull(curr)

def is_bearish_liquidity_sweep(df, lookback=10):
    """Price wicks above recent high then closes back below it (stop hunt then reverse down)."""
    if len(df) < lookback + 1:
        return False
    recent = df.iloc[-(lookback+1):-1]
    curr = df.iloc[-1]
    recent_high = recent['high'].max()
    return curr['high'] > recent_high and curr['close'] < recent_high and is_bear(curr)

def detect_all_patterns(df):
    """
    Run all pattern checks against the latest candle(s) in df.
    Returns a list of detected pattern names.
    """
    detected = []
    if len(df) < 1:
        return detected
    curr = df.iloc[-1]

    if is_hammer(curr): detected.append('hammer')
    if is_inverted_hammer(curr): detected.append('inverted_hammer')
    if is_doji(curr): detected.append('doji')
    if is_marubozu(curr):
        detected.append('marubozu_bull' if is_bull(curr) else 'marubozu_bear')

    if len(df) >= 2:
        prev = df.iloc[-2]
        if is_bullish_engulfing(prev, curr): detected.append('bullish_engulfing')
        if is_bearish_engulfing(prev, curr): detected.append('bearish_engulfing')
        if is_bullish_harami(prev, curr): detected.append('bullish_harami')
        if is_bearish_harami(prev, curr): detected.append('bearish_harami')
        if is_piercing_line(prev, curr): detected.append('piercing_line')
        if is_dark_cloud_cover(prev, curr): detected.append('dark_cloud_cover')

    if len(df) >= 3:
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        if is_morning_star(c1, c2, c3): detected.append('morning_star')
        if is_evening_star(c1, c2, c3): detected.append('evening_star')
        if is_three_white_soldiers(c1, c2, c3): detected.append('three_white_soldiers')
        if is_three_black_crows(c1, c2, c3): detected.append('three_black_crows')

    if is_bullish_liquidity_sweep(df): detected.append('bullish_liquidity_sweep')
    if is_bearish_liquidity_sweep(df): detected.append('bearish_liquidity_sweep')

    return detected
