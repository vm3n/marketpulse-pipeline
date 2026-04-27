from http.server import HTTPServer, SimpleHTTPRequestHandler
import sqlite3
import json
import os
import sys

# Add project root to path so we can import from store/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from store.db import query

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'marketpulse.db')

class DashboardHandler(SimpleHTTPRequestHandler):
    """
    WHY a custom handler?
    The default SimpleHTTPRequestHandler only serves
    static files. We extend it to also handle /api/
    routes that return live data from SQLite.
    """

    def do_GET(self):

        # ── API routes — return JSON from SQLite ──
        if self.path == '/api/live':
            self.serve_json(self.get_live())

        elif self.path == '/api/history':
            self.serve_json(self.get_history())

        elif self.path == '/api/news':
            self.serve_json(self.get_news())

        else:
            # Serve static files (index.html etc.)
            # Change directory to dashboard/ so HTML is found
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            super().do_GET()

    def serve_json(self, data):
        """Send data back as JSON with correct headers."""
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def get_live(self):
        """Latest price snapshot per coin."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT coin, price, change_24h, fetched_at
            FROM prices_live
            GROUP BY coin
            HAVING fetched_at = MAX(fetched_at)
            ORDER BY coin
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {'coin': r[0], 'price': r[1],
             'change_24h': r[2], 'fetched_at': r[3]}
            for r in rows
        ]

    def get_history(self):
        """Last 365 days of closing prices per coin."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT coin, date, close
            FROM prices_history
            ORDER BY coin, date
        """)
        rows = cursor.fetchall()
        conn.close()
        # Group by coin for the chart
        result = {}
        for coin, date, close in rows:
            if coin not in result:
                result[coin] = {'dates': [], 'prices': []}
            result[coin]['dates'].append(date[:10])
            result[coin]['prices'].append(close)
        return result

    def get_news(self):
        """Latest 10 relevant news articles."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, link, published, authors
            FROM news
            WHERE is_relevant = 1
            ORDER BY published DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {'title': r[0], 'link': r[1],
             'published': r[2], 'authors': r[3]}
            for r in rows
        ]

    def log_message(self, format, *args):
        """Suppress default request logging — keeps terminal clean."""
        pass


if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 8081))
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"[DASHBOARD] Server running at http://localhost:{port}")
    print(f"[DASHBOARD] Open that URL in your browser")
    print(f"[DASHBOARD] Press Ctrl+C to stop")
    HTTPServer(('', port), DashboardHandler).serve_forever()
