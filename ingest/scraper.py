import requests
import xml.etree.ElementTree as ET
import pandas as pd
import os
import json
from datetime import datetime

RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"

# ─────────────────────────────────────────
# WHY xml.etree.ElementTree and not BeautifulSoup?
# RSS is valid XML — Python has a built-in XML
# parser. No extra library needed.
# BeautifulSoup is better for messy HTML.
# For clean XML, the built-in is faster and simpler.
# ─────────────────────────────────────────

# RSS feeds use XML namespaces — these are prefixes
# that tell you which "vocabulary" a tag belongs to.
# <dc:creator> means "creator from the dc vocabulary"
# We define them here so we can find those tags.
NAMESPACES = {
    'dc':      'http://purl.org/dc/elements/1.1/',
    'media':   'http://search.yahoo.com/mrss/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
}

# Keywords to flag crypto-relevant articles
CRYPTO_KEYWORDS = [
    'bitcoin', 'ethereum', 'solana', 'btc', 'eth',
    'sol', 'crypto', 'blockchain', 'defi', 'nft',
    'altcoin', 'coinbase', 'binance'
]


def fetch_news(max_articles=50):
    """
    Fetches RSS feed and parses each <item> into
    a clean dictionary. Returns a list of dicts.
    """
    print(f"[SCRAPER] Fetching news from CoinDesk RSS...")

    # ─────────────────────────────────────────
    # WHY a User-Agent header?
    # Some servers block requests with no User-Agent
    # because only bots do that. Adding a browser-like
    # User-Agent makes our request look more normal.
    # ─────────────────────────────────────────
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[SCRAPER] ERROR: {e}")
        return None

    # ─────────────────────────────────────────
    # WHAT IS ET.fromstring()?
    # Takes the raw XML text and builds a tree
    # structure in memory you can navigate.
    # Like a family tree — root has children,
    # children have children, etc.
    #
    # Structure of RSS XML tree:
    # <rss>               ← root
    #   <channel>         ← root[0]
    #     <title>         ← channel child
    #     <item>          ← what we want
    #     <item>
    #     ...
    # ─────────────────────────────────────────
    root = ET.fromstring(response.text)
    channel = root.find('channel')
    items = channel.findall('item')

    print(f"[SCRAPER] Found {len(items)} articles — parsing...")

    articles = []

    for item in items[:max_articles]:

        # ─────────────────────────────────────
        # WHY the 'or ""' pattern?
        # .find() returns None if tag doesn't exist.
        # .text returns None if tag is empty.
        # 'or ""' converts None to empty string
        # so we never crash on missing fields.
        # ─────────────────────────────────────
        title = (item.findtext('title') or '').strip()
        link  = (item.findtext('link')  or '').strip()
        date  = (item.findtext('pubDate') or '').strip()
        desc  = (item.findtext('description') or '').strip()

        # dc:creator needs namespace to find
        creator_els = item.findall('dc:creator', NAMESPACES)
        authors = ', '.join(
            el.text.strip() for el in creator_els if el.text
        )

        # categories — collect all of them
        categories = [
            el.text.strip()
            for el in item.findall('category')
            if el.text
        ]

        # ─────────────────────────────────────
        # WHY flag crypto-relevant articles?
        # Not every CoinDesk article is about
        # BTC/ETH/SOL specifically. We tag the ones
        # that mention our coins so we can filter later.
        # This is called enrichment — adding derived
        # information to the raw data.
        # ─────────────────────────────────────
        title_lower = title.lower()
        desc_lower  = desc.lower()
        is_relevant = any(
            kw in title_lower or kw in desc_lower
            for kw in CRYPTO_KEYWORDS
        )

        articles.append({
            'title':       title,
            'link':        link,
            'published':   date,
            'description': desc,
            'authors':     authors,
            'categories':  ', '.join(categories),
            'is_relevant': is_relevant,
            'scraped_at':  datetime.utcnow().isoformat(),
        })

    print(f"[SCRAPER] Parsed {len(articles)} articles")
    relevant = sum(1 for a in articles if a['is_relevant'])
    print(f"[SCRAPER] {relevant} flagged as crypto-relevant")

    return articles


def save_raw(articles):
    """
    Save raw scraped articles as JSON.
    Same pattern as api_ingest — always save raw
    before transforming. If our parsing logic has
    a bug we can re-parse without re-scraping.
    """
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"data/raw_news_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump(articles, f, indent=2)

    print(f"[SCRAPER] Raw news saved to {filename}")
    return filename


def to_dataframe(articles):
    """
    Convert list of article dicts to a DataFrame.
    Same pattern as clean_api — list of dicts
    where keys become column names.
    """
    df = pd.DataFrame(articles)

    # Convert published date string to datetime
    df['published'] = pd.to_datetime(df['published'], errors='coerce')
    df['scraped_at'] = pd.to_datetime(df['scraped_at'])

    return df


if __name__ == "__main__":
    articles = fetch_news()

    if articles:
        save_raw(articles)
        df = to_dataframe(articles)

        print("\n─── SAMPLE HEADLINES ────────────────────")
        for _, row in df.head(5).iterrows():
            flag = "✓" if row['is_relevant'] else " "
            print(f"[{flag}] {row['title'][:70]}")

        print(f"\n─── RELEVANT ONLY ───────────────────────")
        relevant_df = df[df['is_relevant'] == True]
        for _, row in relevant_df.head(5).iterrows():
            print(f"• {row['title'][:70]}")
            print(f"  {row['authors']} — {row['published']}")
