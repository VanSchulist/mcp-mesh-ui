# 🕸️ `mcp-mesh-ui`

> **The Real-Time Topology Visualizer & Observability Dashboard for `mcp-mesh`**  
> Inspect dynamic tool mesh routing, monitor Turn-0 token economies, visualize tool co-occurrence graphs, and observe downstream MCP server health with zero external dependencies.

[![Satellite 2](https://img.shields.io/badge/Role-Satellite%202%20(Existential%20Cloud)-8A2BE2?style=flat-square)](https://github.com/VanSchulist)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-success?style=flat-square)](https://github.com/VanSchulist/mcp-mesh-ui)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Compatible with mcp-mesh](https://img.shields.io/badge/Gateway-mcp--mesh%20v1.2.0%2B-orange?style=flat-square)](https://github.com/VanSchulist/mcp-mesh)

```text
   __  __  ____ ____        __  __ _____ ____  _   _       _   _ ___ 
  |  \/  |/ ___|  _ \      |  \/  | ____/ ___|| | | |     | | | |_ _|
  | |\/| | |   | |_) |_____| |\/| |  _| \___ \| |_| |_____| | | || | 
  | |  | | |___|  __/______| |  | | |___ ___) |  _  |_____| |_| || | 
  |_|  |_|\____|_|         |_|  |_|_____|____/|_| |_|      \___/|___|
  >> SATELLITE 2: REAL-TIME OBSERVABILITY DASHBOARD <<
  Curated & Engineered by Van Schulist (@VanSchulist) | Existential Cloud
```

---

## 💡 Why `mcp-mesh-ui`?

When running autonomous AI agents through [`mcp-mesh`](https://github.com/VanSchulist/mcp-mesh), the gateway transparently indexes, lazily resolves, and routes tool calls across dozens of downstream servers. 

However, developer visibility has historically been a black box:
* *Which tools are being invoked most frequently?*
* *How many Turn-0 prompt tokens are actually being saved in real time?*
* *What is the p50 and p95 latency across downstream MCP servers?*
* *Which tools frequently co-occur during complex multi-step reasoning?*
* *Are any downstream servers flapping or engaging circuit breakers?*

`mcp-mesh-ui` provides the answer with **Zero External Dependencies**—serving both an interactive dark-mode web dashboard and an ANSI terminal monitor directly from standard Python.

---

## ✨ Features

* 📊 **Live Token Economy Meter**: Real-time counter of Turn-0 tokens saved, percentage reduction vs static schema dumps, and estimated dollar savings based on blended frontier model pricing.
* 🕸️ **Interactive Mesh Topology & Co-occurrence Graph**: Concentric SVG network graph charting the Gateway, connected upstream MCP servers, active tools, and probabilistic tool co-occurrence links.
* ⚡ **Real-Time Invocations Waterfall**: Low-latency event stream with per-call status, duration in milliseconds, LRU cache hit badges, and error diagnostics.
* 📡 **Downstream Server Health Matrix**: Live monitoring of server states (`HEALTHY` vs `DEGRADED`), call counts, and failure rates.
* 🖥️ **Dual UI Interfaces**:
  * **Local Web Dashboard**: Modern glassmorphic SPA on `http://127.0.0.1:8765` with Server-Sent Events (SSE) live updates.
  * **ANSI Terminal TUI**: Zero-browser console monitor refreshing in real-time (`mcp-mesh-ui tui`).
* 🧪 **Built-in Synthetic Traffic Simulator**: Fire benchmark tool calls with a single click or CLI flag to test visualizer telemetry offline.
* 📦 **Zero External Dependencies**: Engineered purely with Python 3.10+ standard library (`http.server`, `sqlite3`, `json`, `dataclasses`, `socketserver`).

---

## 🏛️ Architecture

```text
 ┌────────────────────────────────────────────────────────┐
 │                   Autonomous Agent                     │
 │          (Claude, Cursor, Antigravity, Hunter)         │
 └───────────────────────────┬────────────────────────────┘
                             │ Tool Invocations
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │              mcp-mesh Gateway (v1.2.0)                 │
 │   • Inverted BM25 Index     • Watchdog Circuit Breaker │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼ Writes Telemetry
 ┌────────────────────────────────────────────────────────┐
 │        SQLite Telemetry Ledger (~/.mcp-mesh)           │
 │       • sessions   • calls   • tool_cooccurrence       │
 └───────────────────────────┬────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼ Reads Stream                    ▼
 ┌───────────────────────────┐   ┌───────────────────────────┐
 │   mcp-mesh-ui Web Server  │   │     mcp-mesh-ui TUI       │
 │   • Port 8765 / SSE Stream│   │   • ANSI Live Console     │
 │   • Glassmorphic SPA      │   │   • Zero-Browser Monitor  │
 └───────────────────────────┘   └───────────────────────────┘
```

---

## 🚀 Quickstart & Installation

### Option A: Run from Source
```bash
git clone https://github.com/VanSchulist/mcp-mesh-ui.git
cd mcp-mesh-ui

# 1. Launch the interactive local Web Dashboard (opens browser at http://127.0.0.1:8765)
python main.py web

# 2. Or launch the live-refreshing ANSI Terminal TUI
python main.py tui

# 3. Print a one-shot terminal diagnostic summary
python main.py status

# 4. Inject simulated telemetry calls to demo live charts
python main.py simulate --calls 30

# 5. Export telemetry logs to JSON or CSV
python main.py export --format json --output telemetry_dump.json
```

---

## 🛠️ CLI Subcommands & Options

| Subcommand | Flags / Options | Description |
| :--- | :--- | :--- |
| `web` | `--port <int>`, `--host <str>`, `--no-open`, `--db <path>` | Launches multi-threaded HTTP server and opens browser dashboard. |
| `tui` | `--interval <float>`, `--db <path>` | Starts live terminal dashboard with automatic screen clearing. |
| `status` | `--json`, `--db <path>` | Outputs instantaneous summary metrics and server health. |
| `simulate` | `--calls <int>`, `--db <path>` | Synthesizes realistic agent tool calls for demo & benchmarking. |
| `export` | `--format <json\|csv>`, `--output <path>` | Dumps full historical telemetry records to structured file. |

---

## 🧪 Running the Test Suite

```bash
python -m unittest discover -s tests
```

All 13 unit tests execute in ~1.2s across SQLite data operations, REST API endpoints, topology builders, and export serializers.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
