import sqlite3
import pandas as pd
import os

DB_PATH = "data/marketpulse.db"


def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    print("[DB] Initializing database...")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            coin      TEXT    NOT NULL,
            date      TEXT    NOT NULL,
            open      REAL,
            high      REAL,
            low       REAL,
            close     REAL,
            volume    REAL,
            marketcap REAL,
            UNIQUE(coin, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices_live (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            coin        TEXT    NOT NULL,
            price       REAL,
            market_cap  REAL,
            volume_24h  REAL,
            change_24h  REAL,
            fetched_at  TEXT    NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            link        TEXT    NOT NULL,
            published   TEXT,
            description TEXT,
            authors     TEXT,
            categories  TEXT,
            is_relevant INTEGER,
            scraped_at  TEXT,
            UNIQUE(link)
        )
    """)

    conn.commit()

    conn.commit()
    conn.close()
    print(f"[DB] Tables ready — {DB_PATH}")


def insert_history(df):
    """
    WHY INSERT OR IGNORE?
    Our UNIQUE(coin, date) constraint means the same
    coin+date combination can only exist once.
    INSERT OR IGNORE tells SQLite:
    "if this row already exists, silently skip it."
    This makes the pipeline safe to re-run anytime
    without duplicating data — that's idempotency.
    """
    print(f"[DB] Inserting historical rows...")

    conn = get_connection()
    cursor = conn.cursor()

    # ─────────────────────────────────────────
    # WHY not use to_sql() here?
    # to_sql() doesn't support INSERT OR IGNORE.
    # So we convert the DataFrame to a list of
    # tuples and insert row by row using
    # executemany() which is still fast.
    # ─────────────────────────────────────────
    # rows = df[[
    #     'coin', 'date', 'open', 'high',
    #     'low', 'close', 'volume', 'marketcap'
    # ]].values.tolist()
    df_insert = df[['coin', 'date', 'open', 'high', 'low', 'close', 'volume', 'marketcap']].copy()
    df_insert['date'] = df_insert['date'].astype(str)
    rows = df_insert.values.tolist()

    cursor.executemany("""
        INSERT OR IGNORE INTO prices_history
            (coin, date, open, high, low, close, volume, marketcap)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    inserted = cursor.rowcount
    conn.commit()
    conn.close()

    # ─────────────────────────────────────────
    # WHY show skipped count?
    # Tells you how many rows already existed.
    # On first run: inserted=5603, skipped=0
    # On second run: inserted=0, skipped=5603
    # This is how you confirm idempotency works.
    # ─────────────────────────────────────────
    skipped = len(df) - inserted if inserted >= 0 else 0
    print(f"[DB] prices_history — inserted: {inserted}, skipped: {skipped}")


def insert_live(df):
    print(f"[DB] Inserting {len(df)} rows into prices_live...")
    conn = get_connection()
    df.to_sql(
        name='prices_live',
        con=conn,
        if_exists='append',
        index=False,
        method='multi'
    )
    conn.close()
    print(f"[DB] prices_live insert complete")


def query(sql):
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def insert_news(df):
    """
    Inserts scraped news articles into the news table.
    Uses INSERT OR IGNORE on the unique link column
    so re-running never creates duplicates.
    """
    print(f"[DB] Inserting {len(df)} news articles...")

    conn = get_connection()
    cursor = conn.cursor()

    df_insert = df[[
        'title', 'link', 'published', 'description',
        'authors', 'categories', 'is_relevant', 'scraped_at'
    ]].copy()

    # Convert all datetime columns to string for SQLite
    df_insert['published']  = df_insert['published'].astype(str)
    df_insert['scraped_at'] = df_insert['scraped_at'].astype(str)

    # Convert boolean is_relevant to int (SQLite has no bool)
    df_insert['is_relevant'] = df_insert['is_relevant'].astype(int)

    rows = df_insert.values.tolist()

    cursor.executemany("""
        INSERT OR IGNORE INTO news
            (title, link, published, description,
             authors, categories, is_relevant, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    inserted = cursor.rowcount
    skipped  = len(df) - inserted if inserted >= 0 else 0
    conn.commit()
    conn.close()

    print(f"[DB] news — inserted: {inserted}, skipped: {skipped}")


if __name__ == "__main__":
    from ingest.csv_ingest import load_csv
    from transform.clean import clean_csv, clean_api
    import glob, json

    init_db()
    raw_df = load_csv()
    clean_df = clean_csv(raw_df)
    insert_history(clean_df)

    files = sorted(glob.glob("data/raw_prices_*.json"))
    if files:
        with open(files[-1]) as f:
            raw_api = json.load(f)
        api_df = clean_api(raw_api)
        insert_live(api_df)

    print("\n─── VERIFY ──────────────────────────────")
    print(query("SELECT coin, COUNT(*) as rows FROM prices_history GROUP BY coin").to_string(index=False))
