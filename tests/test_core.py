"""
Unit Tests for mcp-mesh-ui Core Telemetry Store & Topology Engine.
"""

import unittest
import tempfile
import sqlite3
from pathlib import Path
from mcp_mesh_ui.core import MeshTelemetryStore, TelemetrySummary


class TestMeshTelemetryStore(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_telemetry.db"
        self.store = MeshTelemetryStore(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_summary(self):
        summary = self.store.get_summary()
        self.assertIsInstance(summary, TelemetrySummary)
        self.assertEqual(summary.total_calls, 0)
        self.assertEqual(summary.total_tokens_saved, 0)
        self.assertEqual(summary.success_rate, 100.0)

    def test_simulate_traffic_and_metrics(self):
        count = self.store.simulate_traffic(num_calls=20)
        self.assertEqual(count, 20)

        summary = self.store.get_summary()
        self.assertEqual(summary.total_calls, 20)
        self.assertGreater(summary.total_tokens_saved, 0)
        self.assertGreater(summary.active_servers_count, 0)
        self.assertGreater(summary.active_tools_count, 0)
        self.assertGreaterEqual(summary.success_rate, 0.0)

    def test_recent_calls_pagination_and_filter(self):
        self.store.simulate_traffic(num_calls=15)
        calls = self.store.get_recent_calls(limit=10)
        self.assertEqual(len(calls), 10)

        # Check call fields
        c = calls[0]
        self.assertIn("tool_name", c)
        self.assertIn("server_id", c)
        self.assertIn("latency_ms", c)
        self.assertIn("tokens_saved", c)

    def test_topology_graph_construction(self):
        self.store.simulate_traffic(num_calls=25)
        graph = self.store.get_topology_graph()
        self.assertIn("nodes", graph)
        self.assertIn("links", graph)

        # Should contain gateway node
        node_ids = [n["id"] for n in graph["nodes"]]
        self.assertIn("gateway:mcp-mesh", node_ids)
        self.assertGreater(len(graph["nodes"]), 1)
        self.assertGreater(len(graph["links"]), 1)

    def test_server_stats_grouping(self):
        self.store.simulate_traffic(num_calls=20)
        servers = self.store.get_server_stats()
        self.assertGreater(len(servers), 0)
        for s in servers:
            self.assertIn("server_id", s)
            self.assertIn("total_calls", s)
            self.assertIn("status", s)


if __name__ == "__main__":
    unittest.main()
