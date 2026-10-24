"""
Core Data Models, Telemetry Reader, and Graph Aggregator for mcp-mesh-ui.
Zero external dependencies (uses standard library sqlite3, json, dataclasses).
"""

from __future__ import annotations

import os
import json
import sqlite3
import random
import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class CallRecord:
    id: int
    timestamp: str
    session_id: str
    caller: str
    server_id: str
    tool_name: str
    latency_ms: float
    success: bool
    cache_hit: bool
    tokens_baseline: int
    tokens_mesh: int
    tokens_saved: int
    error_message: Optional[str] = None


@dataclass
class TelemetrySummary:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 100.0
    total_tokens_saved: int = 0
    total_tokens_baseline: int = 0
    total_tokens_mesh: int = 0
    overall_savings_pct: float = 0.0
    estimated_cost_saved_usd: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0
    active_servers_count: int = 0
    active_tools_count: int = 0


@dataclass
class ServerStat:
    server_id: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    tokens_saved: int
    avg_latency_ms: float
    status: str = "HEALTHY"


@dataclass
class TopologyNode:
    id: str
    name: str
    group: str  # "gateway" | "server" | "tool"
    call_count: int = 0
    tokens_saved: int = 0
    status: str = "active"


@dataclass
class TopologyLink:
    source: str
    target: str
    weight: int = 1
    type: str = "hierarchy"  # "hierarchy" | "cooccurrence"


