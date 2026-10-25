// mcp-mesh-ui: Developer Observability Client (Vanilla JS)
// Zero external dependencies

let refreshTimer = null;
let currentInterval = 2000;
let cachedCalls = [];
let topologyData = { nodes: [], links: [] };

document.addEventListener("DOMContentLoaded", () => {
  initControls();
  refreshAll();
  startAutoRefresh();
});

function initControls() {
  // Segmented refresh interval
  const segButtons = document.querySelectorAll(".seg-btn");
  segButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      segButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const interval = parseInt(btn.dataset.interval, 10);
      currentInterval = interval;
      startAutoRefresh();
    });
  });

  // Traffic simulation
  const btnSimulate = document.getElementById("btn-simulate");
  btnSimulate.addEventListener("click", async () => {
    btnSimulate.disabled = true;
    btnSimulate.style.opacity = "0.6";
    try {
      const res = await fetch("/api/simulate", { method: "POST" });
      if (res.ok) {
        await refreshAll();
      }
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      btnSimulate.disabled = false;
      btnSimulate.style.opacity = "1";
    }
  });

  // Search filter
  const filterInput = document.getElementById("stream-filter");
  filterInput.addEventListener("input", () => {
    applyCallFilters();
  });

  // Keyboard shortcut '/'
  window.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== filterInput) {
      e.preventDefault();
      filterInput.focus();
    } else if (e.key === "Escape") {
      closeInspectModal();
    }
  });

  // Server filter select
  const serverSelect = document.getElementById("server-filter-select");
  serverSelect.addEventListener("change", () => {
    applyCallFilters();
  });

  // Modal close
  document.getElementById("btn-close-modal").addEventListener("click", closeInspectModal);
  document.getElementById("inspect-modal").addEventListener("click", (e) => {
    if (e.target.id === "inspect-modal") closeInspectModal();
  });

  // Reset zoom
  document.getElementById("btn-reset-zoom").addEventListener("click", () => {
    if (topologyData.nodes.length > 0) renderTopologySvg(topologyData);
  });
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  if (currentInterval > 0) {
    refreshTimer = setInterval(refreshAll, currentInterval);
  }
}

async function refreshAll() {
  await Promise.all([fetchStats(), fetchServers(), fetchCalls(), fetchTopology()]);
}

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("val-tokens-saved").textContent = Number(data.total_tokens_saved).toLocaleString();
    document.getElementById("val-savings-pct").textContent = `${data.overall_savings_pct}% saved`;
    document.getElementById("val-cost-saved").textContent = `$${Number(data.estimated_cost_saved_usd).toFixed(4)}`;
    document.getElementById("val-total-calls").textContent = Number(data.total_calls).toLocaleString();
    document.getElementById("val-success-rate").textContent = `${data.success_rate}% OK`;
    document.getElementById("val-latency").textContent = `${data.p50_latency_ms}ms / ${data.p95_latency_ms}ms`;
    document.getElementById("val-cache-hit").textContent = `Cache: ${data.cache_hit_rate}%`;

    const okCount = data.successful_calls || (data.total_calls - (data.failed_calls || 0));
    const failCount = data.failed_calls || 0;
    document.getElementById("val-call-breakdown").textContent = `${Number(okCount).toLocaleString()} OK • ${failCount} Errors (${data.active_servers_count || 0} active upstreams)`;
  } catch (err) {
    console.error("Error fetching stats:", err);
  }
}

async function fetchServers() {
  try {
    const res = await fetch("/api/servers");
    if (!res.ok) return;
    const servers = await res.json();

    document.getElementById("server-count").textContent = `${servers.length} Upstreams`;
    const container = document.getElementById("servers-container");
    container.innerHTML = "";

    const select = document.getElementById("server-filter-select");
    const currentVal = select.value;
    select.innerHTML = '<option value="">All Upstreams</option>';

    servers.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.server_id;
      opt.textContent = `${s.server_id} (${s.total_calls} calls)`;
      if (s.server_id === currentVal) opt.selected = true;
      select.appendChild(opt);

      const isHealthy = s.status === "HEALTHY";
      const card = document.createElement("div");
      card.className = "server-card";
      card.innerHTML = `
        <div class="server-card-info">
          <span class="server-card-name">${escapeHtml(s.server_id)}</span>
          <span class="server-card-meta">${s.total_calls} calls • ${s.avg_latency_ms}ms avg</span>
        </div>
        <div class="server-card-stats">
          <span class="badge-status ${isHealthy ? 'healthy' : 'failing'}">${s.status}</span>
        </div>
      `;
      card.addEventListener("click", () => {
        select.value = s.server_id;
        applyCallFilters();
      });
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Error fetching servers:", err);
  }
}

async function fetchCalls() {
  try {
    const res = await fetch("/api/calls?limit=60");
    if (!res.ok) return;
    cachedCalls = await res.json();
    applyCallFilters();
  } catch (err) {
    console.error("Error fetching calls:", err);
  }
}

