from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

HOST = "0.0.0.0"
PORT = 5000
BASE_DIR = Path(__file__).parent

TRADINGVIEW_PAGE = "https://www.tradingview.com/symbols/BTCUSD/"


def extract_price_from_html(html: str) -> float | None:
    patterns = [
        r'"last_price"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return float(match.group(1))
    return None


def fetch_btc_price() -> tuple[float, str]:
    req = Request(
        TRADINGVIEW_PAGE,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )

    try:
        with urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
        price = extract_price_from_html(html)
        if price is None:
            raise RuntimeError("Unable to parse BTC price from TradingView HTML")
        return price, TRADINGVIEW_PAGE
    except (URLError, RuntimeError, TimeoutError):
        snapshot = (BASE_DIR / "data" / "tradingview_snapshot.html").read_text(
            encoding="utf-8"
        )
        price = extract_price_from_html(snapshot)
        if price is None:
            raise RuntimeError("No BTC price available from TradingView or local snapshot")
        return price, "local TradingView snapshot fallback"


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._serve_file(BASE_DIR / "templates" / "index.html", "text/html; charset=utf-8")
            return

        if self.path.startswith("/static/"):
            file_path = BASE_DIR / self.path.lstrip("/")
            mime = "text/plain"
            if file_path.suffix == ".css":
                mime = "text/css"
            elif file_path.suffix == ".js":
                mime = "application/javascript"
            self._serve_file(file_path, mime)
            return

        if self.path == "/api/bitcoin-price":
            try:
                price, source = fetch_btc_price()
                payload = {
                    "symbol": "BTCUSD",
                    "price": price,
                    "currency": "USD",
                    "source": source,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._send_json(payload)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        return

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists() or not path.is_file():
            self.send_error(404, "File not found")
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, status: int = 200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), DashboardHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    server.serve_forever()
