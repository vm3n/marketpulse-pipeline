# ingest/api_ingest.py

import requests   # sends HTTP requests — like your browser, but from Python
import json       # converts JSON text into Python dicts
import os         # lets us work with file paths and folders
from datetime import datetime  # for timestamps

# ─────────────────────────────────────────
# WHY A CONSTANT?
# We define the URL once at the top.
# If CoinGecko ever changes it, we fix it
# in ONE place — not scattered in 10 functions.
# ─────────────────────────────────────────
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# Which coins we want, and which currencies
COINS = ["bitcoin", "ethereum", "solana"]
CURRENCIES = ["usd", "usd_market_cap", "usd_24h_vol", "usd_24h_change"]

def fetch_prices():
    """
    WHY A FUNCTION?
    We wrap everything in a function so run_pipeline.py
    can simply call fetch_prices() without knowing HOW it works.
    This is called encapsulation.
    """
    print("[API] Fetching live prices from CoinGecko...")
    # ─────────────────────────────────────────
    # WHAT IS params?
    # Instead of building a messy URL string by hand like:
    # "...?ids=bitcoin,ethereum&vs_currencies=usd"
    # requests builds it cleanly from a dict.
    # ─────────────────────────────────────────
    params = {
        "ids": ",".join(COINS),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }

    # ─────────────────────────────────────────
    # WHY try/except?
    # Networks fail. The API might be down.
    # Without this, one network error crashes
    # your entire pipeline.
    # This is called defensive programming.
    # ─────────────────────────────────────────
    try:
        response = requests.get(COINGECKO_URL, params=params, timeout=10)

        # raise_for_status() throws an error if the server
        # returned 4xx or 5xx — e.g. 429 = rate limited
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"[API] ERROR: Could not fetch data — {e}")
        return None
    
    # ─────────────────────────────────────────
    # WHAT IS .json()?
    # The API returns a string of text like:
    # '{"bitcoin": {"usd": 67000, ...}}'
    # .json() converts that string into a real
    # Python dictionary you can work with.
    # ─────────────────────────────────────────
    
    data = response.json()
    
    # Add a timestamp — critical for pipelines!
    # You always want to know WHEN the data was captured.
    data["_fetched_at"] = datetime.utcnow().isoformat()
    
    print(f"[API] Success - got data for : {list(data.keys())}")
    return data


def save_raw(data):
    """
    WHY save the raw data at all?
    This is the 'raw store' concept from the pipeline diagram.
    We ALWAYS save what we received BEFORE transforming it.
    Why? Because if your transform logic has a bug,
    you can re-run the transform without hitting the API again.
    This is called idempotency in data engineering.
    """
    # Create a filename with a timestamp so each run
    # creates a NEW file instead of overwriting the last one
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"data/raw_prices_{timestamp}.json"
    
    # os.makedirs creates the folder if it doesn't exist yet
    os.makedirs("data", exist_ok=True)
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"[API] Raw data saved to {filename}")
    return filename


# ─────────────────────────────────────────
# WHY this if __name__ == "__main__" block?
# When you run this file directly (python api_ingest.py),
# this block runs. But when run_pipeline.py imports it,
# this block is SKIPPED — only the functions are imported.
# This lets the file work both ways.
# ─────────────────────────────────────────

if __name__ == "__main__":
    data = fetch_prices()
    if data:
        save_raw(data)