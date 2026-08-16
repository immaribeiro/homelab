/* Hermes Mission Control — SPA (vanilla JS, hash routing, SSE live updates).
 * XSS policy: all dynamic data is rendered via textContent — never innerHTML.
 */
"use strict";

/* ── tiny DOM builder (XSS-safe) ─────────────────────────────── */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(node.dataset, v);
    else node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "");
const fmt = (n) => (n ?? 0).toLocaleString("en-US");

/* ── state ───────────────────────────────────────────────────── */
const state = {
  cfg: null,
  overview: null,
  filters: { agent: "", source: "", model: "", status: "", q: "", active: "" },
  sse: null,
  live: false,
};

/* ── api client ──────────────────────────────────────────────── */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { ...(opts.headers || {}), "X-Auth-Token": sessionStorage.getItem("mc_token") || "" },
  });
  if (res.status === 401) {
    showLogin();
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    let msg = `${res.status}`;
    try { msg = (await res.json()).error || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

/* ── time helpers ────────────────────────────────────────────── */
function timeago(ts) {
  if (!ts) return "—";
  const s = Math.max(0, (Date.now() / 1000) - ts);
  if (s < 5) return "now";
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
function clock(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function fulldate(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "medium" });
}

/* ── badges / dots ───────────────────────────────────────────── */
const STATUS_ORDER = ["working", "waiting", "idle", "done", "error", "unknown"];
const STATUS_LABEL = { working: "WORKING", waiting: "WAITING", idle: "IDLE", done: "DONE", error: "ERROR", unknown: "UNKNOWN" };
function dot(status) { return el("span", { class: `dot dot-${status || "unknown"}` }); }
function statusBadge(status) {
  return el("span", { class: "badge" }, dot(status), STATUS_LABEL[status] || status);
}
function sourceBadge(source) {
  return el("span", { class: `badge badge-source-${source || "unknown"}` }, (source || "unknown").toUpperCase());
}
function modelBadge(model) {
  return el("span", { class: "badge badge-model" }, esc(model || "—"));
}
function agentBadge(agent) {
  return el("span", { class: `badge badge-agent-${agent}` }, esc(agent));
}

/* ── login ───────────────────────────────────────────────────── */
function showLogin() {
  $("#login-overlay").classList.remove("hidden");
}
function hideLogin() {
  $("#login-overlay").classList.add("hidden");
}
async function initLogin() {
  try {
    state.cfg = await api("/api/config");
    if (!state.cfg.auth) return; // loopback, no token → open
    showLogin();
  } catch (_) {
    showLogin();
  }
}
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const token = $("#login-token").value.trim();
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!res.ok) {
      let msg = `sign in failed (${res.status})`;
      try {
        const b = await res.json();
        if (b && b.detail) msg = b.detail;
      } catch (_) {}
      throw new Error(msg);
    }
    sessionStorage.setItem("mc_token", token);
    $("#login-error").textContent = "";
    hideLogin();
    bootstrap();
  } catch (err) {
    $("#login-error").textContent = err.message || "sign in failed";
  }
});

