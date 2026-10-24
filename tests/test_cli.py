"""
Unit Tests for mcp-mesh-ui CLI & Export Engine.
"""

import unittest
import tempfile
import json
import csv
from pathlib import Path
from mcp_mesh_ui.core import MeshTelemetryStore
from mcp_mesh_ui.tui import render_dashboard


class TestCliAndExport(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_telemetry.db"
        self.store = MeshTelemetryStore(db_path=self.db_path)
        self.store.simulate_traffic(num_calls=15)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_render_tui_dashboard(self):
        output = render_dashboard(self.store)
        self.assertIn("MCP-MESH REAL-TIME OBSERVABILITY DASHBOARD", output)
        self.assertIn("TOKEN ECONOMY", output)
        self.assertIn("UPSTREAM MCP SERVERS", output)

    def test_export_json(self):
        calls = self.store.get_recent_calls(limit=10)
        export_file = Path(self.temp_dir.name) / "export.json"
        export_file.write_text(json.dumps(calls, indent=2), encoding="utf-8")

        self.assertTrue(export_file.exists())
        loaded = json.loads(export_file.read_text(encoding="utf-8"))
        self.assertEqual(len(loaded), 10)

    def test_export_csv(self):
        calls = self.store.get_recent_calls(limit=10)
        export_file = Path(self.temp_dir.name) / "export.csv"
        with open(export_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=calls[0].keys())
            writer.writeheader()
            writer.writerows(calls)

        self.assertTrue(export_file.exists())
        lines = export_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 11)  # 1 header + 10 rows


if __name__ == "__main__":
    unittest.main()
