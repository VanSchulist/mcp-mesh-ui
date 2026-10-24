"""
Terminal User Interface (TUI) & Live ANSI Console Dashboard.
Zero external dependencies.
"""

from __future__ import annotations

import sys
import time
from typing import Optional
from pathlib import Path

from .core import MeshTelemetryStore, TelemetrySummary

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"


def render_dashboard(store: MeshTelemetryStore) -> str:
    summary = store.get_summary()
    servers = store.get_server_stats()
    recent = store.get_recent_calls(limit=8)

    lines = []
    lines.append(f"{CYAN}{BOLD}=============================================================================={RESET}")
    lines.append(f"  {MAGENTA}{BOLD}[*] MCP-MESH REAL-TIME OBSERVABILITY DASHBOARD  v1.0.0{RESET}")
    lines.append(f"  {DIM}Satellite 2 | Curated by Van Schulist (@VanSchulist) | Existential Cloud{RESET}")
    lines.append(f"{CYAN}=============================================================================={RESET}")

    # Section 1: Token Economy & Latency
    lines.append(f"\n{BOLD}[1] TOKEN ECONOMY & AGENT LATENCY METRICS:{RESET}")
    lines.append(f"  Turn-0 Tokens Saved : {GREEN}{BOLD}{summary.total_tokens_saved:,}{RESET} ({summary.overall_savings_pct}% static reduction)")
    lines.append(f"  Est. Cost Reduction : {YELLOW}${summary.estimated_cost_saved_usd:.4f} USD{RESET} (Blended frontier pricing)")
    lines.append(f"  Total Invocations   : {WHITE}{summary.total_calls:,}{RESET} ({GREEN}{summary.success_rate}% Success{RESET})")
    lines.append(f"  Latency Profile     : p50={summary.p50_latency_ms}ms | p95={summary.p95_latency_ms}ms | avg={summary.avg_latency_ms}ms")
    lines.append(f"  Cache Efficiency    : {summary.cache_hit_rate}% LRU schema hits")

    # Section 2: Upstream Servers Grid
    lines.append(f"\n{BOLD}[2] UPSTREAM MCP SERVERS STATUS ({len(servers)} Connected):{RESET}")
    if not servers:
        lines.append(f"  {DIM}No upstream servers logged yet.{RESET}")
    else:
        lines.append(f"  {BOLD}{'SERVER ID':<20} {'CALLS':<10} {'AVG LATENCY':<14} {'TOKENS SAVED':<16} {'STATUS'}{RESET}")
        lines.append(f"  {'-'*68}")
        for s in servers:
            st_color = GREEN if s["status"] == "HEALTHY" else RED
            lines.append(
                f"  {s['server_id']:<20} {s['total_calls']:<10} {s['avg_latency_ms']:<14.2f} "
                f"+{s['tokens_saved']:<15} {st_color}{s['status']}{RESET}"
            )

    # Section 3: Recent Tool Invocations Waterfall
    lines.append(f"\n{BOLD}[3] REAL-TIME INVOCATIONS WATERFALL:{RESET}")
    if not recent:
        lines.append(f"  {DIM}No tool invocations recorded yet. Run an agent or simulate traffic.{RESET}")
    else:
        lines.append(f"  {BOLD}{'TIMESTAMP':<12} {'SERVER':<16} {'TOOL NAME':<24} {'LATENCY':<10} {'STATUS'}{RESET}")
        lines.append(f"  {'-'*68}")
        for c in recent:
            ts = c["timestamp"].split("T")[1][:8] if "T" in c["timestamp"] else c["timestamp"][:8]
            st = f"{GREEN}OK{RESET}" if c["success"] else f"{RED}ERR{RESET}"
            lines.append(f"  {ts:<12} {c['server_id']:<16} {c['tool_name']:<24} {c['latency_ms']:<10.1f} {st}")

    lines.append(f"\n{CYAN}=============================================================================={RESET}")
    return "\n".join(lines)


def run_tui_loop(store: MeshTelemetryStore, interval: float = 2.0) -> None:
    """Runs continuous live-refreshing TUI in the terminal."""
    try:
        while True:
            # Clear screen ANSI escape
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(render_dashboard(store) + "\n")
            sys.stdout.write(f"{DIM}Press Ctrl+C to exit... (Refreshing every {interval}s){RESET}\n")
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        sys.stdout.write(f"\n{GREEN}[+] Exited mcp-mesh-ui terminal monitor.{RESET}\n")
