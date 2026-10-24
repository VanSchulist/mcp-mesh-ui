"""
Command Line Interface for mcp-mesh-ui.
Subcommands: web, tui, status, simulate, export.
Zero external dependencies.
"""

from __future__ import annotations

import sys
import os
import argparse
import webbrowser
import json
import csv
from pathlib import Path

from .core import MeshTelemetryStore
from .tui import render_dashboard, run_tui_loop
from .web_server import run_server

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-mesh-ui",
        description="mcp-mesh-ui: Real-time Topology Visualizer & Observability Dashboard for mcp-mesh."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: web
    p_web = subparsers.add_parser("web", help="Launch the local web dashboard")
    p_web.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    p_web.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    p_web.add_argument("--no-open", action="store_true", help="Do not automatically open browser")
    p_web.add_argument("--db", default=None, help="Custom path to telemetry.db")

    # Command: tui
    p_tui = subparsers.add_parser("tui", help="Launch live-refreshing terminal ANSI dashboard")
    p_tui.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds (default: 2.0)")
    p_tui.add_argument("--db", default=None, help="Custom path to telemetry.db")

    # Command: status
    p_status = subparsers.add_parser("status", help="Print one-shot status diagnostic")
    p_status.add_argument("--db", default=None, help="Custom path to telemetry.db")
    p_status.add_argument("--json", action="store_true", help="Output raw JSON")

    # Command: simulate
    p_sim = subparsers.add_parser("simulate", help="Inject synthetic traffic for testing and live demonstration")
    p_sim.add_argument("--calls", type=int, default=30, help="Number of simulated calls (default: 30)")
    p_sim.add_argument("--db", default=None, help="Custom path to telemetry.db")

    # Command: export
    p_exp = subparsers.add_parser("export", help="Export telemetry logs to JSON or CSV file")
    p_exp.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    p_exp.add_argument("--output", required=True, help="Output destination file path")
    p_exp.add_argument("--db", default=None, help="Custom path to telemetry.db")

    args = parser.parse_args()

    if not args.command or args.command == "status":
        db_path = getattr(args, "db", None)
        store = MeshTelemetryStore(db_path=db_path)
        if getattr(args, "json", False):
            summary = store.get_summary()
            print(json.dumps(summary.__dict__, indent=2))
        else:
            print(render_dashboard(store))
        return

    if args.command == "web":
        url = f"http://{args.host}:{args.port}"
        print(f"\n[*] Starting mcp-mesh-ui Web Dashboard on {url}")
        print("[*] Press Ctrl+C to terminate server.\n")
        
        server = run_server(port=args.port, host=args.host, db_path=args.db)
        if not args.no_open:
            try:
                webbrowser.open(url)
            except Exception:
                pass

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[+] mcp-mesh-ui Web Server stopped.")
            server.server_close()

    elif args.command == "tui":
        store = MeshTelemetryStore(db_path=args.db)
        run_tui_loop(store, interval=args.interval)

    elif args.command == "simulate":
        store = MeshTelemetryStore(db_path=args.db)
        count = store.simulate_traffic(num_calls=args.calls)
        print(f"[+] Successfully injected {count} simulated tool calls into {store.db_path}")

    elif args.command == "export":
        store = MeshTelemetryStore(db_path=args.db)
        calls = store.get_recent_calls(limit=10000)
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if args.format == "json":
            out_p.write_text(json.dumps(calls, indent=2), encoding="utf-8")
        else:
            if calls:
                with open(out_p, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=calls[0].keys())
                    writer.writeheader()
                    writer.writerows(calls)
            else:
                out_p.write_text("", encoding="utf-8")

        print(f"[+] Exported {len(calls)} records to {out_p.resolve()}")


if __name__ == "__main__":
    main()