class MeshTelemetryStore:
    """
    Interfaces directly with the mcp-mesh SQLite telemetry ledger (~/.mcp-mesh/telemetry.db).
    Provides structured querying, aggregations, and topology mapping.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is None:
            home = Path.home()
            self.db_path = home / ".mcp-mesh" / "telemetry.db"
        else:
            self.db_path = Path(db_path)
            
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        return conn

    def _ensure_schema(self) -> None:
        """Ensures tables exist so queries never fail even on fresh installs."""
        conn = self._get_connection()
        try:
            with conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        started_at TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        server_count INTEGER DEFAULT 0,
                        tool_count INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        session_id TEXT,
                        caller TEXT DEFAULT 'agent',
                        server_id TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        latency_ms REAL NOT NULL,
                        success INTEGER NOT NULL,
                        cache_hit INTEGER DEFAULT 0,
                        tokens_baseline INTEGER DEFAULT 0,
                        tokens_mesh INTEGER DEFAULT 0,
                        tokens_saved INTEGER DEFAULT 0,
                        error_message TEXT
                    );

                    CREATE TABLE IF NOT EXISTS tool_cooccurrence (
                        tool_a TEXT NOT NULL,
                        tool_b TEXT NOT NULL,
                        count INTEGER DEFAULT 1,
                        last_seen TEXT NOT NULL,
                        PRIMARY KEY (tool_a, tool_b)
                    );
                    """
                )
        finally:
            conn.close()

    def get_summary(self) -> TelemetrySummary:
        """Computes comprehensive telemetry metrics across all logged sessions."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                    SUM(tokens_saved) as total_tokens_saved,
                    SUM(tokens_baseline) as total_tokens_baseline,
                    SUM(tokens_mesh) as total_tokens_mesh,
                    AVG(latency_ms) as avg_latency_ms,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits,
                    COUNT(DISTINCT server_id) as active_servers_count,
                    COUNT(DISTINCT tool_name) as active_tools_count
                FROM calls
                """
            )
            row = cur.fetchone()

            total_calls = row["total_calls"] or 0
            if total_calls == 0:
                return TelemetrySummary()

            successful = row["successful_calls"] or 0
            failed = row["failed_calls"] or 0
            tokens_saved = row["total_tokens_saved"] or 0
            tokens_baseline = row["total_tokens_baseline"] or 0
            tokens_mesh = row["total_tokens_mesh"] or 0
            avg_latency = row["avg_latency_ms"] or 0.0
            cache_hits = row["cache_hits"] or 0
            active_servers = row["active_servers_count"] or 0
            active_tools = row["active_tools_count"] or 0

            # Calculate percentiles for latency
            cur.execute("SELECT latency_ms FROM calls ORDER BY latency_ms ASC")
            latencies = [r[0] for r in cur.fetchall()]

            p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
            p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
            p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0

            success_rate = (successful / total_calls * 100.0) if total_calls else 100.0
            savings_pct = (tokens_saved / tokens_baseline * 100.0) if tokens_baseline else 0.0
            # Standard estimated blended frontier model pricing: $3.00 / 1M tokens ($0.000003 per token)
            cost_saved_usd = tokens_saved * 0.000003
            cache_hit_rate = (cache_hits / total_calls * 100.0) if total_calls else 0.0

            return TelemetrySummary(
                total_calls=total_calls,
                successful_calls=successful,
                failed_calls=failed,
                success_rate=round(success_rate, 1),
                total_tokens_saved=tokens_saved,
                total_tokens_baseline=tokens_baseline,
                total_tokens_mesh=tokens_mesh,
                overall_savings_pct=round(savings_pct, 1),
                estimated_cost_saved_usd=round(cost_saved_usd, 4),
                avg_latency_ms=round(avg_latency, 2),
                p50_latency_ms=round(p50, 2),
                p95_latency_ms=round(p95, 2),
                p99_latency_ms=round(p99, 2),
                cache_hit_rate=round(cache_hit_rate, 1),
                active_servers_count=active_servers,
                active_tools_count=active_tools
            )
        finally:
            conn.close()

    def get_recent_calls(
        self,
        limit: int = 50,
        offset: int = 0,
        server_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves paginated and filtered list of recent tool calls."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT * FROM calls WHERE 1=1"
            params: List[Any] = []

            if server_id:
                query += " AND server_id = ?"
                params.append(server_id)
            if tool_name:
                query += " AND tool_name = ?"
                params.append(tool_name)
            if search:
                query += " AND (tool_name LIKE ? OR server_id LIKE ? OR error_message LIKE ?)"
                wild = f"%{search}%"
                params.extend([wild, wild, wild])

            query += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur.execute(query, params)
            rows = cur.fetchall()

            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "session_id": r["session_id"],
                    "caller": r["caller"],
                    "server_id": r["server_id"],
                    "tool_name": r["tool_name"],
                    "latency_ms": round(r["latency_ms"], 2),
                    "success": bool(r["success"]),
                    "cache_hit": bool(r["cache_hit"]),
                    "tokens_baseline": r["tokens_baseline"],
                    "tokens_mesh": r["tokens_mesh"],
                    "tokens_saved": r["tokens_saved"],
                    "error_message": r["error_message"]
                })
            return results
        finally:
            conn.close()

    def get_server_stats(self) -> List[Dict[str, Any]]:
        """Aggregates metrics grouped by upstream server."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    server_id,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                    SUM(tokens_saved) as tokens_saved,
                    AVG(latency_ms) as avg_latency_ms
                FROM calls
                GROUP BY server_id
                ORDER BY total_calls DESC
                """
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                fail = r["failed_calls"] or 0
                total = r["total_calls"] or 0
                status = "DEGRADED" if (fail / total > 0.1) else "HEALTHY"
                results.append({
                    "server_id": r["server_id"],
                    "total_calls": total,
                    "successful_calls": r["successful_calls"] or 0,
                    "failed_calls": fail,
                    "tokens_saved": r["tokens_saved"] or 0,
                    "avg_latency_ms": round(r["avg_latency_ms"] or 0.0, 2),
                    "status": status
                })
            return results
        finally:
            conn.close()

    def get_topology_graph(self) -> Dict[str, Any]:
        """
        Builds graph nodes and links representing the gateway, servers, tools,
        and tool-to-tool co-occurrence relationships.
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()

            nodes: List[Dict[str, Any]] = [
                {"id": "gateway:mcp-mesh", "name": "mcp-mesh Gateway", "group": "gateway", "size": 32}
            ]
            links: List[Dict[str, Any]] = []

            # 1. Fetch servers
            cur.execute("SELECT server_id, COUNT(*) as call_count FROM calls GROUP BY server_id")
            server_rows = cur.fetchall()
            server_ids = set()

            for s in server_rows:
                sid = s["server_id"]
                server_ids.add(sid)
                node_id = f"server:{sid}"
                nodes.append({
                    "id": node_id,
                    "name": sid,
                    "group": "server",
                    "call_count": s["call_count"],
                    "size": 22
                })
                # Link gateway -> server
                links.append({
                    "source": "gateway:mcp-mesh",
                    "target": node_id,
                    "type": "hierarchy",
                    "weight": s["call_count"]
                })

            # 2. Fetch tools
            cur.execute(
                """
                SELECT server_id, tool_name, COUNT(*) as call_count, SUM(tokens_saved) as tokens_saved
                FROM calls
                GROUP BY server_id, tool_name
                ORDER BY call_count DESC
                LIMIT 30
                """
            )
            tool_rows = cur.fetchall()
            tool_ids = set()

            for t in tool_rows:
                t_name = t["tool_name"]
                sid = t["server_id"]
                node_id = f"tool:{sid}::{t_name}"
                tool_ids.add(node_id)
                nodes.append({
                    "id": node_id,
                    "name": t_name,
                    "server": sid,
                    "group": "tool",
                    "call_count": t["call_count"],
                    "tokens_saved": t["tokens_saved"] or 0,
                    "size": 14
                })
                # Link server -> tool
                links.append({
                    "source": f"server:{sid}",
                    "target": node_id,
                    "type": "hierarchy",
                    "weight": t["call_count"]
                })

            # 3. Fetch tool co-occurrence links
            cur.execute("SELECT tool_a, tool_b, count FROM tool_cooccurrence ORDER BY count DESC LIMIT 20")
            co_rows = cur.fetchall()

            for co in co_rows:
                ta = co["tool_a"]
                tb = co["tool_b"]
                node_a = f"tool:{ta}" if "::" in ta else None
                node_b = f"tool:{tb}" if "::" in tb else None

                # Find matching nodes
                matched_a = next((n["id"] for n in nodes if n["name"] == ta or n["id"].endswith(f"::{ta}")), None)
                matched_b = next((n["id"] for n in nodes if n["name"] == tb or n["id"].endswith(f"::{tb}")), None)

                if matched_a and matched_b and matched_a != matched_b:
                    links.append({
                        "source": matched_a,
                        "target": matched_b,
                        "type": "cooccurrence",
                        "weight": co["count"]
                    })

            return {"nodes": nodes, "links": links}
        finally:
            conn.close()

    def simulate_traffic(self, num_calls: int = 30) -> int:
        """
        Injects realistic synthetic tool invocations and co-occurrence updates
        for demonstrations, UI testing, and benchmarks.
        """
        servers_tools = {
            "github": ["search_code", "create_issue", "read_file", "list_pull_requests", "get_commit"],
            "postgres": ["query_readonly", "explain_plan", "introspect_schema", "list_tables"],
            "filesystem": ["read_file", "write_file", "search_directory", "get_metadata"],
            "ghost-job-hunter": ["audit_posting", "audit_company_github", "match_candidate", "generate_pitch"],
            "aws": ["describe_instances", "get_metric_data", "list_buckets"],
            "slack": ["send_message", "list_channels", "search_messages"]
        }

        conn = self._get_connection()
        try:
            with conn:
                session_id = f"sim-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                conn.execute(
                    "INSERT OR REPLACE INTO sessions VALUES (?, ?, 'benchmark', ?, ?)",
                    (session_id, datetime.datetime.now().isoformat(), len(servers_tools), sum(len(t) for t in servers_tools.values()))
                )

                now = datetime.datetime.now()
                last_tool = None

                for i in range(num_calls):
                    time_offset = now - datetime.timedelta(seconds=(num_calls - i) * 3)
                    ts = time_offset.isoformat()
                    server = random.choice(list(servers_tools.keys()))
                    tool = random.choice(servers_tools[server])
                    
                    latency = round(random.uniform(1.2, 14.5), 2)
                    success = 1 if random.random() > 0.05 else 0
                    err = None if success else "Downstream connection timeout (circuit breaker engaged)"
                    cache_hit = 1 if random.random() > 0.4 else 0
                    
                    baseline_tokens = random.randint(1200, 3200)
                    mesh_tokens = random.randint(80, 160)
                    tokens_saved = baseline_tokens - mesh_tokens

                    conn.execute(
                        """
                        INSERT INTO calls (
                            timestamp, session_id, caller, server_id, tool_name,
                            latency_ms, success, cache_hit, tokens_baseline, tokens_mesh, tokens_saved, error_message
                        ) VALUES (?, ?, 'autonomous_agent', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (ts, session_id, server, tool, latency, success, cache_hit, baseline_tokens, mesh_tokens, tokens_saved, err)
                    )

                    # Update co-occurrence
                    current_qualified = f"{server}::{tool}"
                    if last_tool and last_tool != current_qualified:
                        a, b = sorted([last_tool, current_qualified])
                        conn.execute(
                            """
                            INSERT INTO tool_cooccurrence (tool_a, tool_b, count, last_seen)
                            VALUES (?, ?, 1, ?)
                            ON CONFLICT(tool_a, tool_b) DO UPDATE SET count = count + 1, last_seen = ?
                            """,
                            (a, b, ts, ts)
                        )
                    last_tool = current_qualified

            return num_calls
        finally:
            conn.close()
