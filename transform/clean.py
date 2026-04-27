import pandas as pd
import json
import os
from datetime import datetime

def clean_csv(df):
    """
    Takes the raw combined DataFrame from csv_ingest
    and fixes every problem we found in the inspect step.
    """
    print("[TRANSFORM] Cleaning CSV data...")

    # ─────────────────────────────────────────
    # STEP 1: Drop useless columns
    # WHY? SNo is just a row number from the original file.
    # Name and Symbol are redundant — we have our 'coin' column.
    # Less columns = less memory = faster pipeline.
    # ─────────────────────────────────────────
    df = df.drop(columns=['SNo', 'Name', 'Symbol'])
    print(f"[TRANSFORM] Dropped SNo, Name, Symbol columns")

    # ─────────────────────────────────────────
    # STEP 2: Convert Date from string to datetime
    # WHY? Right now "2013-04-29 23:59:59" is just text.
    # After this, pandas understands it as a real date.
    # You can then filter by date, sort by date,
    # calculate time differences etc.
    # errors='coerce' means: if a date is unparseable,
    # set it to NaT (Not a Time) instead of crashing.
    # ─────────────────────────────────────────
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    print(f"[TRANSFORM] Converted Date to datetime")

    # ─────────────────────────────────────────
    # STEP 3: Replace zero Volume with NaN
    # WHY? 0.0 volume doesn't mean nobody traded —
    # it means the data wasn't recorded yet.
    # NaN is the honest way to say "we don't know".
    # If we leave zeros, any average/sum calculation
    # on Volume will be wrong.
    # ─────────────────────────────────────────
    zero_before = (df['Volume'] == 0.0).sum()
    df['Volume'] = df['Volume'].replace(0.0, float('nan'))
    print(f"[TRANSFORM] Replaced {zero_before} zero Volume values with NaN")

    # ─────────────────────────────────────────
    # STEP 4: Round numeric columns to 2 decimal places
    # WHY? 144.539993286132812 and 144.54 mean the same
    # thing in finance. Extra decimals are just noise
    # from floating point storage. Clean data is readable data.
    # ─────────────────────────────────────────
    numeric_cols = ['High', 'Low', 'Open', 'Close', 'Volume', 'Marketcap']
    df[numeric_cols] = df[numeric_cols].round(2)
    print(f"[TRANSFORM] Rounded numeric columns to 2 decimal places")

    # ─────────────────────────────────────────
    # STEP 5: Rename columns to lowercase
    # WHY? Consistency. Our API data uses lowercase keys.
    # Our coin column is lowercase. Having 'Close' and
    # 'coin' mixed is sloppy. In databases, lowercase
    # column names are the standard.
    # ─────────────────────────────────────────
    df.columns = df.columns.str.lower()
    print(f"[TRANSFORM] Renamed all columns to lowercase")

    # ─────────────────────────────────────────
    # STEP 6: Sort by coin and date
    # WHY? Data should be in chronological order
    # per coin. Makes it easier to read, query,
    # and plot later. reset_index() renumbers rows
    # from 0 after sorting.
    # ─────────────────────────────────────────
    df = df.sort_values(['coin', 'date']).reset_index(drop=True)
    print(f"[TRANSFORM] Sorted by coin and date")

    print(f"[TRANSFORM] CSV clean complete — {len(df)} rows, {len(df.columns)} columns")
    return df


def clean_api(raw):
    """
    Takes the raw nested JSON dict from api_ingest
    and flattens it into a proper DataFrame.

    Raw looks like:
    {
      "bitcoin": {"usd": 77805, "usd_market_cap": ..., "usd_24h_change": ...},
      "ethereum": {...},
      "_fetched_at": "2026-04-23T..."
    }

    We need it to look like:
    coin     | price  | market_cap | volume_24h | change_24h | fetched_at
    bitcoin  | 77805  | 1.55T      | 44.4B      | -1.18      | 2026-04-23
    ethereum | 2321   | 280B       | 19.1B      | -3.21      | 2026-04-23
    """
    print("[TRANSFORM] Cleaning API data...")

    # Pull out the timestamp before we loop
    # WHY pop? It removes _fetched_at from the dict
    # so it doesn't get treated as a coin in the loop below
    fetched_at = raw.pop('_fetched_at', None)

    rows = []

    for coin, values in raw.items():
        # ─────────────────────────────────────────
        # WHY .get() instead of values['usd']?
        # .get() returns None if the key doesn't exist
        # instead of crashing. Defensive programming again.
        # ─────────────────────────────────────────
        row = {
            'coin':        coin,
            'price':       values.get('usd'),
            'market_cap':  values.get('usd_market_cap'),
            'volume_24h':  values.get('usd_24h_vol'),
            'change_24h':  values.get('usd_24h_change'),
            'fetched_at':  fetched_at,
        }
        rows.append(row)

    # Convert list of dicts → DataFrame
    # WHY this pattern? Each dict in the list becomes
    # one row. Keys become column names automatically.
    df = pd.DataFrame(rows)

    # Round price and change columns
    df['price']      = df['price'].round(2)
    df['change_24h'] = df['change_24h'].round(4)
    df['market_cap'] = df['market_cap'].round(2)
    df['volume_24h'] = df['volume_24h'].round(2)

    # Convert fetched_at to datetime
    df['fetched_at'] = pd.to_datetime(df['fetched_at'])

    print(f"[TRANSFORM] API clean complete — {len(df)} rows")
    return df


if __name__ == "__main__":
    # ── Test clean_csv ────────────────────────
    from ingest.csv_ingest import load_csv
    raw_df = load_csv()
    if raw_df is not None:
        clean_df = clean_csv(raw_df)

        print("\n─── CLEANED CSV SAMPLE ──────────────────")
        print(clean_df.groupby('coin').head(2)[
            ['coin', 'date', 'open', 'close', 'volume']
        ].to_string(index=False))

        print("\n─── DATA TYPES AFTER CLEAN ──────────────")
        print(clean_df.dtypes)

        print("\n─── MISSING VALUES AFTER CLEAN ──────────")
        print(clean_df.isnull().sum())

    # ── Test clean_api ────────────────────────
    import json, glob

    # Find the most recent raw API file
    files = sorted(glob.glob("data/raw_prices_*.json"))
    if files:
        latest = files[-1]
        print(f"\n[TEST] Loading API file: {latest}")
        with open(latest) as f:
            raw_api = json.load(f)
        api_df = clean_api(raw_api)
        print("\n─── CLEANED API DATA ────────────────────")
        print(api_df.to_string(index=False))
