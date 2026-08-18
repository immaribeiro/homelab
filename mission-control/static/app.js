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
    if (typeof c === "string") node.appendChild(document.createTextNode(c));
    else if (c instanceof Node) node.appendChild(c);
    else node.appendChild(document.createTextNode(String(c))); // numbers, booleans
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
  filters: { agent: "", source: "", model: "", status: "", sort: "last_activity", include_archived: true, q: "", active: "" },
  sse: null,
  live: false,
  page: 0,
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
  const b = el("span", { class: `badge badge-source-${source || "unknown"}` }, (source || "unknown").toUpperCase());
  // Click any source badge to drill into that source's sessions.
  b.style.cursor = "pointer";
  b.addEventListener("click", (e) => {
    e.stopPropagation();
    navigate(`#/source/${encodeURIComponent(source || "unknown")}`);
  });
  return b;
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

// "/" jumps to global search from anywhere
document.addEventListener("keydown", (e) => {
  const tag = (document.activeElement || {}).tagName;
  if (e.key === "/" && !e.metaKey && !e.ctrlKey && !e.altKey &&
      tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
    e.preventDefault();
    navigate("#/search");
    const inp = document.getElementById("search-page-input");
    if (inp) setTimeout(() => inp.focus(), 60);
  }
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
  const hanging = ov.stats?.hanging || 0;
  const chip = $("#hanging-chip");
  if (chip) chip.textContent = `⚠ ${hanging} hanging`;
}

function toast(message, error = false) {
  let host = $("#toast-host");
  if (!host) { host = el("div", { id: "toast-host", class: "toast-host" }); document.body.append(host); }
  const item = el("div", { class: `toast${error ? " toast-error" : ""}` }, message);
  host.append(item);
  setTimeout(() => item.remove(), 3200);
}

async function mutate(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
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
    else if (path.startsWith("agent/")) await renderAgentPage(view, params.get("name") || path.split("/")[1]);
    else if (path.startsWith("source/")) await renderSourcePage(view, params.get("source") || path.split("/")[1]);
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

  // model usage rollup
  const ms = ov.model_stats || [];
  if (ms.length) {
    const mp = el("div", { class: "panel" }, el("div", { class: "panel-head" }, "MODEL USAGE"));
    const mbody = el("div", { class: "panel-body" });
    const maxTok = Math.max(...ms.map((m) => m.tokens), 1);
    for (const m of ms) {
      const right = `${m.sessions} sess · ${fmt(Math.round(m.tokens / 1000))}k tok` +
        (m.estimated_cost_usd > 0 ? ` · $${Number(m.estimated_cost_usd).toFixed(2)}` : "");
      const row = el("div", { style: "display:flex;align-items:center;gap:10px;padding:5px 0" });
      row.append(el("span", { class: "badge badge-model", style: "min-width:200px" }, esc(m.model)));
      const wrap = el("div", { style: "flex:1;height:12px;background:var(--bg-2);border-radius:4px;overflow:hidden" });
      wrap.append(el("div", { style: `width:${Math.max(2, (m.tokens / maxTok) * 100)}%;height:100%;background:var(--accent-dim);border-radius:4px` }));
      row.append(wrap, el("span", { class: "muted", style: "font-size:11px;min-width:150px;text-align:right" }, right));
      mbody.append(row);
    }
    mp.append(mbody);
    view.append(mp);
  }

  // activity trend (14 days)
  const tr = await api("/api/trends?days=14").catch(() => null);
  if (tr && tr.points && tr.points.some((p) => p.sessions)) {
    const maxS = Math.max(...tr.points.map((p) => p.sessions), 1);
    const maxC = Math.max(...tr.points.map((p) => p.cost_usd), 0.01);
    const tp = el("div", { class: "panel" }, el("div", { class: "panel-head" }, "ACTIVITY (14 DAYS)"));
    const tb2 = el("div", { class: "panel-body" });
    const row = (key, max, color, titleFn) => {
      const r = el("div", { style: "display:flex;align-items:flex-end;gap:4px;height:56px;padding:2px 0" });
      for (const p of tr.points) {
        const v = p[key] || 0;
        const h = v ? Math.max(3, Math.round((v / max) * 46)) : 1;
        r.append(el("div", { style: "flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:2px", title: titleFn(p) },
          el("div", { style: `width:72%;height:${h}px;background:${color};border-radius:3px;opacity:${v ? 1 : 0.25}` }),
          el("div", { class: "muted", style: "font-size:8.5px" }, p.date.slice(8))));
      }
      return r;
    };
    tb2.append(el("div", { class: "muted", style: "font-size:10.5px;margin:2px 0" }, "sessions / day"));
    tb2.append(row("sessions", maxS, "var(--accent)",
      (p) => `${p.date}: ${p.sessions} sessions · ${fmt(p.messages)} msgs · ${fmt(p.tool_calls)} tool calls`));
    tb2.append(el("div", { class: "muted", style: "font-size:10.5px;margin:6px 0 2px" }, "est. cost / day"));
    tb2.append(row("cost_usd", maxC, "var(--warn)", (p) => `${p.date}: $${p.cost_usd.toFixed(2)}`));
    tp.append(tb2);
    view.append(tp);
  }

  // active agents
  const activeAgents = (ov.agents || []).filter((a) => a.active_sessions > 0 || (a.last_activity_at && (Date.now() / 1000 - a.last_activity_at) < 600));
  const ap = el("div", { class: "panel" }, el("div", { class: "panel-head" }, "ACTIVE AGENTS",
    el("span", { class: "spacer" }),
    el("span", { class: "muted", style: "font-size:10.5px;font-weight:400" }, "🟢 = live gateway turn (working)")));
  const ab = el("div", { class: "panel-body" });
  if (activeAgents.length) {
    const list = el("div");
    for (const a of activeAgents) {
      const working = a.active_sessions > 0;
      list.append(el("div", { style: "display:flex;gap:12px;align-items:center;padding:6px 2px;cursor:pointer", onclick: () => navigate(`#/sessions?agent=${encodeURIComponent(a.name)}`) },
        working ? dot("working") : dot("idle"),
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

/* ── AGENT / SOURCE PAGES (drill-down) ───────────────────────────────── */
async function renderFilteredPage(view, title, params) {
  view.dataset.view = "sessions";
  view.append(el("div", { class: "loading" }, el("span", { class: "spinner" }), `loading ${esc(title)}…`));
  const data = await api(`/api/sessions?${params}&limit=500`).catch(() => null);
  view.innerHTML = "";
  if (!data) {
    view.append(el("div", { class: "empty" }, "not found"));
    return;
  }
  const head = el("div", { class: "detail-head" },
    el("a", { href: "#/sessions", class: "nav-link", style: "padding:0 8px 0 0" }, "←"),
    el("h2", {}, dot("idle"), esc(title)),
    el("span", { class: "badge" }, `${data.total} SESSIONS`));
  view.append(head);

  const panel = el("div", { class: "panel" });
  const table = el("table", { class: "grid" });
  table.append(el("thead", {}, el("tr", {},
    el("th", {}, "SOURCE"), el("th", {}, "MODEL"), el("th", {}, "STATUS"),
    el("th", {}, "TITLE"), el("th", {}, "LAST ACTIVE"),
    el("th", { class: "num" }, "MSGS"), el("th", { class: "num" }, "TOOLS"))));
  const tbody = el("tbody");
  for (const s of data.sessions) {
    tbody.append(el("tr", { onclick: () => navigate(`#/session/${encodeURIComponent(s.id)}`) },
      el("td", {}, sourceBadge(s.source)),
      el("td", {}, modelBadge(s.model)),
      el("td", {}, statusBadge(s.status)),
      el("td", { style: "max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, esc(s.title || "(untitled)")),
      el("td", { class: "timeago" }, timeago(s.last_activity_at || s.started_at)),
      el("td", { class: "num muted" }, fmt(s.message_count)),
      el("td", { class: "num muted" }, fmt(s.tool_call_count))));
  }
  table.append(tbody);
  panel.append(table);
  view.append(panel);
  if (!data.sessions.length) view.append(el("div", { class: "empty" }, "no sessions"));
}

async function renderAgentPage(view, name) {
  return renderFilteredPage(view, name, `agent=${encodeURIComponent(name)}`);
}
async function renderSourcePage(view, source) {
  return renderFilteredPage(view, source, `source=${encodeURIComponent(source)}`);
}

/* ── SESSIONS ────────────────────────────────────────────────────────── */
let sessionsCache = null;
async function fetchSessions() {
  const f = state.filters;
  const p = new URLSearchParams();
  if (f.agent) p.set("agent", f.agent);
  if (f.source) p.set("source", f.source);
  if (f.model) p.set("model", f.model);
  if (f.status) p.set("status", f.status);
  if (f.sort) p.set("sort", f.sort);
  p.set("include_archived", String(f.include_archived));
  if (f.q) p.set("q", f.q);
  if (f.active) p.set("active", f.active === "active" ? "true" : f.active === "done" ? "false" : "");
  p.set("limit", "200");
  p.set("offset", String(state.page * 200));
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
  if (params.get("status")) state.filters.status = params.get("status");

  // filter bar
  const ov = state.overview || {};
  const agents = (ov.agents || []).map((a) => a.name);
  const sources = Object.keys(ov.source_counts || {});
  const models = [...new Set((ov.agents || []).flatMap((a) => a.models || []))].sort();

  const bar = el("div", { class: "filterbar" });
  const sel = (label, key, options, allLabel) => {
    const wrap = el("div", { style: "display:flex;gap:6px;align-items:center" }, el("label", {}, label));
    const s = el("select", { onchange: (e) => { state.filters[key] = e.target.value; state.page = 0; refreshSessionsView(); } },
      el("option", { value: "" }, allLabel));
    for (const o of options) s.append(el("option", { value: o }, o));
    if (state.filters[key]) s.value = state.filters[key];
    wrap.append(s);
    return wrap;
  };
  bar.append(sel("AGENT", "agent", agents, "all agents"));
  bar.append(sel("SOURCE", "source", sources, "all sources"));
  bar.append(sel("MODEL", "model", models, "all models"));
  bar.append(sel("STATUS", "status", [...STATUS_ORDER, "hanging"], "any status"));
  bar.append(sel("SORT", "sort", ["last_activity", "started", "messages", "cost"], "last activity"));
  const archived = el("label", { class: "archive-toggle" },
    el("input", { type: "checkbox", checked: state.filters.include_archived ? "checked" : null,
      onchange: (e) => { state.filters.include_archived = e.target.checked; state.page = 0; refreshSessionsView(); } }),
    " include archived");
  bar.append(archived);
  bar.append(sel("LIFE", "active", ["active", "done"], "all"));
  const q = el("input", { class: "search-input", placeholder: "filter by title / id / model…", value: state.filters.q || "",
    oninput: debounce((e) => { state.filters.q = e.target.value; refreshSessionsView(); }, 300) });
  bar.append(q);
  bar.append(el("button", { class: "nav-link", onclick: () => { state.page = 0; sessionsCache = null; refreshSessionsView(); } }, "↻ refresh"));
  const clear = el("button", { class: "nav-link", onclick: () => { state.filters = { agent: "", source: "", model: "", status: "", sort: "last_activity", include_archived: true, q: "", active: "" }; state.page = 0; location.hash = "#/sessions"; render(); } }, "clear");
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

function sessionActions(s) {
  const actions = el("div", { class: "row-actions" });
  const archive = el("button", { class: "row-action", onclick: async (e) => {
    e.stopPropagation();
    try { await mutate(`/api/sessions/${encodeURIComponent(s.id)}/archive`, { archived: !s.archived }); s.archived = !s.archived; toast(`${s.archived ? "Archived" : "Restored"} ${s.title || s.id}`); renderSessionsTable($("#view")); refreshOverview(); }
    catch (err) { toast(`Archive failed: ${err.message}`, true); }
  } }, s.archived ? "Unarchive" : "Archive");
  const exportLink = el("a", { class: "row-action", href: `/api/sessions/${encodeURIComponent(s.id)}/export?format=md`, target: "_blank", rel: "noopener noreferrer", onclick: (e) => e.stopPropagation() }, "Export");
  const copy = el("button", { class: "row-action", onclick: async (e) => { e.stopPropagation(); try { await navigator.clipboard.writeText(s.id); toast("Copied session ID"); } catch (_) { toast("Copy failed", true); } } }, "Copy ID");
  actions.append(archive, exportLink, copy);
  return actions;
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
    el("th", { class: "num" }, "MSGS"), el("th", { class: "num" }, "TOOLS"), el("th", {}, "ACTIONS")));
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
      el("td", { class: "num muted" }, fmt(s.tool_call_count)),
      el("td", {}, sessionActions(s)));
    tbody.append(tr);
  }
  table.append(tbody);
  panel.append(table);
  view.append(panel);
  if (data.total > 200) {
    const pages = Math.ceil(data.total / 200);
    const pager = el("div", { class: "pager" },
      el("button", { class: "nav-link", disabled: state.page === 0 ? "disabled" : null, onclick: () => { state.page--; refreshSessionsView(); } }, "← prev"),
      el("span", { class: "muted" }, `Page ${state.page + 1} of ${pages}`),
      el("button", { class: "nav-link", disabled: state.page >= pages - 1 ? "disabled" : null, onclick: () => { state.page++; refreshSessionsView(); } }, "next →"));
    view.append(pager);
  }
}

/* ── SESSION DETAIL ──────────────────────────────────────────── */
/* ── session detail helpers ──────────────────────────────────────────── */
const STATUS_HEX = {
  working: "#3ddc84", waiting: "#f5b841", idle: "#6ea8fe",
  done: "#9aa4b8", error: "#ff5c5c", unknown: "#565f73",
};
const SVG_NS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs = {}) {
  const n = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
  return n;
}

async function fetchSubagentGraph(rootId) {
  /* Recursive parent→child walk (depth ≤ 3, ≤ 40 nodes). */
  const nodes = [];
  const seen = new Set();
  async function walk(id, depth, parent) {
    if (depth > 3 || nodes.length >= 40 || seen.has(id)) return;
    seen.add(id);
    const d = await api(`/api/sessions/${encodeURIComponent(id)}?include_messages=false`).catch(() => null);
    if (!d) return;
    nodes.push({ id: d.id, title: d.title || d.id, agent: d.agent, status: d.status, depth, parent, msgs: d.message_count });
    for (const c of d.children || []) await walk(c.id, depth + 1, id);
  }
  await walk(rootId, 0, null);
  return nodes;
}

function renderSvgGraph(container, nodes) {
  if (!nodes.length) { container.append(el("div", { class: "empty" }, "no subagent data")); return; }
  const childrenOf = {};
  for (const n of nodes) (childrenOf[n.parent] = childrenOf[n.parent] || []).push(n);
  const pos = {};
  let slot = 0;
  (function dfs(n) {
    const kids = childrenOf[n.id] || [];
    if (!kids.length) { pos[n.id] = { x: n.depth, y: slot++ }; return; }
    kids.forEach(dfs);
    const ys = kids.map((k) => pos[k.id].y);
    pos[n.id] = { x: n.depth, y: (Math.min(...ys) + Math.max(...ys)) / 2 };
  })(nodes.find((n) => n.parent === null) || nodes[0]);

  const colW = 200, rowH = 46, pad = 14;
  const maxDepth = Math.max(...nodes.map((n) => n.depth));
  const width = maxDepth * colW + colW + 60;
  const height = slot * rowH + 60;
  const svg = svgEl("svg", { width, height, viewBox: `0 0 ${width} ${height}` });

  // edges
  for (const n of nodes) {
    if (n.parent === null) continue;
    const p = pos[n.parent], c = pos[n.id];
    const x1 = p.x * colW + colW - 8, y1 = p.y * rowH + 28;
    const x2 = c.x * colW + 10, y2 = c.y * rowH + 28;
    svg.append(svgEl("line", { x1, y1, x2, y2, stroke: "#232a3a", "stroke-width": 1.5 }));
  }
  // nodes
  for (const n of nodes) {
    const p = pos[n.id];
    const x = p.x * colW + 10, y = p.y * rowH + 8;
    const w = colW - 20, h = 40;
    const hex = STATUS_HEX[n.status] || STATUS_HEX.unknown;
    const g = svgEl("g", { transform: `translate(${x},${y})`, style: "cursor:pointer" });
    g.addEventListener("click", () => navigate(`#/session/${encodeURIComponent(n.id)}`));
    g.append(svgEl("rect", { width: w, height: h, rx: 6, fill: hex + "1f", stroke: hex, "stroke-width": 1.2 }));
    const title = (n.title || n.id).length > 22 ? (n.title || n.id).slice(0, 21) + "…" : (n.title || n.id);
    const t1 = svgEl("text", { x: 8, y: 18, fill: "#e8ecf4", "font-size": 11, "font-family": "inherit" });
    t1.textContent = title;
    const t2 = svgEl("text", { x: 8, y: 32, fill: "#6b7590", "font-size": 9.5, "font-family": "inherit" });
    t2.textContent = `${n.agent} · ${n.status} · ${n.msgs} msgs`;
    g.append(t1, t2);
    svg.append(g);
  }
  container.append(svg);
}

function showDeleteModal(d) {
  const modal = el("div", { class: "modal-backdrop" });
  const input = el("input", { class: "modal-input", placeholder: "type session ID to confirm" });
  const close = () => modal.remove();
  const del = el("button", { class: "danger-button", disabled: "disabled", onclick: async () => {
    try { await mutate(`/api/sessions/${encodeURIComponent(d.id)}/delete`, { confirm: d.id }); close(); sessionsCache = null; toast(`Deleted ${d.title || d.id}`); navigate("#/sessions"); refreshOverview(); }
    catch (err) { toast(`Delete failed: ${err.message}`, true); }
  } }, "Delete permanently");
  input.addEventListener("input", () => { del.disabled = input.value !== d.id; });
  modal.append(el("div", { class: "modal-card" }, el("h3", {}, "Delete session?"),
    el("p", {}, "This permanently removes ", el("strong", {}, d.title || "(untitled)"), " and all messages."),
    el("p", { class: "muted mono" }, d.id), input,
    el("div", { class: "modal-actions" }, el("button", { class: "nav-link", onclick: close }, "Cancel"), del)));
  document.body.append(modal);
  input.focus();
}

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
  const detailActions = el("div", { class: "detail-actions" });
  const archiveBtn = el("button", { class: "nav-link", onclick: async () => {
    try { await mutate(`/api/sessions/${encodeURIComponent(id)}/archive`, { archived: !d.archived }); d.archived = !d.archived; archiveBtn.textContent = d.archived ? "Unarchive" : "Archive"; toast(`${d.archived ? "Archived" : "Restored"} ${d.title || id}`); refreshOverview(); }
    catch (err) { toast(`Archive failed: ${err.message}`, true); }
  } }, d.archived ? "Unarchive" : "Archive");
  const deleteBtn = el("button", { class: "danger-button", onclick: () => showDeleteModal(d) }, "Delete session");
  detailActions.append(archiveBtn, deleteBtn);
  view.append(detailActions);

  // export links (JSON / MD)
  const exp = el("div", { class: "detail-head" },
    el("a", { href: `/api/sessions/${encodeURIComponent(id)}/export?format=json`, class: "nav-link", style: "padding:0 8px 4px;opacity:0.7" }, "JSON"),
    el("a", { href: `/api/sessions/${encodeURIComponent(id)}/export?format=md`, class: "nav-link", style: "padding:0 8px 4px;opacity:0.7" }, "MD"));
  view.append(exp);

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
  meta.append(el("div", { class: "kv" },
    el("div", { class: "k" }, "DASHBOARD"),
    el("div", { class: "v" }, el("a", { href: `https://hermes.immas.org/chat?resume=${encodeURIComponent(d.id)}`, target: "_blank", rel: "noopener noreferrer" }, "open in Hermes dashboard ↗"))));
  view.append(meta);

  // subagent graph (recursive, SVG, status-colored, clickable)
  if (d.children && d.children.length) {
    const tp = el("div", { class: "panel" },
      el("div", { class: "panel-head" }, `SUBAGENT GRAPH (${d.children.length} direct)`));
    const tb = el("div", { class: "panel-body", style: "overflow-x:auto" });
    const graph = el("div");
    tb.append(graph);
    tp.append(tb);
    view.append(tp);
    fetchSubagentGraph(d.id).then((nodes) => renderSvgGraph(graph, nodes));
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
  // assistant reasoning (thinking trace) — collapsible
  if (m.role === "assistant" && m.reasoning) {
    block.append(el("details", { class: "tool-call" },
      el("summary", {}, "🧠 ", "reasoning", el("span", { class: "tc-time" }, "thinking")),
      el("div", { class: "tc-body" }, el("pre", {}, esc(String(m.reasoning).slice(0, 4000))))));
  }
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

  // Sort: active agents first (by active_sessions desc), then by last_activity_at desc
  const now = Date.now() / 1000;
  agents.forEach((a) => {
    const age = a.last_activity_at ? now - a.last_activity_at : Infinity;
    a._sortKey = { active: a.active_sessions > 0, age };
  });
  agents.sort((x, y) => {
    if (x._sortKey.active !== y._sortKey.active) return x._sortKey.active ? -1 : 1;
    return x._sortKey.age - y._sortKey.age;
  });

  // Find max tokens for token bar scaling
  const maxTokens = Math.max(...agents.map((a) => a.total_tokens || 0), 1);

  // Empty state
  if (!agents.length) {
    view.append(el("div", { class: "empty" }, "no agents configured"));
    return;
  }

  const grid = el("div", { class: "agent-grid" });

  for (const a of agents) {
    const status = a.active_sessions > 0 ? "working" : (now - (a.last_activity_at || 0)) < 600 ? "idle" : "done";
    const is_active = a.active_sessions > 0;

    // Token bar data (guard against missing/NaN)
    const token_pct = ((a.total_tokens || 0) / maxTokens) * 100;

    // Build stats cells
    const stat_cells = [];
    if (a.active_sessions > 0) stat_cells.push(el("span", { class: "stat-cell" }, el("b", {}, fmt(a.active_sessions)), el("span", { class: "stat-label" }, "active")));
    if (a.total_sessions > 0) stat_cells.push(el("span", { class: "stat-cell" }, el("b", {}, fmt(a.total_sessions)), el("span", { class: "stat-label" }, "total")));
    stat_cells.push(el("span", { class: "stat-cell" }, el("b", {}, fmt(a.total_tool_calls)), el("span", { class: "stat-label" }, "tools")));
    stat_cells.push(el("span", { class: "stat-cell" }, el("b", {}, fmt(a.total_tokens)), el("span", { class: "stat-label" }, "tokens")));
    if (a.estimated_cost_usd > 0) stat_cells.push(el("span", { class: "stat-cell" }, el("b", {}, `$${Number(a.estimated_cost_usd).toFixed(2)}`), el("span", { class: "stat-label" }, "cost")));

    const card = el("div", {
      class: `agent-card${is_active ? " active" : ""}`,
      onclick: () => navigate(`#/sessions?agent=${encodeURIComponent(a.name)}`),
    });

    // Header: status dot + name + badge
    card.append(
      el("div", { class: "agent-header" },
        dot(status),
        el("span", { class: "agent-name", style: "font-weight:600;font-size:15px" }, a.name),
        el("span", { class: `badge badge-agent-${is_active ? "active" : "idle"}` }, is_active ? `${a.active_sessions} ACTIVE` : "IDLE")
      )
    );

    // Model + source badges
    card.append(
      el("div", { class: "agent-models" },
        ...a.models.map((m) => modelBadge(m))),
      el("div", { class: "agent-sources" },
        ...a.sources.map((s) => sourceBadge(s)))
    );

    // Token usage mini bar
    card.append(
      el("div", { class: "token-bar", title: `${a.total_tokens.toLocaleString()} tokens` },
        el("div", { class: "token-fill", style: `width:${Math.max(1, token_pct)}%;background:var(--accent)` })
      )
    );

    // Stats row
    card.append(el("div", { class: "agent-stats" }, ...stat_cells));

    // Footer: last activity
    const desc = a.last_activity_description ? (a.last_activity_description.length > 40 ? a.last_activity_description.slice(0, 37) + "…" : a.last_activity_description) : "";
    card.append(
      el("div", { class: "agent-footer" },
        el("span", { class: "timeago" }, timeago(a.last_activity_at)),
        el("span", { class: "agent-desc" }, desc)
      )
    );

    grid.append(card);
  }

  view.append(grid);
}

/* ── SEARCH ──────────────────────────────────────────────────── */
function renderSearch(view) {
  const hero = el("div", { class: "search-hero" });
  const input = el("input", { id: "search-page-input", placeholder: "search sessions, messages, tool calls…", autofocus: "",
    onkeydown: (e) => { if (e.key === "Enter") doSearch(input.value); } });
  hero.append(input);
  hero.append(el("button", { class: "nav-link", style: "border:1px solid var(--border)", onclick: () => doSearch(input.value) }, "search"));
  view.append(hero);
  const results = el("div", { id: "search-results" });
  view.append(results);
  const { params } = parseHash();
  if (params.get("q")) { input.value = params.get("q"); doSearch(params.get("q")); }
}

function highlightText(container, text, term) {
  /* Highlight term matches with <mark> nodes (XSS-safe: text nodes only). */
  const t = (term || "").toLowerCase();
  if (!t) { container.append(document.createTextNode(text)); return; }
  const lower = text.toLowerCase();
  let i = 0, idx;
  while ((idx = lower.indexOf(t, i)) !== -1) {
    if (idx > i) container.append(document.createTextNode(text.slice(i, idx)));
    const mark = document.createElement("mark");
    mark.textContent = text.slice(idx, idx + t.length);
    container.append(mark);
    i = idx + t.length;
  }
  if (i < text.length) container.append(document.createTextNode(text.slice(i)));
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
      const snippet = el("span", { class: "result-snippet" });
      highlightText(snippet, (m.snippet || "").replace(/[\[\]]/g, "").slice(0, 220), q);
      out.append(el("div", { class: "result-row", onclick: () => navigate(`#/session/${encodeURIComponent(m.session_id)}`) },
        sourceBadge("msg"), agentBadge(m.agent || "main"),
        snippet,
        el("span", { class: "timeago" }, timeago(m.timestamp))));
    }
  }
}

/* ── init ────────────────────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", () => {
  // kick off login/bootstrap on load
});
