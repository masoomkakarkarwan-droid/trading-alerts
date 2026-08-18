"""
Multi-timeframe structure helpers: EMA20, trend, SNR zone strength.
Built on top of the existing single-timeframe structure.py logic.
"""
import pandas as pd

def ema(df, period=20):
    return df['close'].ewm(span=period, adjust=False).mean()

def ema_alignment(df, period=20):
    """
    Returns 'bullish', 'bearish', or 'ranging' based on price vs EMA slope,
    per the rule: price above RISING ema = bullish, price below FALLING ema
    = bearish. Flat ema + price crossing repeatedly = ranging.
    """
    e = ema(df, period)
    if len(e) < 5 or e.isna().iloc[-5:].any():
        return "insufficient_data"
    curr_price = df['close'].iloc[-1]
    ema_now = e.iloc[-1]
    ema_slope = e.iloc[-1] - e.iloc[-5]
    slope_pct = abs(ema_slope) / ema_now if ema_now else 0

    if slope_pct < 0.0003:
        return "ranging"
    if curr_price > ema_now and ema_slope > 0:
        return "bullish"
    if curr_price < ema_now and ema_slope < 0:
        return "bearish"
    return "mixed"

def zone_strength(df, zones, window=3, tolerance_pct=0.0007):
    """
    Counts how many times price has touched/reacted near a given zone level
    across the dataframe's history -- more touches = stronger SNR.
    Returns the touch count for the zone closest to the current price.
    """
    if not zones:
        return 0
    curr_price = df['close'].iloc[-1]
    closest = min(zones, key=lambda z: abs(z[0] - curr_price))
    level = closest[0]
    tol = level * tolerance_pct
    touches = 0
    for _, row in df.iterrows():
        if abs(row['high'] - level) <= tol or abs(row['low'] - level) <= tol:
            touches += 1
    return touches

def candle_body_ratio(c):
    """Body size as a fraction of full candle range -- proxy for momentum
    strength when real volume isn't available on forex feeds."""
    rng = c['high'] - c['low']
    if rng == 0:
        return 0
    return abs(c['close'] - c['open']) / rng
