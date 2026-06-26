#!/usr/bin/env python3
"""
captive_server.py — minimal captive-portal responder.

Problem: when a phone joins WiFi it runs an "is there internet?" check by
fetching a known URL. On the Sahar-Connect hotspot with the uplink unplugged,
that check fails, so iOS (especially) marks the network "No Internet" and may
auto-disconnect mid-demo.

Fix: answer those checks with the success response each OS expects, so the
device believes the network is fine and stays connected. Pair this with
deploy/dnsmasq-captive.conf, which points the OS check domains at this Pi
(10.42.0.1). Runs on port 80 (see deploy/sahar-captive.service).

Stdlib only — no dependencies.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APPLE_SUCCESS = b"<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="text/html"):
        self.send_response(code)
        if body:
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.lower()
        if "generate_204" in path or "gen_204" in path:
            self._send(204)                                   # Android / Chrome
        elif "connecttest" in path or "ncsi" in path:
            self._send(200, b"Microsoft Connect Test", "text/plain")  # Windows
        else:
            self._send(200, APPLE_SUCCESS)                    # Apple + catch-all

    def log_message(self, *args):  # keep the journal quiet
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
