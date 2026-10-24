// mcp-mesh-ui Real-Time Dashboard Client (Vanilla JS)

let topologyData = { nodes: [], links: [] };

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const data = await res.json();
    
    document.getElementById("val-tokens-saved").textContent = Number(data.total_tokens_saved).toLocaleString();
    document.getElementById("val-savings-pct").textContent = `${data.overall_savings_pct}% reduction vs static injection`;
    document.getElementById("val-cost-saved").textContent = `$${Number(data.estimated_cost_saved_usd).toFixed(4)}`;
    document.getElementById("val-total-calls").textContent = Number(data.total_calls).toLocaleString();
    document.getElementById("val-success-rate").textContent = `${data.success_rate}% Success Rate`;
    document.getElementById("val-latency").textContent = `${data.p50_latency_ms}ms / ${data.p95_latency_ms}ms`;
    document.getElementById("val-cache-hit").textContent = `Cache Hit: ${data.cache_hit_rate}%`;
  } catch (err) {
    console.error("Error fetching stats:", err);
  }
}

async function fetchServers() {
  try {
    const res = await fetch("/api/servers");
    if (!res.ok) return;
    const servers = await res.json();
    
    document.getElementById("server-count").textContent = `${servers.length} Connected`;
    const container = document.getElementById("servers-container");
    container.innerHTML = "";
    
    servers.forEach(s => {
      const item = document.createElement("div");
      item.className = "server-item";
      item.innerHTML = `
        <div>
          <div class="server-name">📡 ${s.server_id}</div>
          <div class="server-meta">${s.total_calls} calls | ${s.avg_latency_ms}ms avg</div>
        </div>
        <span class="badge ${s.status === 'HEALTHY' ? 'badge-success' : 'badge-fail'}">${s.status}</span>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    console.error("Error fetching servers:", err);
  }
}

async function fetchCalls() {
  try {
    const filter = document.getElementById("stream-filter").value.toLowerCase();
    const res = await fetch(`/api/calls?limit=25&search=${encodeURIComponent(filter)}`);
    if (!res.ok) return;
    const calls = await res.json();
    
    const tbody = document.getElementById("calls-tbody");
    tbody.innerHTML = "";
    
    calls.forEach(c => {
      const tr = document.createElement("tr");
      const time = c.timestamp ? c.timestamp.split("T")[1]?.slice(0, 8) || c.timestamp : "";
      tr.innerHTML = `
        <td>${time}</td>
        <td><strong>${c.server_id}</strong></td>
        <td><code>${c.tool_name}</code></td>
        <td>${c.latency_ms}ms</td>
        <td>+${c.tokens_saved}</td>
        <td>${c.cache_hit ? '<span class="badge-cache">HIT</span>' : '-'}</td>
        <td>${c.success ? '<span class="badge-success">OK</span>' : '<span class="badge-fail">ERR</span>'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error fetching calls:", err);
  }
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
  const width = svg.clientWidth || 600;
  const height = 380;
  svg.innerHTML = "";

  if (!data.nodes || data.nodes.length === 0) {
    svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="#94a3b8">No topology data yet. Trigger traffic to view graph.</text>`;
    return;
  }

  // Simple concentric layout
  const gateway = data.nodes.find(n => n.group === "gateway") || { id: "gateway" };
  const servers = data.nodes.filter(n => n.group === "server");
  const tools = data.nodes.filter(n => n.group === "tool");

  const pos = {};
  pos[gateway.id] = { x: width / 2, y: height / 2 };

  // Servers in inner ring
  const sRadius = Math.min(width, height) * 0.25;
  servers.forEach((s, i) => {
    const angle = (i / Math.max(servers.length, 1)) * 2 * Math.PI;
    pos[s.id] = { x: width / 2 + sRadius * Math.cos(angle), y: height / 2 + sRadius * Math.sin(angle) };
  });

  // Tools in outer ring
  const tRadius = Math.min(width, height) * 0.42;
  tools.forEach((t, i) => {
    const angle = (i / Math.max(tools.length, 1)) * 2 * Math.PI;
    pos[t.id] = { x: width / 2 + tRadius * Math.cos(angle), y: height / 2 + tRadius * Math.sin(angle) };
  });

  // Render links
  data.links.forEach(l => {
    const p1 = pos[l.source];
    const p2 = pos[l.target];
    if (p1 && p2) {
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", p1.x);
      line.setAttribute("y1", p1.y);
      line.setAttribute("x2", p2.x);
      line.setAttribute("y2", p2.y);
      line.setAttribute("stroke", l.type === "cooccurrence" ? "#f59e0b" : "rgba(138, 43, 226, 0.4)");
      line.setAttribute("stroke-width", l.type === "cooccurrence" ? "1.5" : "1");
      if (l.type === "cooccurrence") line.setAttribute("stroke-dasharray", "3,3");
      svg.appendChild(line);
    }
  });

  // Render nodes
  data.nodes.forEach(n => {
    const p = pos[n.id];
    if (!p) return;
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    circle.setAttribute("r", n.group === "gateway" ? 16 : n.group === "server" ? 10 : 6);
    circle.setAttribute("fill", n.group === "gateway" ? "#8a2be2" : n.group === "server" ? "#06b6d4" : "#10b981");
    circle.setAttribute("stroke", "#ffffff");
    circle.setAttribute("stroke-width", "1.5");

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", p.x);
    text.setAttribute("y", p.y + (n.group === "tool" ? 14 : 20));
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", n.group === "gateway" ? "11px" : "9px");
    text.setAttribute("fill", "#cbd5e1");
    text.textContent = n.name.length > 15 ? n.name.slice(0, 13) + "..." : n.name;

    g.appendChild(circle);
    g.appendChild(text);
    svg.appendChild(g);
  });
}

function initSSE() {
  const evtSource = new EventSource("/api/stream");
  const indicator = document.getElementById("connection-status");

  evtSource.onmessage = function(event) {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "ping") return;
      fetchStats();
      fetchCalls();
      fetchServers();
    } catch(e) {}
  };

  evtSource.onerror = function() {
    indicator.textContent = "○ POLLING";
    indicator.className = "status-indicator";
  };
}

document.addEventListener("DOMContentLoaded", () => {
  fetchStats();
  fetchServers();
  fetchCalls();
  fetchTopology();
  initSSE();

  // Polling fallback every 3s
  setInterval(() => {
    fetchStats();
    fetchCalls();
  }, 3000);

  // Re-fetch topology every 10s
  setInterval(fetchTopology, 10000);

  document.getElementById("btn-simulate").addEventListener("click", async () => {
    const btn = document.getElementById("btn-simulate");
    btn.disabled = true;
    btn.textContent = "Generating...";
    await fetch("/api/simulate", { method: "POST" });
    await fetchStats();
    await fetchCalls();
    await fetchServers();
    await fetchTopology();
    btn.disabled = false;
    btn.textContent = "⚡ Simulate Traffic";
  });

  document.getElementById("stream-filter").addEventListener("input", fetchCalls);
});
