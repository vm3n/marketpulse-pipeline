# MarketPulse Pipeline 📈

A production-structured data pipeline that tracks Bitcoin, Ethereum, and Solana
across live prices, 8 years of historical data, and real-time news headlines.

Built to demonstrate end-to-end data engineering skills — ingestion, transformation,
storage, orchestration, and serving.

---

## What it does

Every hour, automatically:
1. Fetches live crypto prices from the CoinGecko API
2. Scrapes the latest news headlines from CoinDesk RSS
3. Cleans and transforms all data
4. Stores everything in a SQLite database
5. Serves a live dashboard at localhost:8081

---

## Architecture

```
Data Sources          Ingest              Transform           Store               Serve
────────────          ──────              ─────────           ─────               ─────
CoinGecko API    →  api_ingest.py   →   clean_api()    →   prices_live    →   dashboard
CSV (Kaggle)     →  csv_ingest.py   →   clean_csv()    →   prices_history     (Chart.js)
CoinDesk RSS     →  scraper.py      →   to_dataframe() →   news
                                                                ↑
                                                        marketpulse.db
                                                          (SQLite)
```

Orchestrated by `run_pipeline.py` — one command runs the entire pipeline.
Scheduled via cron to run every hour automatically.

---

## Skills demonstrated

| Skill | How it's used |
|---|---|
| REST API ingestion | CoinGecko API with error handling, rate limit awareness |
| CSV processing | Loading and unifying 3 historical datasets (5,603 rows) |
| Web scraping | CoinDesk RSS parsed with Python's built-in XML parser |
| Data cleaning | Type conversion, NaN handling, deduplication, normalization |
| SQL & SQLite | Schema design, UNIQUE constraints, INSERT OR IGNORE |
| Idempotency | Pipeline safe to re-run — never creates duplicate rows |
| Orchestration | cron scheduler with full logging to logs/pipeline.log |
| Python best practices | Separation of concerns, defensive programming, modular design |
| Data serving | Lightweight HTTP server with JSON API endpoints |
| Visualization | Chart.js dashboard with live price cards and history charts |

---

## Project structure

```
marketpulse_pipeline/
├── ingest/
│   ├── api_ingest.py      # Fetches live prices from CoinGecko API
│   ├── csv_ingest.py      # Loads historical CSV data for 3 coins
│   └── scraper.py         # Scrapes news headlines from CoinDesk RSS
├── transform/
│   └── clean.py           # Cleans and normalizes all data sources
├── store/
│   └── db.py              # SQLite schema, inserts, queries
├── dashboard/
│   ├── index.html         # Live dashboard (Chart.js)
│   └── server.py          # Lightweight HTTP + JSON API server
├── data/                  # Raw JSON snapshots + SQLite database
├── logs/                  # Pipeline run logs
├── run_pipeline.py        # Master controller — runs the full pipeline
└── requirements.txt       # Python dependencies
```

---

## Database schema

**prices_history** — 5,603 rows of daily OHLCV data (2013–2021)
```sql
coin | date | open | high | low | close | volume | marketcap
```

**prices_live** — live price snapshots, one row per coin per pipeline run
```sql
coin | price | market_cap | volume_24h | change_24h | fetched_at
```

**news** — scraped headlines with relevance flagging
```sql
title | link | published | description | authors | categories | is_relevant | scraped_at
```

---

## Data quality decisions

| Problem found | Fix applied |
|---|---|
| Date column stored as string | Converted to datetime64 with pd.to_datetime() |
| 242 zero-volume rows in Bitcoin CSV | Replaced with NaN — honest representation of missing data |
| Redundant columns (SNo, Name, Symbol) | Dropped — reduced from 11 to 8 columns |
| Nested JSON from API | Flattened into rows with coin as a column |
| Duplicate rows on pipeline re-run | UNIQUE constraints + INSERT OR IGNORE |

---

## How to run

**Install dependencies:**
```bash
pip install requests pandas beautifulsoup4
```

**Run the pipeline once:**
```bash
python run_pipeline.py
```

**Start the dashboard:**
```bash
python dashboard/server.py
# Open http://localhost:8081
```

**Schedule to run every hour (cron):**
```bash
crontab -e
# Add this line:
0 * * * * cd /path/to/marketpulse_pipeline && python run_pipeline.py >> logs/pipeline.log 2>&1
```

---

## Data sources

| Source | Type | What it provides |
|---|---|---|
| [CoinGecko API](https://www.coingecko.com/en/api) | REST API | Live prices, market cap, 24h volume and change |
| [Kaggle — Crypto History](https://www.kaggle.com/datasets/sudalairajkumar/cryptocurrencypricehistory) | CSV | Daily OHLCV data from 2013–2021 |
| [CoinDesk RSS](https://www.coindesk.com/arc/outboundfeeds/rss/) | RSS/XML | Latest crypto news headlines |

---

## Key concepts learned

**Idempotency** — the pipeline can be re-run any number of times without
creating duplicate data. UNIQUE constraints on coin+date and article URL
ensure every run is safe.

**Separation of concerns** — each module has one job. Ingest fetches,
transform cleans, store writes, serve reads. If the API changes, only
api_ingest.py needs to change.

**Defensive programming** — every network call is wrapped in try/except.
Every field access uses .get() with a default. The pipeline never crashes
silently.

**Raw store pattern** — raw API responses and scraped data are saved to
disk before transformation. If transform logic has a bug, data can be
re-processed without hitting the API again.

---

Built with Python 3.11 · pandas · SQLite · Chart.js · cron