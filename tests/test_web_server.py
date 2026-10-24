"""
Unit Tests for mcp-mesh-ui Web Server and REST API Endpoints.
"""

import unittest
import tempfile
import threading
import urllib.request
import json
from pathlib import Path

from mcp_mesh_ui.core import MeshTelemetryStore
from mcp_mesh_ui.web_server import run_server


class TestWebServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_telemetry.db"
        cls.store = MeshTelemetryStore(db_path=cls.db_path)
        cls.store.simulate_traffic(num_calls=10)

        # Bind to high test port
        cls.port = 18765
        cls.server = run_server(port=cls.port, host="127.0.0.1", db_path=cls.db_path)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def test_get_index_html(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            content = res.read().decode("utf-8")
            self.assertIn("mcp-mesh-ui", content)
            self.assertIn("Topology", content)

    def test_get_api_stats(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/stats")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("total_calls", data)
            self.assertEqual(data["total_calls"], 10)
            self.assertIn("total_tokens_saved", data)

    def test_get_api_calls(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/calls?limit=5")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            calls = json.loads(res.read().decode("utf-8"))
            self.assertIsInstance(calls, list)
            self.assertEqual(len(calls), 5)

    def test_get_api_topology(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/topology")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            topology = json.loads(res.read().decode("utf-8"))
            self.assertIn("nodes", topology)
            self.assertIn("links", topology)

    def test_post_api_simulate(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/simulate", data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertGreater(data["generated_calls"], 0)


if __name__ == "__main__":
    unittest.main()
