"""
Fetches live 1-minute candles from Twelve Data.
Reads the API key from the TWELVE_DATA_API_KEY environment variable
(set as a GitHub Actions secret -- never hardcode it here).
"""
import os
import requests
import pandas as pd

TWELVE_DATA_BASE = "https://api.twelvedata.com/time_series"

# Real-market pairs (will match Pocket Option's real, non-OTC listings)
REAL_PAIRS = ["EUR/USD", "EUR/JPY", "GBP/USD"]

def fetch_candles(symbol, interval="1min", outputsize=50):
    """
    Fetch the latest `outputsize` 1-min candles for a symbol from Twelve Data.
    Returns a DataFrame sorted oldest -> newest (required for pattern detection).
    """
    api_key = os.environ.get("TWELVE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY not set. Add it as a GitHub Actions secret "
            "and reference it in the workflow's 'env:' block."
        )

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key,
        "format": "JSON",
    }
    resp = requests.get(TWELVE_DATA_BASE, params=params, timeout=15)
    data = resp.json()

    if "values" not in data:
        raise RuntimeError(f"Fetch failed for {symbol}: {data.get('message', data)}")

    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime": "time"})
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df[["time", "open", "high", "low", "close"]]

def check_symbol_available(symbol):
    """
    Quick availability check -- used once to confirm which of your
    requested pairs Twelve Data actually supports.
    """
    try:
        df = fetch_candles(symbol, outputsize=1)
        return True, len(df)
    except Exception as e:
        return False, str(e)
