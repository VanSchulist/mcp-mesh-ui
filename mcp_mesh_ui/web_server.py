"""
Lightweight Web Server & API Gateway for mcp-mesh-ui.
Zero external dependencies (uses standard library http.server, socketserver, json).
"""

from __future__ import annotations

import os
import sys
import json
import time
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional

from .core import MeshTelemetryStore


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP Server handling concurrent REST and SSE connections."""
    daemon_threads = True
    allow_reuse_address = True


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """Handles REST API requests, SSE telemetry streaming, and static assets."""

    store: MeshTelemetryStore = MeshTelemetryStore()
    static_dir: Path = Path(__file__).parent / "static"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ["/", "/index.html"]:
            self._serve_file(self.static_dir / "index.html", "text/html")
        elif path.startswith("/static/"):
            filename = path.replace("/static/", "")
            file_path = self.static_dir / filename
            mime = "text/css" if filename.endswith(".css") else "application/javascript" if filename.endswith(".js") else "text/plain"
            self._serve_file(file_path, mime)
        elif path == "/api/stats":
            summary = self.store.get_summary()
            self._send_json(summary.__dict__)
        elif path == "/api/calls":
            limit = int(query.get("limit", [50])[0])
            search = query.get("search", [None])[0]
            server_id = query.get("server_id", [None])[0]
            calls = self.store.get_recent_calls(limit=limit, search=search, server_id=server_id)
            self._send_json(calls)
        elif path == "/api/topology":
            topology = self.store.get_topology_graph()
            self._send_json(topology)
        elif path == "/api/servers":
            servers = self.store.get_server_stats()
            self._send_json(servers)
        elif path == "/api/stream":
            self._handle_sse_stream()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/simulate":
            count = self.store.simulate_traffic(num_calls=25)
            self._send_json({"status": "ok", "generated_calls": count})
        else:
            self.send_error(404, "Not Found")

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.exists():
            self.send_error(404, "File Not Found")
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: any) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_sse_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            for _ in range(60):  # Stream heartbeat for 60 iterations (1 min)
                payload = json.dumps({"type": "update", "timestamp": time.time()})
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format: str, *args: any) -> None:
        # Silence routine static request logging to keep console clean
        if "/static/" not in args[0]:
            sys.stderr.write(f"[mcp-mesh-ui] {args[0]} - {args[1]}\n")


def run_server(
    port: int = 8765,
    host: str = "127.0.0.1",
    db_path: Optional[str] = None
) -> ThreadedHTTPServer:
    """Starts the mcp-mesh-ui Web Dashboard HTTP server."""
    DashboardRequestHandler.store = MeshTelemetryStore(db_path=db_path)
    server = ThreadedHTTPServer((host, port), DashboardRequestHandler)
    return server