/* ── router ──────────────────────────────────────────────────── */
function parseHash() {
  const h = location.hash.replace(/^#\/?/, "");
  const [path, query] = h.split("?");
  const params = new URLSearchParams(query || "");
  return { path: path || "overview", params };
}
function navigate(hash) { location.hash = hash; }

window.addEventListener("hashchange", render);
window.addEventListener("load", async () => {
  await initLogin();
  bootstrap();
});
async function bootstrap() {
  setNav();
  try {
    state.info = await api("/api/info").catch(() => null);
    await refreshOverview();
    startSSE();
    render();
  } catch (err) {
    console.error(err);
  }
}

function setNav() {
  const { path } = parseHash();
  document.querySelectorAll(".nav-link").forEach((a) => {
    a.classList.toggle("active", a.dataset.route === path);
  });
}

/* ── live updates (SSE) ──────────────────────────────────────── */
function startSSE() {
  if (state.sse) state.sse.close();
  // Same-origin EventSource: the session cookie (set at login) is sent
  // automatically. Never put the token in the URL — it would land in logs.
  const es = new EventSource("/api/stream");
  state.sse = es;
  es.addEventListener("refresh", (ev) => {
    try {
      state.overview = JSON.parse(ev.data);
      state.live = true;
      $("#live-pill").classList.add("pill-live");
      $("#live-pill").classList.remove("pill-off");
      $("#live-pill").textContent = "LIVE";
      updateGatewayPill();
      const { path } = parseHash();
      if (path === "overview") renderOverview();
      else if (path === "sessions") maybeRefreshSessions();
    } catch (_) {}
  });
  es.onerror = () => {
    state.live = false;
    $("#live-pill").classList.remove("pill-live");
    $("#live-pill").classList.add("pill-off");
    $("#live-pill").textContent = "LIVE…";
  };
}

function updateGatewayPill() {
  const pill = $("#gateway-pill");
  const ov = state.overview;
  if (!ov) return;
  const working = ov.status_counts?.working || 0;
  pill.className = "pill " + (working > 0 ? "pill-ok" : "pill-off");
  pill.textContent = working > 0 ? `${working} ACTIVE` : "GATEWAY OK";
  pill.title = `${working} session(s) working right now`;
}

async function refreshOverview() {
  state.overview = await api("/api/overview");
  updateGatewayPill();
  const errs = state.overview.db_errors || [];
  $("#db-errors").textContent = errs.length ? `DB errors: ${errs.join("; ")}` : "";
  $("#footer-info").textContent =
    `Hermes Mission Control · ${state.info?.version || ""} · poll ${state.info?.poll_seconds || 4}s · ` +
    `${(state.overview.stats?.sessions || 0)} sessions · ${(state.overview.stats?.agents || 0)} agents`;
}

/* ── view renderer ───────────────────────────────────────────── */
async function render() {
  setNav();
  const { path, params } = parseHash();
  const view = $("#view");
  view.innerHTML = "";
  try {
    if (path === "sessions") await renderSessions(view);
    else if (path.startsWith("session/")) await renderSessionDetail(view, params.get("id") || path.split("/")[1]);
    else if (path === "agents") await renderAgents(view);
    else if (path === "search") renderSearch(view);
    else await renderOverview(view);
  } catch (err) {
    view.append(el("div", { class: "empty" }, `Error: ${err.message}`));
  }
}

/* ── OVERVIEW ────────────────────────────────────────────────── */
async function renderOverview(view) {
  if (!state.overview) {
    view.append(el("div", { class: "loading" }, el("span", { class: "spinner" }), "loading…"));
    return;
  }
  const ov = state.overview;
  const st = ov.stats;
  const row = el("div", { class: "stats-row" });
  const card = (label, value, sub) => el("div", { class: "stat-card" },
    el("div", { class: "stat-label" }, label), el("div", { class: "stat-value" }, value),
    sub ? el("div", { class: "stat-sub" }, sub) : null);
  row.append(
    card("AGENTS", st.agents, `${(ov.source_counts?.telegram || 0)} telegram · ${(ov.source_counts?.cli || 0)} cli`),
    card("WORKING", st.active_sessions, `${st.open_sessions} open sessions`),
    card("SESSIONS", fmt(st.sessions), `${fmt(st.messages)} messages`),
    card("TOOL CALLS", fmt(st.tool_calls), `${fmt(ov.agents?.length || 0)} agents tracked`),
  );
  view.append(row);

  // status distribution mini-bar
  const statuses = ov.status_counts || {};
  const total = Object.values(statuses).reduce((a, b) => a + b, 0) || 1;
  const bar = el("div", { class: "panel" }, el("div", { class: "panel-head" }, "SESSION STATUS"));
  const body = el("div", { class: "panel-body" });
  const line = el("div", { style: "display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:10px" });
  const colors = { working: "var(--st-working)", waiting: "var(--st-waiting)", idle: "var(--st-idle)", done: "var(--st-done)", error: "var(--st-error)", unknown: "var(--st-unknown)" };
  for (const s of STATUS_ORDER) {
    if (statuses[s]) line.append(el("div", { style: `width:${(statuses[s] / total) * 100}%;background:${colors[s]}` }));
  }
  body.append(line);
  const legend = el("div", { style: "display:flex;flex-wrap:wrap;gap:8px 16px" });
  for (const s of STATUS_ORDER) {
    if (!statuses[s]) continue;
    legend.append(el("span", { class: "muted", style: "font-size:12px" }, dot(s), `${STATUS_LABEL[s]} ${statuses[s]}`));
  }
  body.append(legend);
  bar.append(body);
  view.append(bar);

  // active agents
  const activeAgents = (ov.agents || []).filter((a) => a.active_sessions > 0 || (a.last_activity_at && (Date.now() / 1000 - a.last_activity_at) < 600));
  const ap = el("div", { class: "panel" }, el("div", { class: "panel-head" }, "ACTIVE AGENTS"));
  const ab = el("div", { class: "panel-body" });
  if (activeAgents.length) {
    const list = el("div");
    for (const a of activeAgents) {
      list.append(el("div", { style: "display:flex;gap:12px;align-items:center;padding:6px 2px;cursor:pointer", onclick: () => navigate(`#/sessions?agent=${encodeURIComponent(a.name)}`) },
        a.active_sessions > 0 ? dot("working") : dot("idle"),
        el("span", { style: "font-weight:600;min-width:110px" }, esc(a.name)),
        sourceBadge(a.sources?.[0] || "—"),
        el("span", { class: "muted" }, esc(a.models?.[0] || "—")),
        el("span", { class: "timeago", style: "margin-left:auto" }, `${a.active_sessions} active · ${timeago(a.last_activity_at)}`)));
    }
    ab.append(list);
  } else {
    ab.append(el("div", { class: "empty", style: "padding:14px 0" }, "no agents currently active"));
  }
  ap.append(ab);
  view.append(ap);

  // recent activity
  const rp = el("div", { class: "panel" }, el("div", { class: "panel-head" }, "RECENT ACTIVITY"));
  const rb = el("div", { class: "panel-body" });
  const feed = el("ul", { class: "feed" });
  for (const s of ov.recent_activity || []) {
    const desc = s.last_activity_description || (s.status === "working" ? "working…" : s.status === "done" ? "completed" : "idle");
    const item = el("li", { onclick: () => navigate(`#/session/${encodeURIComponent(s.id)}`) },
      el("span", { class: "feed-time" }, clock(s.last_activity_at || s.started_at)),
      el("span", { class: "feed-agent" }, esc(s.agent)),
      el("span", { class: "feed-desc" },
        el("span", { class: "mono" }, esc(desc.split(":")[0] + ":")), " ",
        esc(desc.split(":").slice(1).join(":").slice(0, 140))),
      el("span", { class: "timeago", style: "margin-left:auto" }, timeago(s.last_activity_at || s.started_at)));
    feed.append(item);
  }
  rb.append(feed);
  rp.append(rb);
  view.append(rp);
}

/* ── SESSIONS ────────────────────────────────────────────────── */
let sessionsCache = null;
async function fetchSessions() {
  const f = state.filters;
  const p = new URLSearchParams();
  if (f.agent) p.set("agent", f.agent);
  if (f.source) p.set("source", f.source);
  if (f.model) p.set("model", f.model);
  if (f.status) p.set("status", f.status);
  if (f.q) p.set("q", f.q);
  if (f.active) p.set("active", f.active === "active" ? "true" : f.active === "done" ? "false" : "");
  p.set("limit", "500");
  return api(`/api/sessions?${p.toString()}`);
}
function maybeRefreshSessions() {
  if ($("#view").dataset.view !== "sessions") return;
  fetchSessions().then((d) => { sessionsCache = d; if ($("#view").dataset.view === "sessions") renderSessionsTable($("#view")); }).catch(() => {});
}

async function renderSessions(view) {
  view.dataset.view = "sessions";
  const { params } = parseHash();
  if (params.get("agent")) state.filters.agent = params.get("agent");

  // filter bar
  const ov = state.overview || {};
  const agents = (ov.agents || []).map((a) => a.name);
  const sources = Object.keys(ov.source_counts || {});
  const models = [...new Set((ov.agents || []).flatMap((a) => a.models || []))].sort();

  const bar = el("div", { class: "filterbar" });
  const sel = (label, key, options, allLabel) => {
    const wrap = el("div", { style: "display:flex;gap:6px;align-items:center" }, el("label", {}, label));
    const s = el("select", { onchange: (e) => { state.filters[key] = e.target.value; refreshSessionsView(); } },
      el("option", { value: "" }, allLabel));
    for (const o of options) s.append(el("option", { value: o }, o));
    if (state.filters[key]) s.value = state.filters[key];
    wrap.append(s);
    return wrap;
  };
  bar.append(sel("AGENT", "agent", agents, "all agents"));
  bar.append(sel("SOURCE", "source", sources, "all sources"));
  bar.append(sel("MODEL", "model", models, "all models"));
  bar.append(sel("STATUS", "status", STATUS_ORDER, "any status"));
  bar.append(sel("LIFE", "active", ["active", "done"], "all"));
  const q = el("input", { class: "search-input", placeholder: "filter by title / id / model…", value: state.filters.q || "",
    oninput: debounce((e) => { state.filters.q = e.target.value; refreshSessionsView(); }, 300) });
  bar.append(q);
  const clear = el("button", { class: "nav-link", onclick: () => { state.filters = { agent: "", source: "", model: "", status: "", q: "", active: "" }; location.hash = "#/sessions"; render(); } }, "clear");
  bar.append(clear);
  view.append(bar);

  if (!sessionsCache) sessionsCache = await fetchSessions();
  renderSessionsTable(view);
}

function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

function refreshSessionsView() {
  sessionsCache = null;
  fetchSessions().then((d) => { sessionsCache = d; renderSessionsTable($("#view")); }).catch(() => {});
}

function renderSessionsTable(view) {
  const existing = $("#sessions-panel");
  if (existing) existing.remove();
  const data = sessionsCache || { sessions: [], total: 0 };
  const panel = el("div", { id: "sessions-panel", class: "panel" });
  const head = el("div", { class: "panel-head" },
    `${fmt(data.total)} SESSIONS`, el("span", { class: "spacer" }),
    el("span", { class: "muted", style: "font-size:11px" }, state.live ? "live" : "snapshot"));
  panel.append(head);

  if (!data.sessions.length) {
    panel.append(el("div", { class: "empty" }, "no sessions match"));
    view.append(panel);
    return;
  }
  const table = el("table", { class: "grid" });
  const thead = el("thead", {}, el("tr", {},
    el("th", {}, "SOURCE"), el("th", {}, "AGENT"), el("th", {}, "MODEL"),
    el("th", {}, "STATUS"), el("th", {}, "TITLE"), el("th", {}, "LAST ACTIVE"),
    el("th", { class: "num" }, "MSGS"), el("th", { class: "num" }, "TOOLS")));
  table.append(thead);
  const tbody = el("tbody");
  for (const s of data.sessions) {
    const tr = el("tr", { onclick: () => navigate(`#/session/${encodeURIComponent(s.id)}`) },
      el("td", {}, sourceBadge(s.source)),
      el("td", {}, agentBadge(s.agent)),
      el("td", {}, modelBadge(s.model)),
      el("td", {}, statusBadge(s.status)),
      el("td", { style: "max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, esc(s.title || "(untitled)")),
      el("td", { class: "timeago" }, timeago(s.last_activity_at || s.started_at)),
      el("td", { class: "num muted" }, fmt(s.message_count)),
      el("td", { class: "num muted" }, fmt(s.tool_call_count)));
    tbody.append(tr);
  }
  table.append(tbody);
  panel.append(table);
  view.append(panel);
}

/* ── SESSION DETAIL ──────────────────────────────────────────── */
async function renderSessionDetail(view, id) {
  view.dataset.view = "detail";
  view.append(el("div", { class: "loading" }, el("span", { class: "spinner" }), "loading session…"));
  const d = await api(`/api/sessions/${encodeURIComponent(id)}`);
  view.innerHTML = "";

  const head = el("div", { class: "detail-head" },
    el("a", { href: "#/sessions", class: "nav-link", style: "padding:0 8px 0 0" }, "←"),
    el("h2", {}, esc(d.title || "(untitled)")),
    agentBadge(d.agent), sourceBadge(d.source), statusBadge(d.status), modelBadge(d.model));
  view.append(head);

  // metadata panel
  const meta = el("div", { class: "detail-meta panel", style: "padding:12px 14px" });
  const kv = (k, v) => el("div", {}, el("div", { class: "k" }, k), el("div", { class: "v" }, v));
  meta.append(kv("session id", esc(d.id)));
  meta.append(kv("profile", esc(d.profile || d.db || "main")));
  if (d.parent_session_id) meta.append(kv("parent session", esc(d.parent_session_id)));
  meta.append(kv("started", fulldate(d.started_at)));
  meta.append(kv("ended", d.ended_at ? fulldate(d.ended_at) : "—"));
  meta.append(kv("end reason", esc(d.end_reason || "—")));
  meta.append(kv("last activity", fulldate(d.last_activity_at)));
  meta.append(kv("last activity", esc(d.last_activity_description || "—")));
  meta.append(kv("messages", fmt(d.message_count)));
  meta.append(kv("tool calls", fmt(d.tool_call_count)));
  meta.append(kv("input tokens", fmt(d.tokens?.input)));
  meta.append(kv("output tokens", fmt(d.tokens?.output)));
  meta.append(kv("cache read/write", `${fmt(d.tokens?.cache_read)} / ${fmt(d.tokens?.cache_write)}`));
  meta.append(kv("reasoning tokens", fmt(d.tokens?.reasoning)));
  meta.append(kv("est. cost", d.estimated_cost_usd != null ? `$${Number(d.estimated_cost_usd).toFixed(4)}` : "—"));
  if (d.chat_type) meta.append(kv("chat", `${d.chat_type}${d.chat_id ? ` · ${d.chat_id}` : ""}${d.thread_id ? ` · thread ${d.thread_id}` : ""}`));
  if (d.cwd) meta.append(kv("cwd", esc(d.cwd)));
  if (d.git_branch) meta.append(kv("branch", esc(d.git_branch)));
  view.append(meta);

  // subagent tree
  if (d.children && d.children.length) {
    const tp = el("div", { class: "panel" }, el("div", { class: "panel-head" }, `SUBAGENTS (${d.children.length})`));
    const tb = el("div", { class: "panel-body" });
    const tree = el("div", { class: "tree" });
    const root = el("div", { class: "tree-root tree-node" },
      el("span", { class: "tag" }, "◆ "), esc(d.title || d.id),
      el("span", { class: "muted", style: "font-size:11px" }, ` (${esc(d.agent)})`));
    tree.append(root);
    for (const c of d.children) {
      tree.append(el("div", { class: "tree-node", style: "cursor:pointer", onclick: () => navigate(`#/session/${encodeURIComponent(c.id)}`) },
        el("span", { class: "tag" }, "└─ "), esc(c.title || c.id),
        el("span", { class: "muted", style: "font-size:11px" }, ` · ${esc(c.status)} · ${fmt(c.message_count)} msgs`)));
    }
    tb.append(tree);
    tp.append(tb);
    view.append(tp);
  }

  // conversation timeline
  const cp = el("div", { class: "panel" }, el("div", { class: "panel-head" }, `CONVERSATION (${(d.messages || []).length})`));
  const cb = el("div", { class: "panel-body" });
  const tl = el("div", { class: "timeline" });
  for (const m of d.messages || []) {
    tl.append(messageBlock(m));
  }
  if (!(d.messages || []).length) cb.append(el("div", { class: "empty" }, "no messages stored for this session"));
  cb.append(tl);
  cp.append(cb);
  view.append(cp);
}

function messageBlock(m) {
  const item = el("div", { class: `tl-item role-${m.role}` });
  if (m.role === "tool") {
    item.append(el("div", { class: "msg-block" },
      el("div", { class: "msg-head" }, el("span", { class: "role-label" }, "TOOL"),
        el("span", { class: "mono", style: "color:var(--accent)" }, esc(m.tool_name || "?")),
        el("span", { class: "timeago", style: "margin-left:auto" }, clock(m.timestamp))),
      el("div", { class: "msg-content muted" }, esc((m.content || "").slice(0, 400)))));
    return item;
  }
  const block = el("div", { class: "msg-block" });
  block.append(el("div", { class: "msg-head" },
    el("span", { class: "role-label" }, m.role.toUpperCase()),
    el("span", { class: "timeago", style: "margin-left:auto" }, clock(m.timestamp))));
  const content = m.content || "";
  if (content) block.append(el("div", { class: "msg-content" }, esc(content.slice(0, 6000))));
  // assistant tool calls (request side)
  if (m.role === "assistant" && m.tool_calls) {
    let calls = null;
    try { calls = JSON.parse(m.tool_calls); } catch (_) {}
    if (calls) {
      const arr = Array.isArray(calls) ? calls : [calls];
      for (const tc of arr) {
        const name = tc?.function?.name || tc?.name || "tool";
        const args = tc?.function?.arguments || tc?.arguments || "";
        const det = el("details", { class: "tool-call" },
          el("summary", {}, "⚙ ", esc(String(name)), el("span", { class: "tc-time" }, "tool call")),
          el("div", { class: "tc-body" },
            el("div", { class: "tc-label" }, "arguments"),
            el("pre", {}, esc(typeof args === "string" ? args : JSON.stringify(args, null, 2)))));
        block.append(det);
      }
    }
  }
  item.append(block);
  return item;
}

/* ── AGENTS ──────────────────────────────────────────────────── */
async function renderAgents(view) {
  view.append(el("div", { class: "loading" }, el("span", { class: "spinner" }), "loading…"));
  const { agents } = await api("/api/agents");
  view.innerHTML = "";
  const grid = el("div", { class: "agent-grid" });
  for (const a of agents) {
    const status = a.active_sessions > 0 ? "working" : (Date.now() / 1000 - (a.last_activity_at || 0)) < 600 ? "idle" : "done";
    grid.append(el("div", { class: "agent-card", onclick: () => navigate(`#/sessions?agent=${encodeURIComponent(a.name)}`) },
      el("h3", {}, dot(status), esc(a.name), el("span", { class: "spacer" }),
        el("span", { class: "badge" }, a.active_sessions > 0 ? `${a.active_sessions} ACTIVE` : "IDLE")),
      el("div", { class: "agent-meta" },
        el("span", {}, `model: ${esc((a.models || []).join(", ") || "—")}`),
        el("span", {}, `sources: ${esc((a.sources || []).join(", "))}`)),
      el("div", { class: "agent-stats" },
        el("div", {}, el("b", {}, fmt(a.total_sessions)), el("span", {}, "sessions")),
        el("div", {}, el("b", {}, fmt(a.total_tool_calls)), el("span", {}, "tool calls")),
        el("div", {}, el("b", {}, fmt(Math.round((a.total_tokens || 0) / 1000)) + "k"), el("span", {}, "tokens")),
        el("div", {}, el("b", {}, fmt(a.subagent_count)), el("span", {}, "subagents"))),
      el("div", { class: "agent-meta", style: "margin-top:8px" },
        el("span", {}, `last: ${timeago(a.last_activity_at)}`),
        a.last_activity_description ? el("span", { style: "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%" }, esc(a.last_activity_description)) : null)));
  }
  view.append(grid);
}

/* ── SEARCH ──────────────────────────────────────────────────── */
function renderSearch(view) {
  const hero = el("div", { class: "search-hero" });
  const input = el("input", { placeholder: "search sessions, messages, tool calls…", autofocus: "",
    onkeydown: (e) => { if (e.key === "Enter") doSearch(input.value); } });
  hero.append(input);
  hero.append(el("button", { class: "nav-link", style: "border:1px solid var(--border)", onclick: () => doSearch(input.value) }, "search"));
  view.append(hero);
  const results = el("div", { id: "search-results" });
  view.append(results);
  const { params } = parseHash();
  if (params.get("q")) { input.value = params.get("q"); doSearch(params.get("q")); }
}

async function doSearch(q) {
  q = (q || "").trim();
  if (!q) return;
  navigate(`#/search?q=${encodeURIComponent(q)}`);
  const out = $("#search-results");
  out.innerHTML = "";
  out.append(el("div", { class: "loading" }, el("span", { class: "spinner" }), `searching “${esc(q)}”…`));
  let res;
  try { res = await api(`/api/search?q=${encodeURIComponent(q)}&limit=50`); }
  catch (err) { out.append(el("div", { class: "empty" }, `search failed: ${err.message}`)); return; }

  const msgs = res.messages || [];
  const sess = res.sessions || [];
  if (!msgs.length && !sess.length) {
    out.append(el("div", { class: "empty" }, `no results for “${esc(q)}”`));
    return;
  }
  if (sess.length) {
    out.append(el("div", { class: "search-group-title" }, `SESSIONS (${sess.length})`));
    for (const s of sess) {
      out.append(el("div", { class: "result-row", onclick: () => navigate(`#/session/${encodeURIComponent(s.id)}`) },
        sourceBadge(s.source), agentBadge(s.agent), statusBadge(s.status),
        el("span", { class: "result-snippet" }, esc(s.title || s.id)),
        el("span", { class: "timeago" }, timeago(s.started_at))));
    }
  }
  if (msgs.length) {
    out.append(el("div", { class: "search-group-title" }, `MESSAGES (${msgs.length})`));
    for (const m of msgs) {
      out.append(el("div", { class: "result-row", onclick: () => navigate(`#/session/${encodeURIComponent(m.session_id)}`) },
        sourceBadge("msg"), agentBadge(m.agent || "main"),
        el("span", { class: "result-snippet" }, esc((m.snippet || "").replace(/[\[\]]/g, "").slice(0, 180))),
        el("span", { class: "timeago" }, timeago(m.timestamp))));
    }
  }
}

/* ── init ────────────────────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", () => {
  // kick off login/bootstrap on load
});
