"""
Fetches M15, M5, and M3 candles from Twelve Data, including a
constructed "forming" M3 candle for the early (partial) confirmation read.
"""
import os
import requests
import pandas as pd

TWELVE_DATA_BASE = "https://api.twelvedata.com/time_series"
REAL_PAIRS = ["EUR/USD", "EUR/JPY", "GBP/USD"]

def _fetch(symbol, interval, outputsize=60):
    api_key = os.environ.get("TWELVE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY not set.")
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize,
              "apikey": api_key, "format": "JSON"}
    resp = requests.get(TWELVE_DATA_BASE, params=params, timeout=15)
    data = resp.json()
    if "values" not in data:
        raise RuntimeError(f"Fetch failed for {symbol} ({interval}): {data.get('message', data)}")
    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime": "time"})
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["time"] = pd.to_datetime(df["time"])
    return df.sort_values("time").reset_index(drop=True)[["time", "open", "high", "low", "close"]]

def fetch_m15(symbol):
    return _fetch(symbol, "15min", 60)

def fetch_m5(symbol):
    return _fetch(symbol, "5min", 60)

def fetch_m3_and_forming(symbol):
    """
    Twelve Data doesn't offer a native 3-min interval reliably on the free
    tier, so we build M3 candles ourselves from 1-min data:
      - m3_recent: the last several FULLY CLOSED 3-min candles
      - m3_forming: the CURRENT, still-building 3-min candle (partial),
        used for the early ~2-minute-warning confirmation read.
    """
    df1 = _fetch(symbol, "1min", 30)
    df1["m3_bucket"] = df1["time"].dt.floor("3min")

    grouped = df1.groupby("m3_bucket")
    buckets = sorted(grouped.groups.keys())

    m3_candles = []
    for b in buckets:
        g = grouped.get_group(b)
        m3_candles.append({
            "time": b, "open": g["open"].iloc[0], "high": g["high"].max(),
            "low": g["low"].min(), "close": g["close"].iloc[-1],
            "n_1min_bars": len(g),
        })
    m3_df = pd.DataFrame(m3_candles)

    closed = m3_df[m3_df["n_1min_bars"] >= 3].reset_index(drop=True)
    forming_rows = m3_df[m3_df["n_1min_bars"] < 3]

    if len(forming_rows) == 0:
        return closed, None

    forming = forming_rows.iloc[-1]
    return closed, forming
