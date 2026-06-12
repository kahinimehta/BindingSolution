/* BindingSolution frontend — vanilla JS SPA, no build step.
   Views: Library · Connections · Strategies · Project specs.
   Long tasks run as server jobs; we poll /api/jobs/{id} for live progress. */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ── API ──────────────────────────────────────────────────────── */
const api = {
  async get(path) { return this._req("GET", path); },
  async post(path, body) { return this._req("POST", path, body); },
  async del(path) { return this._req("DELETE", path); },
  async _req(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    const res = await fetch(`/api${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `${res.status} ${res.statusText}`);
    return data;
  },
  async upload(formData) {
    const res = await fetch("/api/specs", { method: "POST", body: formData });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    return data;
  },
};

/* ── job polling ──────────────────────────────────────────────── */
function runJob(startResponse, { onProgress } = {}) {
  const jobId = startResponse.job_id;
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const job = await api.get(`/jobs/${jobId}`);
        if (onProgress) onProgress(job.progress, job);
        if (job.status === "done") return resolve(job.result);
        if (job.status === "error") return reject(new Error(job.error || "Job failed"));
        setTimeout(tick, 650);
      } catch (e) { reject(e); }
    };
    tick();
  });
}

/* ── toasts ───────────────────────────────────────────────────── */
function toast(msg, kind = "") {
  const node = el("div", { class: `toast ${kind}` }, msg);
  $("#toasts").append(node);
  setTimeout(() => { node.style.transition = "opacity .3s, transform .3s"; node.style.opacity = "0"; node.style.transform = "translateX(20px)"; setTimeout(() => node.remove(), 300); }, 4200);
}

/* ── modal ────────────────────────────────────────────────────── */
let _scrollLock = 0;

function lockScroll() {
  if (_scrollLock++ === 0) {
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
  }
}

function unlockScroll() {
  if (--_scrollLock <= 0) {
    _scrollLock = 0;
    document.documentElement.style.overflow = "";
    document.body.style.overflow = "";
  }
}

function buildModalNode(title, bodyNode, size = "dialog") {
  return el("div", { class: `modal modal-${size}` },
    el("div", { class: "modal-head" },
      el("h2", {}, title),
      el("button", { type: "button", class: "modal-x", onclick: closeModal, "aria-label": "Close" }, "✕")),
    el("div", { class: "modal-body" }, bodyNode));
}

function openModal(title, bodyNode, size = "dialog") {
  const host = $("#modal-host");
  host.hidden = false;
  host.replaceChildren(buildModalNode(title, bodyNode, size));
  host.onclick = (e) => { if (e.target === host) closeModal(); };
  lockScroll();
}

function setModal(title, bodyNode, size = "dialog") {
  const host = $("#modal-host");
  if (host.hidden) {
    openModal(title, bodyNode, size);
    return;
  }
  const modal = $(".modal", host);
  if (modal) modal.className = `modal modal-${size}`;
  const heading = $(".modal-head h2", host);
  if (heading) heading.textContent = title;
  const body = $(".modal-body", host);
  if (body) body.replaceChildren(bodyNode);
}

function closeModal() {
  const host = $("#modal-host");
  if (host.hidden) return;
  host.hidden = true;
  host.replaceChildren();
  host.onclick = null;
  unlockScroll();
}

function showProgressModal(title, message) {
  const bar = progressBlock(message);
  const box = el("div", { class: "modal-progress" }, bar.node);
  box._update = bar.update;
  setModal(title, box, "dialog");
  return box;
}

document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

/* ── global state ─────────────────────────────────────────────── */
const state = { status: null, projects: [], busy: false };
const fmtTime = (t) => t ? new Date(t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
const fmtReadMinutes = (m) => {
  if (!m) return "";
  if (m < 60) return `${m} min`;
  const h = m / 60;
  return Number.isInteger(h) ? `${h} h` : `${h.toFixed(1)} h`;
};
const planScheduleLabel = (plan) => {
  const s = plan?.schedule;
  if (!s?.total_minutes) return "";
  return `${fmtReadMinutes(s.total_minutes)} · ${s.estimated_days} day${s.estimated_days === 1 ? "" : "s"}`;
};
const isUsable = (p) => p.usable !== false;
const usableProjects = () => state.projects.filter(isUsable);
const inactiveProjects = () => state.projects.filter((p) => !isUsable(p));

/* ── status / sidebar ─────────────────────────────────────────── */
async function refreshStatus() {
  try {
    state.status = await api.get("/status");
    renderStatusChips();
    setCount("projects", state.status.library.num_usable_projects ?? state.status.library.num_projects);
    updatePurgeButton();
  } catch (e) { /* server not up yet */ }
}

function updatePurgeButton() {
  const btn = $("#purge-btn");
  if (!btn) return;
  const n = state.status?.library?.num_projects ?? state.projects.length;
  btn.classList.toggle("hidden", !n);
}
function setCount(name, n) {
  const node = $(`.nav-count[data-count="${name}"]`);
  if (node) node.textContent = n ? String(n) : "";
}
function renderStatusChips() {
  const s = state.status; if (!s) return;
  const chips = [];
  if (s.using_mock_llm) chips.push(chip("Demo AI", "warn", "No Claude key — heuristic mode"));
  else chips.push(chip(s.anthropic_model.replace("claude-", "").replace(/-/g, " "), "ok", "Claude connected"));
  if (s.zotero_mode) chips.push(chip(`Zotero · ${s.zotero_mode}`, "ok"));
  else chips.push(chip("No Zotero", "warn", "Use the demo library"));
  $("#status-chips").replaceChildren(...chips);
}
function chip(label, kind = "", title = "") {
  return el("span", { class: `chip ${kind}`, title }, el("span", { class: "dot" }), label);
}

/* ── sync ─────────────────────────────────────────────────────── */
async function doSync(source) {
  const btn = $("#sync-btn");
  btn.classList.add("busy"); btn.disabled = true;
  $(".sync-label", btn).textContent = source === "demo" ? "Loading demo…" : "Syncing…";
  try {
    const start = await api.post("/library/sync", { source });
    const result = await runJob(start, {
      onProgress: (p) => { if (p.message) $(".sync-label", btn).textContent = p.message.slice(0, 18); },
    });
    toast(`Loaded ${result.num_projects} projects from ${result.source}.`, "ok");
    await refreshStatus();
    await loadProjects();
    if (location.hash.replace("#/", "") === "library") renderLibrary();
    else location.hash = "#/library";
  } catch (e) {
    toast(e.message, "err");
  } finally {
    btn.classList.remove("busy"); btn.disabled = false;
    $(".sync-label", btn).textContent = "Sync library";
  }
}

async function loadProjects() {
  try {
    const data = await api.get("/projects");
    state.projects = data.projects;
    setCount("projects", usableProjects().length);
    updatePurgeButton();
  } catch { state.projects = []; }
}

function confirmPurgeLibrary() {
  const body = el("div", {},
    el("p", { class: "lead" },
      "This removes everything stored locally: synced projects, categorizations, connections, reading plans, and project specs."),
    el("p", { class: "muted", style: "margin-top:12px;font-size:.9rem" },
      "Your Zotero library is not changed. After purging, sync again or load the demo library to start fresh."),
    el("div", { class: "spread mt-3", style: "justify-content:flex-end;gap:10px" },
      el("button", { type: "button", class: "btn btn-ghost", onclick: closeModal }, "Cancel"),
      el("button", { type: "button", class: "btn btn-danger", onclick: () => { closeModal(); runPurgeLibrary(); } }, "Purge library")));
  openModal("Purge library?", body, "dialog");
}

async function runPurgeLibrary() {
  const btn = $("#purge-btn");
  if (btn) btn.disabled = true;
  try {
    await api.del("/library");
    state.projects = [];
    toast("Library purged. Sync or load the demo to start over.", "ok");
    await refreshStatus();
    setCount("strategies", "");
    setCount("specs", "");
    if (location.hash.replace("#/", "") === "library") await renderLibrary();
    else location.hash = "#/library";
  } catch (e) {
    toast(e.message, "err");
  } finally {
    if (btn) btn.disabled = false;
  }
}

/* ════════════════════════════════════════════════════════════════
   VIEWS
   ════════════════════════════════════════════════════════════════ */
const view = () => $("#view");

const viewMeta = {
  library: {
    title: "Library",
    subtitle: "Your Zotero collections, categorized and ready to explore.",
  },
  connections: {
    title: "Connections",
    subtitle: "Where your projects overlap — shared themes, methods, and authors.",
  },
  strategies: {
    title: "Reading strategies",
    subtitle: "Compose ordered reading paths across projects for a specific goal.",
  },
  specs: {
    title: "Suggest new papers",
    subtitle: "Upload a project spec, screen your library, and see which papers match — with why each one matters.",
  },
};

function setView(route, actions = []) {
  const meta = viewMeta[route] || viewMeta.library;
  $("#view-title").textContent = meta.title;
  $("#view-subtitle").textContent = meta.subtitle;
  $("#view-actions").replaceChildren(...actions);
}

function viewHero(title, text) {
  return el("div", { class: "view-hero" },
    el("div", { class: "section-label" }, "Overview"),
    el("h2", {}, title),
    el("p", {}, text));
}

function kpiItem(val, lbl, sub = "", accent = false) {
  const kids = [el("div", { class: "val" }, String(val)), el("div", { class: "lbl" }, lbl)];
  if (sub) kids.push(el("div", { class: "kpi-sub" }, sub));
  return el("div", { class: `kpi-item${accent ? " accent" : ""}` }, ...kids);
}

function totalPapers(onlyUsable = false) {
  const list = onlyUsable ? usableProjects() : state.projects;
  return list.reduce((n, p) => n + (p.num_items || 0), 0);
}

function categorizedCount() {
  return usableProjects().filter((p) => p.category).length;
}

async function renderKpiStrip(route) {
  const host = $("#kpi-inner");
  if (!host) return;
  const items = [];

  if (route === "library") {
    const active = usableProjects();
    const inactive = inactiveProjects();
    items.push(
      kpiItem(active.length, "Active projects", "Collections with papers", true),
      kpiItem(totalPapers(true), "Papers", "In active collections"),
      kpiItem(categorizedCount(), "Categorized", categorizedCount() ? "AI-tagged" : "Run categorize"),
    );
    if (inactive.length) items.push(kpiItem(inactive.length, "Excluded", "Empty, single & unfiled"));
    const src = state.status?.zotero_mode || (state.projects.length ? "loaded" : "—");
    items.push(kpiItem(src, "Source", state.status?.using_mock_llm ? "demo AI" : "library sync"));
  } else if (route === "connections") {
    const active = usableProjects();
    items.push(
      kpiItem(active.length, "Active projects", "Used for analysis", true),
      kpiItem(active.length >= 2 ? "Ready" : "Need 2+", "Status", "Minimum for connections"),
    );
    try {
      const { connections } = await api.get("/connections");
      if (connections) {
        items.push(
          kpiItem(connections.shared_threads?.length || 0, "Threads", "Shared concepts"),
          kpiItem(connections.clusters?.length || 0, "Groupings", "Suggested clusters"),
        );
      } else {
        items.push(kpiItem("—", "Threads", "Run analysis"), kpiItem("—", "Groupings", "Run analysis"));
      }
    } catch {
      items.push(kpiItem("—", "Threads", "—"), kpiItem("—", "Groupings", "—"));
    }
  } else if (route === "strategies") {
    let n = 0;
    try { n = (await api.get("/strategies")).strategies.length; } catch { /* ignore */ }
    items.push(
      kpiItem(n, "Saved plans", "Reading strategies", true),
      kpiItem(usableProjects().length, "Active projects", "Available to combine"),
      kpiItem(strategyMode === "auto" ? "Agent" : "Manual", "Mode", "Project selection"),
    );
  } else if (route === "specs") {
    let specs = [];
    try { specs = (await api.get("/specs")).specs; } catch { /* ignore */ }
    const analyzed = specs.filter((s) => s.status === "analyzed").length;
    items.push(
      kpiItem(specs.length, "Specs", "Uploaded descriptions", true),
      kpiItem(analyzed, "With suggestions", "Specs with relevant papers"),
      kpiItem(usableProjects().length ? totalPapers(true) : "—", "Papers", "Screened from library"),
    );
  }

  host.replaceChildren(...items);
}

/* ── 1. LIBRARY ───────────────────────────────────────────────── */
async function renderLibrary() {
  await loadProjects();
  const active = usableProjects();
  const actions = active.length
    ? [el("button", { class: "btn btn-brass btn-sm", onclick: categorizeAll }, "✦ Categorize all")]
    : [];
  setView("library", actions);
  await renderKpiStrip("library");

  if (!state.projects.length) {
    view().replaceChildren(emptyLibrary());
    return;
  }

  const inactive = inactiveProjects();
  const parts = [
    viewHero("Your projects", "Each Zotero collection with papers is a project. Categorize one to see its discipline, themes, and methods — or categorize the whole shelf at once."),
    el("div", { class: "grid grid-projects" }, ...active.map((p) => projectCard(p))),
  ];
  if (inactive.length) {
    parts.push(
      el("div", { class: "section-head mt-3" },
        el("div", {},
          el("h2", {}, "Excluded collections"),
          el("p", {}, "Empty folders, single-paper collections, and unfiled papers — shown for reference only, not used in analysis."))),
      el("div", { class: "grid grid-projects grid-inactive" }, ...inactive.map((p) => projectCard(p, true))));
  }
  view().replaceChildren(...parts);
}

function projectCard(p, inactive = false) {
  const head = el("div", { class: "project-card-head" },
    el("h3", {}, p.name),
    el("div", { class: "muted" }, `${p.num_items} ${p.num_items === 1 ? "paper" : "papers"}`));
  const scroll = el("div", { class: "project-card-scroll" });

  if (inactive) {
    const labels = { unfiled: "Unfiled", empty: "Empty folder", single: "Single paper" };
    const hints = {
      unfiled: "Papers not in any collection — move them into a collection with 2+ papers.",
      empty: "No papers in this folder — add papers in Zotero or ignore this collection.",
      single: "Only one paper — add another to this collection or merge with a related folder.",
    };
    const reason = p.inactive_reason || "empty";
    scroll.append(
      el("div", { class: "project-meta", style: "margin-top:0" },
        el("span", { class: "pill ink" }, labels[reason] || "Excluded")),
      el("p", { class: "inactive-hint" }, hints[reason] || hints.empty));
    const canView = p.num_items > 0;
    return el("div", {
      class: `card spine project-card inactive${canView ? " viewable" : ""}`,
      ...(canView ? { onclick: () => openProject(p.key, { readOnly: true }) } : {}),
    }, head, scroll);
  }

  const cat = p.category;
  if (cat) {
    scroll.append(el("p", { class: "lead" }, cat.summary));
    scroll.append(el("div", { class: "project-meta", style: "margin-top:0" },
      el("span", { class: "pill green" }, cat.discipline),
      el("span", { class: "pill ink" }, cat.maturity)));
    if (cat.themes?.length) {
      scroll.append(el("div", { class: "tag-row" }, ...cat.themes.slice(0, 5).map((t) => el("span", { class: "tag" }, t))));
    }
  } else {
    scroll.append(el("div", { class: "project-meta", style: "margin-top:0" },
      el("button", {
        class: "btn btn-ghost btn-sm",
        onclick: (e) => { e.stopPropagation(); categorizeOne(p.key, e.currentTarget); },
      }, "✦ Categorize")));
  }
  return el("div", { class: "card spine linkish project-card", onclick: () => openProject(p.key) }, head, scroll);
}

function emptyLibrary() {
  return el("div", { class: "empty" },
    el("div", { class: "emoji" }, "❡"),
    el("h3", {}, "Your shelf is empty"),
    el("p", {}, "Sync your Zotero library to pull in your collections — or load a demo library to explore everything first."),
    el("div", { class: "row" },
      el("button", { class: "btn btn-primary", onclick: () => doSync("zotero") }, "Sync Zotero"),
      el("button", { class: "btn btn-brass", onclick: () => doSync("demo") }, "Load demo library")));
}

async function categorizeOne(key, btn) {
  if (btn) { btn.disabled = true; btn.textContent = "Categorizing…"; }
  try {
    const start = await api.post(`/projects/${key}/categorize`);
    await runJob(start);
    toast("Categorized.", "ok");
    await renderLibrary();
  } catch (e) { toast(e.message, "err"); if (btn) { btn.disabled = false; btn.textContent = "✦ Categorize"; } }
}

async function categorizeAll(e) {
  const btn = e?.currentTarget;
  if (btn) btn.disabled = true;
  const box = showProgressModal("Categorizing projects", "Categorizing every project…");
  try {
    const start = await api.post("/projects/categorize-all");
    await runJob(start, { onProgress: (p) => box._update(p) });
    closeModal();
    toast("All projects categorized.", "ok");
    await renderLibrary();
  } catch (err) {
    closeModal();
    toast(err.message, "err");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function openProject(key, { readOnly = false } = {}) {
  openModal("Loading…", el("div", { class: "skeleton modal-skeleton" }), "sheet");
  try {
    const p = await api.get(`/projects/${key}`);
    const body = el("div", {});
    if (readOnly) {
      body.append(el("p", { class: "inactive-hint", style: "margin:0 0 12px" },
        "This collection is excluded from analysis. Collections need at least 2 papers to be used."));
    }
    if (p.category) {
      body.append(
        el("div", { class: "spread", style: "flex-wrap:wrap;gap:8px;margin-bottom:6px" },
          el("span", { class: "pill green" }, p.category.discipline),
          el("span", { class: "pill ink" }, p.category.maturity),
          p.category._mock ? el("span", { class: "mock-note" }, "demo AI") : null),
        el("p", { class: "lead", style: "margin:12px 0" }, p.category.summary),
        labeledTags("Themes", p.category.themes),
        labeledTags("Methods", p.category.methods));
    } else if (!readOnly) {
      body.append(el("button", { class: "btn btn-brass btn-sm", style: "margin-bottom:14px",
        onclick: async (e) => { e.currentTarget.disabled = true; await categorizeOne(key); closeModal(); openProject(key); } }, "✦ Categorize this project"));
    }
    const papers = p.items || [];
    body.append(el("h3", { class: "mt-2", style: "font-family:var(--font-display);font-size:1.05rem" }, `${papers.length} papers`));
    const list = el("div", {});
    for (const it of papers) {
      list.append(el("div", { class: "paper-line" },
        el("div", { class: "pt" }, it.title),
        el("div", { class: "pm" }, [it.creators, it.year, it.publication].filter(Boolean).join(" · "))));
    }
    body.append(list);
    setModal(p.name, body, "sheet");
  } catch (e) { closeModal(); toast(e.message, "err"); }
}
function labeledTags(label, items) {
  if (!items?.length) return null;
  return el("div", { style: "margin:10px 0" },
    el("div", { class: "muted", style: "font-size:.76rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px" }, label),
    el("div", { class: "tag-row" }, ...items.map((t) => el("span", { class: "tag" }, t))));
}

/* ── 2. CONNECTIONS ───────────────────────────────────────────── */
async function renderConnections() {
  await loadProjects();
  const active = usableProjects();
  setView("connections", active.length >= 2
    ? [el("button", { class: "btn btn-primary btn-sm", onclick: findConnections }, "⁂ Find connections")] : []);
  await renderKpiStrip("connections");

  if (active.length < 2) {
    view().replaceChildren(el("div", { class: "empty" },
      el("div", { class: "emoji" }, "⁂"),
      el("h3", {}, "Connections need active projects"),
      el("p", {}, "Sync at least two collections with 2+ papers each. Empty, single-paper, and unfiled collections are excluded."),
      el("div", { class: "row" }, el("button", { class: "btn btn-brass", onclick: () => doSync("demo") }, "Load demo library"))));
    return;
  }

  view().replaceChildren(
    viewHero("Cross-project threads", "Shared concepts, recurring methods, and authors that thread through different corners of your library."),
    el("div", { id: "conn-body" }, el("div", { class: "muted" }, "Loading…")));

  try {
    const { connections } = await api.get("/connections");
    if (connections) renderConnectionMap(connections);
    else $("#conn-body").replaceChildren(el("div", { class: "empty" },
      el("div", { class: "emoji" }, "⁂"),
      el("h3", {}, "No analysis yet"),
      el("p", {}, "Run the analysis to map how your projects connect."),
      el("div", { class: "row" }, el("button", { class: "btn btn-primary", onclick: findConnections }, "⁂ Find connections"))));
  } catch (e) { $("#conn-body").replaceChildren(el("div", { class: "muted" }, e.message)); }
}

async function findConnections() {
  const box = showProgressModal("Finding connections", "Reading across your projects…");
  try {
    const start = await api.post("/connections");
    await runJob(start, { onProgress: (p) => box._update(p) });
    closeModal();
    toast("Connections mapped.", "ok");
    const { connections } = await api.get("/connections");
    renderConnectionMap(connections);
  } catch (e) {
    closeModal();
    toast(e.message, "err");
    renderConnections();
  }
}

function projName(key) { return state.projects.find((p) => p.key === key)?.name || key; }

function renderConnectionMap(c) {
  const root = el("div", {});
  root.append(el("div", { class: "card panel view-hero", style: "padding:22px;margin-bottom:22px;border-left-width:4px" },
    c._mock ? el("span", { class: "mock-note", style: "margin-bottom:10px" }, "demo AI — connect a Claude key for real analysis") : null,
    el("p", { class: "lead", style: "margin:0;font-size:1.02rem" }, c.overview)));

  if (c.shared_threads?.length) {
    root.append(el("h3", { style: "font-family:var(--font-display);margin:6px 0 12px" }, "Shared threads"));
    for (const t of c.shared_threads) {
      root.append(el("div", { class: "thread" },
        el("div", {}, el("div", { class: "thread-label" }, t.label), el("div", { class: "thread-kind" }, t.kind)),
        el("div", { class: "links" }, ...t.project_keys.map((k) => el("span", { class: "pill green" }, projName(k)))),
        el("span", { class: `strength ${t.strength}` }, t.strength)));
      if (t.explanation) root.lastChild.after(el("p", { class: "muted", style: "font-size:.83rem;margin:-4px 0 12px 2px" }, t.explanation));
    }
  }

  if (c.clusters?.length) {
    root.append(el("h3", { style: "font-family:var(--font-display);margin:22px 0 12px" }, "Suggested groupings"));
    for (const cl of c.clusters) {
      root.append(el("div", { class: "card spine cluster" },
        el("h4", {}, cl.name),
        el("div", { class: "links tag-row" }, ...cl.project_keys.map((k) => el("span", { class: "pill green" }, projName(k)))),
        el("p", { class: "muted", style: "margin:6px 0 14px;font-size:.88rem;line-height:1.5" }, cl.rationale),
        el("button", { class: "btn btn-ghost btn-sm", onclick: () => { location.hash = "#/strategies"; setTimeout(() => prefillStrategy(cl.project_keys), 60); } }, "↯ Build a reading plan")));
    }
  }
  $("#conn-body").replaceChildren(root);
}

/* ── 3. STRATEGIES ────────────────────────────────────────────── */
let strategySelection = new Set();
let strategyMode = "manual";

async function renderStrategies() {
  await loadProjects();
  setView("strategies");
  await renderKpiStrip("strategies");
  const wrap = el("div", {});

  // builder
  wrap.append(buildStrategyForm());

  // saved strategies
  wrap.append(el("div", { class: "section-head mt-3" }, el("div", {}, el("h2", {}, "Saved plans"))));
  const list = el("div", { id: "strat-list" }, el("div", { class: "muted" }, "Loading…"));
  wrap.append(list);
  view().replaceChildren(wrap);
  await loadStrategies();
}

function buildStrategyForm() {
  const active = usableProjects();
  if (!active.length) {
    return el("div", { class: "empty" },
      el("div", { class: "emoji" }, "↯"),
      el("h3", {}, "Plans need projects"),
      el("p", {}, "Sync or load a library with collections that have at least 2 papers each (excluded collections do not count)."),
      el("div", { class: "row" }, el("button", { class: "btn btn-brass", onclick: () => doSync("demo") }, "Load demo library")));
  }
  const card = el("div", { class: "card panel", style: "padding:24px" });
  const modeToggle = el("div", { class: "mode-toggle" },
    el("button", { class: strategyMode === "manual" ? "on" : "", onclick: () => setMode("manual") }, "I choose projects"),
    el("button", { class: strategyMode === "auto" ? "on" : "", onclick: () => setMode("auto") }, "Let the agent decide"));

  const chooser = el("div", { class: "choose-grid", id: "strat-choose" },
    ...active.map((p) => choiceTile(p)));

  const goal = el("textarea", { id: "strat-goal", rows: "3", placeholder: "e.g. I'm writing a related-work section connecting fairness and causal inference — what should I read and in what order?" });

  card.append(
    el("div", { class: "strat-head" },
      el("h2", {}, "Compose a reading plan"),
      el("p", { class: "muted" }, "Pick the projects to combine and state your goal. You get an ordered path through the papers."),
      modeToggle),
    el("div", { class: "field", id: "strat-choose-field" }, el("label", {}, "Projects"), chooser),
    el("div", { class: "field mt-2" }, el("label", {}, "Your goal (optional)"), goal),
    el("div", { class: "mt-2" }, el("button", { type: "button", class: "btn btn-primary", id: "strat-go", onclick: submitStrategy }, "↯ Generate strategy")));
  applyModeUI(card);
  return card;
}

function choiceTile(p) {
  const on = strategySelection.has(p.key);
  return el("label", { class: `choice ${on ? "on" : ""}`, "data-key": p.key },
    el("input", { type: "checkbox", ...(on ? { checked: "checked" } : {}), onchange: (e) => toggleChoice(p.key, e.target.checked) }),
    el("div", {}, el("div", { class: "c-name" }, p.short_name || p.name), el("div", { class: "c-sub" }, `${p.num_items} papers`)));
}
function toggleChoice(key, on) {
  if (on) strategySelection.add(key); else strategySelection.delete(key);
  const tile = $(`.choice[data-key="${key}"]`); if (tile) tile.classList.toggle("on", on);
}
function setMode(mode) {
  strategyMode = mode;
  $$(".mode-toggle button").forEach((b, i) => b.classList.toggle("on", (mode === "manual") === (i === 0)));
  applyModeUI(view());
}
function applyModeUI(root) {
  const field = $("#strat-choose-field", root);
  if (field) field.style.opacity = strategyMode === "auto" ? ".4" : "1";
  if (field) field.style.pointerEvents = strategyMode === "auto" ? "none" : "auto";
}
function prefillStrategy(keys) {
  strategyMode = "manual";
  strategySelection = new Set(keys);
  renderStrategies();
}

async function submitStrategy(e) {
  const btn = e.currentTarget;
  const goal = $("#strat-goal")?.value.trim() || "";
  const keys = [...strategySelection];
  if (strategyMode === "manual" && keys.length === 0) { toast("Pick at least one project, or switch to “Let the agent decide”.", "err"); return; }
  btn.disabled = true;
  const box = showProgressModal("Generating reading plan", "Designing your reading path…");
  try {
    const start = await api.post("/strategies", { goal, mode: strategyMode, project_keys: keys });
    await runJob(start, { onProgress: (p) => box._update(p) });
    closeModal();
    toast("Reading plan ready.", "ok");
    strategySelection.clear();
    await renderStrategies();
  } catch (err) {
    closeModal();
    toast(err.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function loadStrategies() {
  try {
    const { strategies } = await api.get("/strategies");
    const host = $("#strat-list"); if (!host) return;
    if (!strategies.length) { host.replaceChildren(el("p", { class: "muted" }, "No saved plans yet — generate one above.")); return; }
    host.replaceChildren(...strategies.map(strategyRow));
  } catch { /* ignore */ }
}
function strategyModeLabel(s) {
  if (s.mode === "spec") return `from spec · ${s.spec_title || "project"}`;
  if (s.mode === "auto") return "agent-chosen";
  return "you chose";
}

function strategyRow(s) {
  const plan = s.plan || {};
  return el("div", { class: "row-item linkish" },
    el("div", { onclick: () => openStrategy(s), style: "cursor:pointer;flex:1" },
      el("h4", {}, plan.title || "Reading plan"),
      el("div", { class: "muted" }, [
        `${plan.sequence?.length || 0} papers`,
        planScheduleLabel(plan),
        strategyModeLabel(s),
        fmtTime(s.created_at),
      ].filter(Boolean).join(" · "))),
    el("div", { style: "display:flex;gap:8px" },
      el("button", { class: "btn btn-ghost btn-sm", onclick: () => openStrategy(s) }, "Open"),
      el("button", { class: "btn btn-ghost btn-sm btn-danger", onclick: () => deleteStrategy(s.id) }, "Delete")));
}
function openStrategy(s) {
  const plan = s.plan || {};
  const body = el("div", {});
  if (plan._mock) body.append(el("span", { class: "mock-note", style: "margin-bottom:10px" }, "demo AI"));
  if (s.spec_id) {
    body.append(el("div", { class: "spec-map-banner" },
      el("span", {}, "Mapped from project spec: "),
      el("button", {
        type: "button",
        class: "btn btn-ghost btn-sm",
        onclick: () => { closeModal(); selectedSpecId = s.spec_id; specsTab = "suggestions"; location.hash = "#/specs"; },
      }, s.spec_title || "View suggestions")));
  }
  if (plan.schedule?.summary) {
    body.append(el("div", { class: "schedule-banner" },
      el("strong", {}, "Reading schedule: "),
      el("span", {}, plan.schedule.summary)));
  }
  body.append(el("p", { class: "lead" }, plan.approach || ""));
  if (plan.goal_restatement) body.append(el("p", { class: "rel-why", style: "margin:10px 0" }, "Goal: " + plan.goal_restatement));
  const seq = el("div", { class: "sequence" });
  let lastDay = null;
  (plan.sequence || []).forEach((step, i) => {
    if (step.scheduled_day && step.scheduled_day !== lastDay) {
      lastDay = step.scheduled_day;
      seq.append(el("div", { class: "schedule-day" }, `Day ${lastDay}`));
    }
    const head = el("div", { class: "spread", style: "align-items:flex-start;gap:10px" },
      el("h4", { style: "margin:0;flex:1" }, step.title),
      el("div", { style: "display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end" },
        step.read_minutes ? el("span", { class: "read-time" }, fmtReadMinutes(step.read_minutes)) : null,
        step.spec_relevance
          ? el("span", { class: `rel-flag rel-${step.spec_relevance}` }, step.spec_relevance.replace("_", " "))
          : null));
    seq.append(el("div", { class: "step" },
      el("div", { class: "step-n" }, `${i + 1} · ${projName(step.project_key)}`),
      head,
      el("div", { class: "step-reason" }, step.reason)));
  });
  body.append(seq);
  if (plan.synthesis_prompts?.length) {
    body.append(el("h3", { class: "mt-2", style: "font-family:var(--font-display);font-size:1.05rem" }, "Hold these in mind"),
      el("ul", { style: "color:var(--ink-2);line-height:1.7;padding-left:20px" }, ...plan.synthesis_prompts.map((q) => el("li", {}, q))));
  }
  openModal(plan.title || "Reading plan", body, "sheet");
}
async function deleteStrategy(id) {
  try { await api.del(`/strategies/${id}`); toast("Deleted.", "ok"); await loadStrategies(); }
  catch (e) { toast(e.message, "err"); }
}

/* ── 4. SPECS ─────────────────────────────────────────────────── */
let specsTab = "upload";
let selectedSpecId = null;

async function renderSpecs() {
  await loadProjects();
  const specActions = specsTab === "upload"
    ? [el("button", { type: "button", class: "btn btn-primary btn-sm", onclick: () => switchSpecsTab("suggestions") }, "View suggestions")]
    : [el("button", { type: "button", class: "btn btn-primary btn-sm", onclick: () => switchSpecsTab("upload") }, "Upload spec")];
  setView("specs", specActions);
  await renderKpiStrip("specs");
  const wrap = el("div", {});
  wrap.append(el("div", { class: "sub-tabs" },
    el("button", { type: "button", class: specsTab === "upload" ? "on" : "", onclick: () => switchSpecsTab("upload") }, "Upload & manage"),
    el("button", { type: "button", class: specsTab === "suggestions" ? "on" : "", onclick: () => switchSpecsTab("suggestions") }, "Suggested papers")));
  wrap.append(el("div", { id: "specs-panel" }));
  view().replaceChildren(wrap);
  await renderSpecsPanel();
}

async function switchSpecsTab(tab) {
  if (specsTab === tab) return;
  specsTab = tab;
  $$(".sub-tabs button").forEach((b, i) => b.classList.toggle("on", (tab === "upload") === (i === 0)));
  await renderSpecsPanel();
}

async function renderSpecsPanel() {
  const panel = $("#specs-panel");
  if (!panel) return;
  if (specsTab === "upload") {
    panel.replaceChildren(
      viewHero("Upload a project spec",
        "Drop in a grant aim, proposal, or project description (PDF, Word, Markdown, or text). Irrelevant uploads are rejected with guidance on what to upload instead."),
      specUploader(),
      el("div", { class: "section-head mt-3" }, el("div", {}, el("h2", {}, "Your specs"))),
      el("div", { id: "spec-list" }, el("div", { class: "muted" }, "Loading…")),
    );
    await loadSpecs();
  } else {
    panel.replaceChildren(
      viewHero("Suggested papers",
        "Relevant papers from your library for each project spec, with a short explanation of why each one matters."),
      el("div", { id: "spec-suggestions" }, el("div", { class: "muted" }, "Loading…")),
    );
    await loadSpecSuggestions();
  }
}

function specUploader() {
  const card = el("div", { class: "card panel", style: "padding:22px" });
  const drop = el("div", { class: "dropzone" },
    el("div", { class: "emoji" }, "✦"),
    el("p", { style: "margin:8px 0 4px;font-weight:600" }, "Drop a PDF, Word, Markdown, or text file"),
    el("p", { class: "muted", style: "margin:0;font-size:.84rem" }, ".pdf · .doc · .docx · .md · .txt — or paste below"),
    el("input", { type: "file", id: "spec-file", accept: ".pdf,.doc,.docx,.md,.txt,.markdown", style: "display:none" }));
  drop.addEventListener("click", () => $("#spec-file", drop).click());
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("drag"); if (e.dataTransfer.files[0]) uploadSpecFile(e.dataTransfer.files[0]); });
  $("#spec-file", drop)?.addEventListener("change", (e) => { if (e.target.files[0]) uploadSpecFile(e.target.files[0]); });

  const title = el("input", { type: "text", id: "spec-title", placeholder: "Project title (optional)" });
  const text = el("textarea", { id: "spec-text", rows: "4", placeholder: "Or paste your project spec / aims here…" });
  card.append(drop,
    el("div", { class: "field mt-2" }, el("label", {}, "Title"), title),
    el("div", { class: "field mt-2" }, el("label", {}, "Paste a specification"), text),
    el("div", { class: "mt-2" }, el("button", { class: "btn btn-primary", onclick: submitSpecText }, "✦ Save spec")));
  return card;
}

async function uploadSpecFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("title", $("#spec-title")?.value || "");
  try { const spec = await api.upload(fd); toast(`Saved “${spec.title}”.`, "ok"); await loadSpecs(); offerAnalyze(spec); }
  catch (e) { toast(e.message, "err"); }
}
async function submitSpecText() {
  const text = $("#spec-text")?.value.trim();
  if (!text) { toast("Paste some text or drop a file.", "err"); return; }
  const fd = new FormData();
  fd.append("text", text);
  fd.append("title", $("#spec-title")?.value || "");
  try { const spec = await api.upload(fd); toast(`Saved “${spec.title}”.`, "ok"); $("#spec-text").value = ""; await loadSpecs(); offerAnalyze(spec); }
  catch (e) { toast(e.message, "err"); }
}

async function loadSpecs() {
  try {
    const { specs } = await api.get("/specs");
    const host = $("#spec-list"); if (!host) return;
    if (!specs.length) { host.replaceChildren(el("p", { class: "muted" }, "No specs yet.")); return; }
    host.replaceChildren(...specs.map(specRow));
  } catch { /* ignore */ }
}
function specRow(s) {
  const status = { new: "ink", analyzing: "brass", analyzed: "green" }[s.status] || "ink";
  return el("div", { class: "row-item" },
    el("div", { style: "flex:1;cursor:pointer", onclick: () => openSpec(s.id) },
      el("div", { class: "spread", style: "justify-content:flex-start;gap:10px" },
        el("h4", {}, s.title),
        el("span", { class: `pill ${status}` }, s.status === "analyzed" ? `${s.num_relevant ?? 0} relevant` : s.status)),
      el("div", { class: "muted", style: "margin-top:3px" }, esc(s.preview).slice(0, 120) + "…")),
    el("div", { style: "display:flex;gap:8px" },
      el("button", { class: "btn btn-primary btn-sm", onclick: () => confirmAnalyzeSpec(s.id) }, s.status === "analyzed" ? "Refresh suggestions" : "Find relevant papers"),
      el("button", { class: "btn btn-ghost btn-sm btn-danger", onclick: () => deleteSpec(s.id) }, "Delete")));
}
function offerAnalyze(spec) {
  if (!usableProjects().length) { toast("Saved — sync a library with categorized collections to analyze.", ""); return; }
  confirmAnalyzeSpec(spec.id);
}

function confirmAnalyzeSpec(specId) {
  if (!usableProjects().length) { toast("Sync a library with papers in collections first.", "err"); return; }
  const papers = totalPapers(true);
  const paperLabel = papers === 1 ? "paper" : "papers";
  const body = el("div", {},
    el("p", { class: "lead" },
      `This will screen your active library (${papers} ${paperLabel}) and list only the papers that look relevant to your project spec.`),
    el("p", { class: "muted", style: "margin-top:12px;font-size:.9rem" },
      "Depending on how many papers you have, this can take a while — from under a minute for a small library to several minutes for a large one. You can keep using the app while it runs."),
    el("div", { class: "spread mt-3", style: "justify-content:flex-end;gap:10px" },
      el("button", { type: "button", class: "btn btn-ghost", onclick: closeModal }, "Cancel"),
      el("button", { type: "button", class: "btn btn-primary", onclick: () => runAnalyzeSpec(specId) }, "Find relevant papers")));
  openModal("Find relevant papers?", body, "dialog");
}

async function runAnalyzeSpec(specId) {
  const box = showProgressModal("Finding relevant papers", "Screening your library against the project spec…");
  try {
    const start = await api.post(`/specs/${specId}/analyze`, {});
    const result = await runJob(start, { onProgress: (p) => box._update(p) });
    closeModal();
    const n = result?.relevant ?? 0;
    toast(n ? `Found ${n} relevant paper${n === 1 ? "" : "s"}.` : "No relevant papers found.", n ? "ok" : "");
    selectedSpecId = specId;
    specsTab = "suggestions";
    await renderSpecs();
  } catch (e) { closeModal(); toast(e.message, "err"); }
}

async function loadSpecSuggestions() {
  const host = $("#spec-suggestions");
  if (!host) return;
  try {
    const { specs } = await api.get("/specs");
    const analyzed = specs.filter((s) => s.status === "analyzed");
    if (!analyzed.length) {
      host.replaceChildren(el("div", { class: "empty" },
        el("div", { class: "emoji" }, "✦"),
        el("h3", {}, "No suggestions yet"),
        el("p", {}, "Upload a project spec and click Find relevant papers to see which library papers matter for your aim."),
        el("button", { type: "button", class: "btn btn-primary", onclick: () => switchSpecsTab("upload") }, "Upload a spec")));
      return;
    }
    const pick = selectedSpecId && analyzed.some((s) => s.id === selectedSpecId)
      ? selectedSpecId
      : analyzed[0].id;
    selectedSpecId = pick;
    const spec = await api.get(`/specs/${pick}`);
    const results = Object.values(spec.analysis || {}).sort((a, b) => (b.score || 0) - (a.score || 0));
    const wrap = el("div", {});
    const picker = el("div", { class: "field" },
      el("label", {}, "Project spec"),
      el("select", {
        class: "input",
        onchange: async (e) => { selectedSpecId = e.target.value; await loadSpecSuggestions(); },
      }, ...analyzed.map((s) => {
        const opt = el("option", { value: s.id }, s.title);
        if (s.id === pick) opt.selected = true;
        return opt;
      })));
    wrap.append(picker);
    wrap.append(el("p", { class: "muted", style: "margin:12px 0;font-size:.86rem" },
      spec.num_screened
        ? `${results.length} relevant of ${spec.num_screened} screened`
        : `${results.length} relevant papers`));
    if (!results.length) {
      wrap.append(el("p", { class: "muted" }, "No relevant papers found for this spec. Try refreshing after syncing more papers."));
      wrap.append(el("button", { type: "button", class: "btn btn-primary mt-2", onclick: () => confirmAnalyzeSpec(pick) }, "Refresh suggestions"));
    } else {
      wrap.append(el("div", { class: "spread mt-2", style: "margin-bottom:14px;align-items:center" },
        el("p", { class: "muted", style: "margin:0;font-size:.86rem" }, "Turn these into an ordered reading plan — each step keeps its spec relevance note."),
        el("button", { type: "button", class: "btn btn-primary btn-sm", onclick: () => buildReadingPlanFromSpec(pick) }, "↯ Build reading plan")));
      for (const r of results) wrap.append(relevanceRow(r));
    }
    host.replaceChildren(wrap);
  } catch (e) { host.replaceChildren(el("p", { class: "muted" }, e.message)); }
}

async function openSpec(specId) {
  selectedSpecId = specId;
  specsTab = "suggestions";
  await renderSpecs();
}

async function buildReadingPlanFromSpec(specId) {
  let spec;
  try { spec = await api.get(`/specs/${specId}`); }
  catch (e) { toast(e.message, "err"); return; }
  const box = showProgressModal("Generating reading plan", "Ordering spec-relevant papers into a reading path…");
  try {
    const start = await api.post("/strategies", {
      spec_id: specId,
      goal: `Read the papers most relevant to: ${spec.title}`,
      mode: "spec",
    });
    const saved = await runJob(start, { onProgress: (p) => box._update(p) });
    closeModal();
    toast("Reading plan ready — mapped from your spec.", "ok");
    openStrategy(saved);
  } catch (e) {
    closeModal();
    toast(e.message, "err");
  }
}

function relevanceRow(r) {
  return el("div", { class: "relevance-row relevance-row--suggest" },
    el("div", {},
      el("div", { class: "rel-title" }, r.title || r.paper_key),
      el("div", { class: "muted", style: "font-size:.76rem" }, projName(r.project_key)),
      el("div", { class: "rel-why" }, r.relevance_explanation),
      r.use_for?.length ? el("div", { class: "tag-row" }, ...r.use_for.map((u) => el("span", { class: "tag" }, u))) : null),
    el("span", { class: `rel-flag rel-${r.relevance}` }, r.relevance.replace("_", " ")));
}
async function deleteSpec(id) {
  try { await api.del(`/specs/${id}`); toast("Deleted.", "ok"); await loadSpecs(); }
  catch (e) { toast(e.message, "err"); }
}

/* ── shared: progress block ───────────────────────────────────── */
function progressBlock(initial) {
  const fill = el("div", { class: "progress-fill" });
  const msg = el("span", {}, initial);
  const pct = el("span", { class: "muted" }, "");
  const node = el("div", { class: "progress card", style: "padding:16px" },
    el("div", { class: "progress-bar" }, fill),
    el("div", { class: "progress-msg" }, msg, pct));
  return {
    node,
    update(p) {
      if (!p) return;
      const total = p.total || 0; const cur = p.current || 0;
      const ratio = total ? cur / total : 0.05;
      fill.style.width = `${Math.max(5, ratio * 100)}%`;
      if (p.message) msg.textContent = p.message;
      pct.textContent = total ? `${cur}/${total}` : "";
    },
  };
}

/* ── router ───────────────────────────────────────────────────── */
const routes = { library: renderLibrary, connections: renderConnections, strategies: renderStrategies, specs: renderSpecs };
async function route() {
  const name = (location.hash.replace("#/", "") || "library");
  $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.route === name));
  const fn = routes[name] || renderLibrary;
  $("#app").dataset.loading = "true";
  try { await fn(); } finally { $("#app").dataset.loading = "false"; }
  // keep saved-counts fresh
  api.get("/strategies").then((d) => setCount("strategies", d.strategies.length)).catch(() => {});
  api.get("/specs").then((d) => setCount("specs", d.specs.length)).catch(() => {});
}

/* ── boot ─────────────────────────────────────────────────────── */
async function goSuggestPapers() {
  try {
    const { specs } = await api.get("/specs");
    specsTab = specs.some((s) => s.status === "analyzed") ? "suggestions" : "upload";
  } catch {
    specsTab = "upload";
  }
  location.hash = "#/specs";
}

function bindChrome() {
  $("#suggest-btn")?.addEventListener("click", goSuggestPapers);
  $("#sync-btn").addEventListener("click", () => {
    if (state.status && !state.status.zotero_mode) doSync("demo");
    else doSync("zotero");
  });
  $("#purge-btn")?.addEventListener("click", confirmPurgeLibrary);
}
window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", async () => {
  bindChrome();
  await refreshStatus();
  if (!location.hash) location.hash = "#/library";
  else route();
});
