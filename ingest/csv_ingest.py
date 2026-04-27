import pandas as pd
import os

# ─────────────────────────────────────────
# WHY a list of files instead of one?
# Scalable — if you add Cardano tomorrow,
# you just add one line here. Nothing else changes.
# ─────────────────────────────────────────
CSV_FILES = {
    "bitcoin":  "data/coin_Bitcoin.csv",
    "ethereum": "data/coin_Ethereum.csv",
    "solana":   "data/coin_Solana.csv",
}

def load_csv(files = CSV_FILES):
    """
    Loads all CSV files and stacks them into
    one unified DataFrame with a 'coin' column
    so you always know which row belongs to which asset.
    """
    print("[CSV] Loading historical CSV files...")

    # ─────────────────────────────────────────
    # WHY an empty list first?
    # We load each file into a separate DataFrame,
    # collect them in a list, then stack them all
    # at once at the end. This is more efficient
    # than stacking one by one in a loop.
    # ─────────────────────────────────────────
    all_frames = []
    
    for coin_name,path in files.items():
        
        if not os.path.exists(path):
            print(f"[CSV] WARNING: {path} not found — skipping")
            continue
        df = pd.read_csv(path)
        df['coin'] = coin_name
        
        print(f"[CSV] {coin_name}: {len(df)} rows loaded "
              f"({df['Date'].min()[:10]} → {df['Date'].max()[:10]})")
        
        all_frames.append(df)
        
    if not all_frames:
        print("[CSV] ERROR: No files were loaded.")
        return None
    
    # ─────────────────────────────────────────
    # WHAT IS pd.concat()?
    # concat = concatenate = stack vertically.
    # ignore_index=True resets row numbers from
    # 0 to N instead of repeating 0,1,2 three times.
    # ─────────────────────────────────────────
    combined = pd.concat(all_frames, ignore_index=True)

    print(f"\n[CSV] Combined: {len(combined)} total rows "
          f"across {combined['coin'].nunique()} coins")

    return combined

def inspect(df):
    """
    Development tool — understand your data before transforming it.
    Never called in the production pipeline.
    """

    print("\n─── SHAPE ───────────────────────────────")
    print(f"Rows: {df.shape[0]:,}   Columns: {df.shape[1]}")

    print("\n─── COINS IN THIS DATASET ───────────────")
    # value_counts shows how many rows each coin has
    print(df['coin'].value_counts())

    print("\n─── DATA TYPES ──────────────────────────")
    # Look for: is Date an 'object' (string) or 'datetime'?
    # Right now it'll be object — we fix that in transform.
    print(df.dtypes)

    print("\n─── MISSING VALUES ──────────────────────")
    print(df.isnull().sum())

    print("\n─── ZERO VOLUME ROWS ────────────────────")
    # Zero volume = suspicious — probably missing data
    zero_vol = (df['Volume'] == 0.0).sum()
    print(f"Rows where Volume is 0.0: {zero_vol:,}")

    print("\n─── SAMPLE: first 2 rows per coin ───────")
    print(df.groupby('coin').head(2)[
        ['coin', 'Date', 'Open', 'Close', 'Volume']
    ].to_string(index=False))


if __name__ == "__main__":
    df = load_csv()
    if df is not None:
        inspect(df)
