from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'marketpulse.db')
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))

class DashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split('?')[0]  # strip query params

        if path == '/api/live':
            self.serve_json(self.get_live())
        elif path == '/api/history':
            self.serve_json(self.get_history())
        elif path == '/api/news':
            self.serve_json(self.get_news())
        elif path == '/' or path == '/index.html':
            self.serve_file('index.html', 'text/html')
        else:
            self.send_error(404)

    def serve_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, filename, content_type):
        filepath = os.path.join(DASHBOARD_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def get_live(self):
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
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT coin, date, close
            FROM prices_history
            ORDER BY coin, date
        """)
        history_rows = cursor.fetchall()
        cursor.execute("""
            SELECT coin,
                   DATE(fetched_at) as date,
                   AVG(price) as close
            FROM prices_live
            GROUP BY coin, DATE(fetched_at)
            ORDER BY coin, date
        """)
        live_rows = cursor.fetchall()
        conn.close()

        result = {}
        for coin, date, close in history_rows:
            if coin not in result:
                result[coin] = {'dates': [], 'prices': []}
            if close is not None:
                result[coin]['dates'].append(str(date)[:10])
                result[coin]['prices'].append(close)

        for coin, date, close in live_rows:
            if coin not in result:
                result[coin] = {'dates': [], 'prices': []}
            if close is not None:
                result[coin]['dates'].append(str(date)[:10])
                result[coin]['prices'].append(round(close, 2))

        return result

    def get_news(self):
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
        pass


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8081))
    print(f"[DASHBOARD] Server running at http://localhost:{port}")
    print(f"[DASHBOARD] DB path: {DB_PATH}")
    print(f"[DASHBOARD] Dashboard dir: {DASHBOARD_DIR}")
    HTTPServer(('', port), DashboardHandler).serve_forever()
