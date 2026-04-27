import json
import glob
from datetime import datetime

from ingest.api_ingest  import fetch_prices, save_raw
from ingest.csv_ingest  import load_csv
from transform.clean    import clean_csv, clean_api
#from store.db           import init_db, insert_history, insert_live, query
from ingest.scraper import fetch_news, save_raw as save_news, to_dataframe
from store.db       import init_db, insert_history, insert_live, insert_news, query

def run():
    start = datetime.now()
    print("=" * 50)
    print(f"MARKETPULSE PIPELINE — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # ── STEP 1: Initialize database ───────────
    print("\n[1/5] Setting up database...")
    init_db()

    # ── STEP 2: Fetch live API prices ─────────
    print("\n[2/5] Fetching live prices...")
    raw_api = fetch_prices()
    if raw_api:
        save_raw(raw_api)
    else:
        print("[WARN] API fetch failed — skipping live insert")
        
    # ── STEP 2b: Scrape news headlines ────────
    print("\n[2b/5] Scraping news headlines...")
    articles = fetch_news()
    if articles:
        save_news(articles)
        news_df = to_dataframe(articles)
        insert_news(news_df)

    # ── STEP 3: Load historical CSV data ──────
    print("\n[3/5] Loading historical CSV data...")
    raw_df = load_csv()

    # ── STEP 4: Transform everything ──────────
    print("\n[4/5] Transforming data...")
    if raw_df is not None:
        clean_df = clean_csv(raw_df)
        insert_history(clean_df)

    if raw_api:
        api_df = clean_api(raw_api)
        insert_live(api_df)

    # ── STEP 5: Summary report ─────────────────
    print("\n[5/5] Pipeline summary...")
    print("\n─── DATABASE STATE ──────────────────────")
    summary = query("""
        SELECT coin,
               COUNT(*)             AS history_rows,
               ROUND(MAX(close), 2) AS last_hist_price,
               MAX(date)            AS last_hist_date
        FROM prices_history
        GROUP BY coin
    """)
    print(summary.to_string(index=False))

    print("\n─── LATEST LIVE PRICES ──────────────────")
    live = query("""
        SELECT coin, price, change_24h, fetched_at
        FROM prices_live
        ORDER BY fetched_at DESC
        LIMIT 3
    """)
    print(live.to_string(index=False))

    elapsed = (datetime.now() - start).seconds
    print(f"\n{'=' * 50}")
    print(f"PIPELINE COMPLETE in {elapsed}s")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run()
