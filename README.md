# MarketPulse Pipeline

A live data pipeline that tracks Bitcoin, Ethereum, and Solana — combining 8 years of historical data with real-time prices and crypto news, served on a live dashboard.

🔗 **Live Dashboard:** https://marketpulse-pipeline-production.up.railway.app

---

## What it does

Every time the pipeline runs it:
1. Fetches live crypto prices from the CoinGecko API
2. Scrapes the latest news headlines from CoinDesk RSS
3. Loads and processes historical price data from CSV files
4. Cleans and transforms all data
5. Stores everything in a SQLite database
6. Serves it all on a live dashboard with auto-refresh

---

## Architecture

```
Data Sources           Ingest               Transform          Store
────────────           ──────               ─────────          ─────
CoinGecko API    →   api_ingest.py    →   clean_api()    →   prices_live
CSV (Kaggle)     →   csv_ingest.py    →   clean_csv()    →   prices_history
CoinDesk RSS     →   scraper.py       →   to_dataframe() →   news
                                                               ↓
                                                         marketpulse.db
                                                               ↓
                                                         dashboard/
                                                         server.py + index.html
```

---

## Project Structure

```
marketpulse_pipeline/
├── ingest/
│   ├── api_ingest.py      # Fetches live prices from CoinGecko API
│   ├── csv_ingest.py      # Loads 3 historical CSV files, stacks into one DataFrame
│   └── scraper.py         # Scrapes CoinDesk RSS feed for news headlines
├── transform/
│   └── clean.py           # Fixes data quality issues across all sources
├── store/
│   └── db.py              # SQLite schema, inserts, idempotent writes
├── dashboard/
│   ├── index.html         # Live dashboard — price cards, chart, news
│   └── server.py          # HTTP server with JSON API endpoints
├── data/
│   ├── coin_Bitcoin.csv   # Historical daily prices 2013-2021
│   ├── coin_Ethereum.csv  # Historical daily prices 2015-2021
│   └── coin_Solana.csv    # Historical daily prices 2020-2021
├── start.sh               # Railway startup — runs pipeline then server
├── run_pipeline.py        # Master controller — orchestrates all steps
└── requirements.txt
```

---

## Three Data Sources

### 1. Public API — CoinGecko
Fetches live BTC, ETH, SOL prices including market cap, 24h volume, and 24h price change. Uses Python `requests` library. Handles rate limits and network errors with try/except.

### 2. CSV Files — Kaggle Historical Data
Three CSV files with daily OHLCV data from 2013 to 2021. Loaded with pandas, stacked into one unified DataFrame, and cleaned before storing.

### 3. Web Scraping — CoinDesk RSS
Parses the CoinDesk RSS feed using Python's built-in `xml.etree.ElementTree`. Extracts headlines, authors, publish dates, and article links. Flags articles as crypto-relevant based on keyword matching.

---

## Data Quality

Every raw data source had problems that needed fixing before storing:

| Problem | Source | Fix |
|---|---|---|
| Date stored as string | CSV | Converted to datetime64 with pd.to_datetime() |
| 242 zero-volume rows | CSV | Replaced with NaN — honest representation of missing data |
| Redundant columns (SNo, Name, Symbol) | CSV | Dropped — reduced from 11 to 8 columns |
| Nested JSON structure | API | Flattened into rows, one per coin |
| Duplicate rows on re-run | All | UNIQUE constraints + INSERT OR IGNORE |

---

## Database

**prices_history** — 5,603 rows of daily closing prices (2013–2021)
```
coin | date | open | high | low | close | volume | marketcap
```

**prices_live** — live price snapshots, grows with every pipeline run
```
coin | price | market_cap | volume_24h | change_24h | fetched_at
```

**news** — scraped headlines
```
title | link | published | authors | categories | is_relevant | scraped_at
```

---

## Key Engineering Concepts

**Idempotency** — the pipeline can re-run any number of times without creating duplicate data. UNIQUE constraints on `coin+date` and article `link` ensure every run is safe.

**Separation of concerns** — each module has one job. Ingest fetches, transform cleans, store writes, serve reads. Changing one module never breaks another.

**Defensive programming** — every API call is wrapped in try/except. Every field uses `.get()` with a default. The pipeline never crashes silently.

**Raw store pattern** — raw JSON and scraped data are saved to disk before transformation. If transform logic has a bug, data can be reprocessed without hitting the API again.

---

## How to Run Locally

```bash
# Install dependencies
pip install requests pandas beautifulsoup4

# Run the pipeline
python run_pipeline.py

# Start the dashboard
python dashboard/server.py
# Open http://localhost:8081
```

---

## Deployment

Deployed on **Railway** — pipeline runs on startup, dashboard serves live data.

To deploy your own copy:
1. Fork this repo
2. Connect to Railway
3. Set start command: `bash start.sh`
4. Railway auto-deploys on every push

---

## Data Sources

| Source | Type | Data |
|---|---|---|
| [CoinGecko API](https://www.coingecko.com/en/api) | REST API | Live prices, market cap, 24h change |
| [Kaggle](https://www.kaggle.com/datasets/sudalairajkumar/cryptocurrencypricehistory) | CSV | Daily OHLCV 2013–2021 |
| [CoinDesk RSS](https://www.coindesk.com/arc/outboundfeeds/rss/) | RSS/XML | Latest crypto news |

---

Built with Python 3.11 · pandas · SQLite · Chart.js · Railway