function applyCallFilters() {
  const query = document.getElementById("stream-filter").value.toLowerCase().trim();
  const selectedServer = document.getElementById("server-filter-select").value;

  const filtered = cachedCalls.filter(c => {
    if (selectedServer && c.server_id !== selectedServer) return false;
    if (query) {
      const matchServer = c.server_id && c.server_id.toLowerCase().includes(query);
      const matchTool = c.tool_name && c.tool_name.toLowerCase().includes(query);
      if (!matchServer && !matchTool) return false;
    }
    return true;
  });

  renderCallsTable(filtered);
}

function renderCallsTable(calls) {
  const tbody = document.getElementById("calls-tbody");
  tbody.innerHTML = "";

  if (calls.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">No matching invocation records found</td>`;
    tbody.appendChild(tr);
    return;
  }

  calls.forEach(c => {
    const tr = document.createElement("tr");
    const rawTime = c.timestamp || "";
    const timeDisplay = rawTime.includes("T") ? rawTime.split("T")[1].slice(0, 12) : rawTime.slice(11, 23);

    const isOk = c.success !== false && c.success !== 0;
    const latencyColor = c.latency_ms < 15 ? "color: var(--color-emerald)" : c.latency_ms < 60 ? "color: var(--color-amber)" : "color: var(--color-rose)";

    tr.innerHTML = `
      <td class="mono" style="font-size: 11px;">${escapeHtml(timeDisplay)}</td>
      <td><span class="mono" style="font-weight: 600; color: #fafafa;">${escapeHtml(c.server_id)}</span></td>
      <td><span class="mono" style="color: #93c5fd;">${escapeHtml(c.tool_name)}</span></td>
      <td class="mono" style="${latencyColor}; font-weight: 500;">${c.latency_ms}ms</td>
      <td class="mono" style="color: var(--color-emerald);">+${Number(c.tokens_saved || 0).toLocaleString()}</td>
      <td>${c.cache_hit ? '<span class="pill-cache-hit">HIT</span>' : '<span class="pill-cache-miss">MISS</span>'}</td>
      <td>${isOk ? '<span class="outcome-ok">200 OK</span>' : '<span class="outcome-err">500 ERR</span>'}</td>
      <td style="text-align: right;">
        <button class="btn-inspect" data-call-id="${escapeHtml(c.tool_name)}">Inspect</button>
      </td>
    `;

    tr.querySelector(".btn-inspect").addEventListener("click", (e) => {
      e.stopPropagation();
      openInspectModal(c);
    });

    tr.addEventListener("click", () => {
      openInspectModal(c);
    });

    tbody.appendChild(tr);
  });
}

async function fetchTopology() {
  try {
    const res = await fetch("/api/topology");
    if (!res.ok) return;
    topologyData = await res.json();
    document.getElementById("topology-stats").textContent = `Nodes: ${topologyData.nodes.length} | Links: ${topologyData.links.length}`;
    renderTopologySvg(topologyData);
  } catch (err) {
    console.error("Error fetching topology:", err);
  }
}

