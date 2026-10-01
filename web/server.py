#!/usr/bin/env python3
"""
server.py - Simple local HTTP server for Calligraphy Font Studio demo webpage.
"""
import sys
import http.server
import socketserver
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for font files
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

def run(port=8088):
    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        print(f"============================================================")
        print(f"  Calligraphy Font Studio Running at: http://localhost:{port}")
        print(f"  Press Ctrl+C to stop.")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    run(port)
