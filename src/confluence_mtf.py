"""
Multi-timeframe confluence scoring engine, per your framework:
M15 trend -> M5 setup -> M3 confirmation, scored 0-100.

Score breakdown (your spec):
  M15 trend direction     = 20
  M15 structure/SNR       = 20
  M5 setup (pullback)     = 20
  20 EMA alignment        = 15
  M3 confirmation         = 15
  Volume/momentum proxy   = 10
  Total                   = 100

Thresholds: 90-100 A+, 75-89 acceptable, below 75 = NO TRADE.
Honesty note: forex/OTC feeds usually carry no real volume, so the
"volume" factor uses candle-body-ratio as a momentum proxy instead.
"""
from . import structure as struct
from . import structure_mtf as mtf

THRESHOLD = 75

def score_setup(df15, df5, m3_recent, m3_forming):
    if len(df15) < 10 or len(df5) < 10 or len(m3_recent) < 3:
        return 0, None, {}

    breakdown = {}

    trend15 = struct.classify_trend(df15)
    trend_pts = 20 if trend15 in ('bullish', 'bearish') else 0
    breakdown['m15_trend'] = trend15
    if trend15 not in ('bullish', 'bearish'):
        return 0, None, breakdown

    direction = "BUY" if trend15 == "bullish" else "SELL"

    support15, resistance15 = struct.get_key_levels(df15)
    curr_price = df15['close'].iloc[-1]
    zones = support15 if direction == "BUY" else resistance15
    touches = mtf.zone_strength(df15, zones)
    near_zone = struct.price_in_zone(curr_price, zones) is not None
    structure_pts = 20 if (near_zone and touches >= 2) else (10 if near_zone else 0)
    breakdown['m15_structure_touches'] = touches
    breakdown['near_m15_zone'] = near_zone

    support5, resistance5 = struct.get_key_levels(df5)
    zones5 = support5 if direction == "BUY" else resistance5
    price5 = df5['close'].iloc[-1]
    near_zone5 = struct.price_in_zone(price5, zones5) is not None
    trend5 = struct.classify_trend(df5)
    setup_pts = 20 if (near_zone5 and trend5 in (trend15, 'sideways')) else (10 if near_zone5 else 0)
    breakdown['m5_near_zone'] = near_zone5
    breakdown['m5_trend'] = trend5

    align15 = mtf.ema_alignment(df15)
    align5 = mtf.ema_alignment(df5)
    wanted = "bullish" if direction == "BUY" else "bearish"
    ema_pts = 0
    if align15 == wanted:
        ema_pts += 8
    if align5 == wanted:
        ema_pts += 7
    breakdown['ema_m15'] = align15
    breakdown['ema_m5'] = align5

    prev_m3 = m3_recent.iloc[-1]
    conf_pts = 0
    if direction == "BUY":
        if m3_forming['close'] > m3_forming['open'] and m3_forming['low'] <= prev_m3['low']:
            conf_pts = 15
        elif m3_forming['close'] > m3_forming['open']:
            conf_pts = 8
    else:
        if m3_forming['close'] < m3_forming['open'] and m3_forming['high'] >= prev_m3['high']:
            conf_pts = 15
        elif m3_forming['close'] < m3_forming['open']:
            conf_pts = 8
    breakdown['m3_confirmation_partial'] = conf_pts

    ratios = [mtf.candle_body_ratio(m3_recent.iloc[-i]) for i in range(1, 4)]
    avg_ratio = sum(ratios) / len(ratios)
    momentum_pts = 10 if avg_ratio > 0.5 else (5 if avg_ratio > 0.3 else 0)
    breakdown['momentum_body_ratio'] = round(avg_ratio, 2)

    total = trend_pts + structure_pts + setup_pts + ema_pts + conf_pts + momentum_pts
    breakdown['scores'] = {
        'm15_trend': trend_pts, 'm15_structure': structure_pts,
        'm5_setup': setup_pts, 'ema_alignment': ema_pts,
        'm3_confirmation': conf_pts, 'momentum': momentum_pts,
        'total': total
    }

    if total < THRESHOLD:
        return total, None, breakdown

    return total, direction, breakdown