function renderTopologySvg(data) {
  const svg = document.getElementById("topology-svg");
  const width = svg.clientWidth || 700;
  const height = 360;
  svg.innerHTML = "";

  if (!data.nodes || data.nodes.length === 0) {
    svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="#71717a" font-size="12" font-family="monospace">Zero topology entries recorded. Click 'Simulate Traffic' to view network.</text>`;
    return;
  }

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(g);

  // Group servers and tools
  const serverNodes = data.nodes.filter(n => n.type === "server");
  const toolNodes = data.nodes.filter(n => n.type === "tool");

  // Center coordinates
  const centerX = width / 2;
  const centerY = height / 2;

  // Position servers in inner ring
  const serverRadius = Math.min(width, height) * 0.25;
  serverNodes.forEach((s, idx) => {
    const angle = (idx / (serverNodes.length || 1)) * 2 * Math.PI;
    s.x = centerX + serverRadius * Math.cos(angle);
    s.y = centerY + serverRadius * Math.sin(angle);
  });

  // Position tools in outer ring
  const toolRadius = Math.min(width, height) * 0.42;
  toolNodes.forEach((t, idx) => {
    const angle = (idx / (toolNodes.length || 1)) * 2 * Math.PI;
    t.x = centerX + toolRadius * Math.cos(angle);
    t.y = centerY + toolRadius * Math.sin(angle);
  });

  const nodeMap = new Map();
  data.nodes.forEach(n => nodeMap.set(n.id, n));

  // Render Links (Curved subtle lines)
  data.links.forEach(link => {
    const source = nodeMap.get(link.source);
    const target = nodeMap.get(link.target);
    if (!source || !target) return;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dr = Math.sqrt(dx * dx + dy * dy) * 1.2;
    path.setAttribute("d", `M${source.x},${source.y}A${dr},${dr} 0 0,1 ${target.x},${target.y}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#272a33");
    path.setAttribute("stroke-width", Math.min(link.weight || 1, 3));
    path.setAttribute("stroke-opacity", "0.6");
    g.appendChild(path);
  });

  // Render Nodes
  data.nodes.forEach(node => {
    const isServer = node.type === "server";
    const nodeG = document.createElementNS("http://www.w3.org/2000/svg", "g");
    nodeG.setAttribute("transform", `translate(${node.x},${node.y})`);
    nodeG.style.cursor = "pointer";

    if (isServer) {
      // Server node as crisp rounded rect
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", -45);
      rect.setAttribute("y", -14);
      rect.setAttribute("width", 90);
      rect.setAttribute("height", 28);
      rect.setAttribute("rx", 6);
      rect.setAttribute("fill", "#181a20");
      rect.setAttribute("stroke", "#3b82f6");
      rect.setAttribute("stroke-width", "1.5");
      nodeG.appendChild(rect);

      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("y", 4);
      label.setAttribute("fill", "#fafafa");
      label.setAttribute("font-size", "11");
      label.setAttribute("font-family", "ui-monospace, monospace");
      label.setAttribute("font-weight", "600");
      label.textContent = truncate(node.label || node.id, 10);
      nodeG.appendChild(label);
    } else {
      // Tool node as crisp circle
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("r", 6);
      circle.setAttribute("fill", "#10b981");
      circle.setAttribute("stroke", "#09090b");
      circle.setAttribute("stroke-width", "2");
      nodeG.appendChild(circle);

      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("text-anchor", node.x > centerX ? "start" : "end");
      label.setAttribute("x", node.x > centerX ? 10 : -10);
      label.setAttribute("y", 3);
      label.setAttribute("fill", "#a1a1aa");
      label.setAttribute("font-size", "10");
      label.setAttribute("font-family", "ui-monospace, monospace");
      label.textContent = truncate(node.label || node.id, 12);
      nodeG.appendChild(label);
    }

    // Hover tooltip
    const tooltip = document.getElementById("node-tooltip");
    nodeG.addEventListener("mouseenter", (e) => {
      tooltip.classList.remove("hidden");
      tooltip.textContent = `${node.type.toUpperCase()}: ${node.id} (${node.invocations || 0} calls)`;
      const rect = svg.getBoundingClientRect();
      tooltip.style.left = `${node.x + 15}px`;
      tooltip.style.top = `${node.y - 10}px`;
    });

    nodeG.addEventListener("mouseleave", () => {
      tooltip.classList.add("hidden");
    });

    nodeG.addEventListener("click", () => {
      if (isServer) {
        document.getElementById("server-filter-select").value = node.id;
        applyCallFilters();
      } else {
        document.getElementById("stream-filter").value = node.id;
        applyCallFilters();
      }
    });

    g.appendChild(nodeG);
  });
}

function openInspectModal(call) {
  const modal = document.getElementById("inspect-modal");
  document.getElementById("modal-tool-title").textContent = `JSON-RPC Telemetry // ${call.server_id}::${call.tool_name}`;

  const metaGrid = document.getElementById("modal-meta-grid");
  metaGrid.innerHTML = `
    <div class="meta-box">
      <div class="meta-box-label">Execution Latency</div>
      <div class="meta-box-value" style="color: var(--color-emerald);">${call.latency_ms} ms</div>
    </div>
    <div class="meta-box">
      <div class="meta-box-label">Tokens Saved</div>
      <div class="meta-box-value">+${Number(call.tokens_saved || 0).toLocaleString()}</div>
    </div>
    <div class="meta-box">
      <div class="meta-box-label">Cache Outcome</div>
      <div class="meta-box-value" style="color: ${call.cache_hit ? 'var(--color-sky)' : 'var(--text-muted)'};">${call.cache_hit ? 'LRU HIT' : 'COLD ROUTE'}</div>
    </div>
  `;

  const payload = {
    jsonrpc: "2.0",
    id: `req_${Math.random().toString(36).substring(2, 8)}`,
    method: "tools/call",
    params: {
      server: call.server_id,
      name: call.tool_name,
      arguments: {
        filter: "auto",
        scope: "production",
        dry_run: false
      }
    },
    meta: {
      gateway: "mcp-mesh-v1.3.0",
      routing_latency_ms: call.latency_ms,
      tokens_saved: call.tokens_saved,
      status: call.success ? "200_OK" : "500_FAILED"
    }
  };

  document.getElementById("modal-code-body").textContent = JSON.stringify(payload, null, 2);
  modal.classList.remove("hidden");
}

function closeInspectModal() {
  document.getElementById("inspect-modal").classList.add("hidden");
}

function truncate(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max - 1) + "…" : str;
}

function escapeHtml(text) {
  if (!text) return "";
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}
