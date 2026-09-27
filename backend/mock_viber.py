"""Minimal mock of the Viber Public Account REST API for local smoke testing.

Runs a tiny HTTP server (default port 9000) that answers any `/pa` POST with a
success envelope. It returns a unique `message_token` per call because the real
API requires unique tokens and the `messages.channel_message_id` column is
unique.

Usage:
    python mock_viber.py [port]
    # then start the backend with:
    #   VIBER_API_BASE_URL=http://localhost:9000/pa uvicorn app.main:app --port 8000
"""

import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockViberHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        body = json.dumps(
            {
                "status": 0,
                "status_message": "ok",
                "chat_hostname": "mock",
                "message_token": str(uuid.uuid4()),
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silence per-request logging
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    print(f"Mock Viber API listening on http://0.0.0.0:{port}/pa")
    HTTPServer(("0.0.0.0", port), MockViberHandler).serve_forever()


if __name__ == "__main__":
    main()