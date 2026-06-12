#!/usr/bin/env python3
"""Build the static Vercel demo site from bundled demo data + mock AI.

Runs the full offline pipeline (demo sync → categorize → connections → groups
→ spec → strategies → chat) and writes pre-baked API responses into vercel/.
No API keys or user input required on the deployed site.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
OUT = ROOT / "vercel"


def run_job(client, start_response: dict) -> dict:
    job_id = start_response["job_id"]
    for _ in range(300):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == "done":
            return job["result"]
        if job["status"] in ("error", "cancelled"):
            raise RuntimeError(f"job {job_id} {job['status']}: {job.get('error')}")
        time.sleep(0.02)
    raise RuntimeError(f"job {job_id} timed out")


def build_snapshot(client) -> dict:
    """Populate the store via the real API, then export GET responses."""
    run_job(client, client.post("/api/library/sync", json={"source": "demo"}).json())

    for proj in client.get("/api/projects").json()["projects"]:
        if proj.get("usable"):
            run_job(client, client.post(f"/api/projects/{proj['key']}/categorize").json())

    run_job(client, client.post("/api/connections").json())
    run_job(client, client.post("/api/groups").json())

    spec = client.post(
        "/api/specs",
        data={
            "text": (
                "We study fairness and calibration in recommender systems using "
                "causal inference and graph-based methods for literature review planning."
            ),
            "title": "Fairness aim",
        },
    ).json()
    run_job(client, client.post(f"/api/specs/{spec['id']}/analyze", json={}).json())
    run_job(client, client.post(f"/api/specs/{spec['id']}/discover", json={}).json())
    run_job(
        client,
        client.post("/api/strategies", json={"goal": "connect themes across projects", "mode": "auto"}).json(),
    )

    chat = client.post(
        "/api/chat",
        json={"message": "Which collections overlap on recommender systems and causal inference?"},
    ).json()

    projects = client.get("/api/projects").json()["projects"]
    project_details = {
        p["key"]: client.get(f"/api/projects/{p['key']}").json() for p in projects
    }

    spec_id = spec["id"]
    return {
        "status": client.get("/api/status").json(),
        "projects": projects,
        "projectDetails": project_details,
        "connections": client.get("/api/connections").json()["connections"],
        "groups": client.get("/api/groups").json()["paper_groups"],
        "strategies": client.get("/api/strategies").json(),
        "specs": client.get("/api/specs").json(),
        "specDetails": {spec_id: client.get(f"/api/specs/{spec_id}").json()},
        "chatThread": {
            "thread_id": chat["thread_id"],
            "messages": chat["messages"],
            "mock": chat.get("_mock", False),
        },
    }


def patch_app_js(src: str) -> str:
    """Turn the live SPA into a read-only demo that reads from DEMO_SNAPSHOT."""
    demo_api = r'''
/* ── API (demo — static snapshot, no network) ───────────────── */
const DEMO_SNAPSHOT = window.__DEMO_SNAPSHOT__;
const demoToast = (msg) => toast(msg, "warn");

function demoLookupGet(path) {
  const snap = DEMO_SNAPSHOT;
  if (path === "/status") return snap.status;
  if (path === "/projects") return { projects: snap.projects };
  const proj = path.match(/^\/projects\/([^/]+)$/);
  if (proj) return snap.projectDetails[proj[1]];
  if (path === "/connections") return { connections: snap.connections };
  if (path === "/groups") return { paper_groups: snap.groups };
  if (path === "/strategies") return snap.strategies;
  const spec = path.match(/^\/specs\/([^/]+)$/);
  if (spec) return snap.specDetails[spec[1]];
  if (path === "/specs") return snap.specs;
  const thread = path.match(/^\/chat\/threads\/([^/]+)$/);
  if (thread && thread[1] === snap.chatThread.thread_id) {
    return { thread: { id: thread[1], messages: snap.chatThread.messages } };
  }
  if (path === "/chat/threads") return { threads: [{ id: snap.chatThread.thread_id, updated_at: "" }] };
  throw new Error("Demo snapshot missing: " + path);
}

const api = {
  async get(path) { return demoLookupGet(path); },
  async post() { demoToast("This is a read-only demo. Clone the repo and run make run locally for full features."); throw new Error("demo"); },
  async del() { demoToast("This is a read-only demo. Clone the repo and run make run locally for full features."); throw new Error("demo"); },
  async upload() { demoToast("This is a read-only demo. Clone the repo and run make run locally for full features."); throw new Error("demo"); },
};
'''

    src = re.sub(
        r"/\* ── API ──.*?\n\};\n",
        demo_api + "\n",
        src,
        count=1,
        flags=re.DOTALL,
    )

    # Skip job polling / resume — nothing runs in the demo.
    src = src.replace(
        "async function resumeTrackedJobs() {",
        "async function resumeTrackedJobs() { return; /* demo */",
        1,
    )

    # Boot: load snapshot into state, hide write controls.
    src = src.replace(
        """window.addEventListener("DOMContentLoaded", async () => {
  bindChrome();
  bindJobRail();
  await refreshStatus();
  await resumeTrackedJobs();
  if (!location.hash) location.hash = "#/library";
  else route();
});""",
        """window.addEventListener("DOMContentLoaded", async () => {
  bindChrome();
  bindJobRail();
  document.getElementById("sync-btn")?.classList.add("hidden");
  document.getElementById("purge-btn")?.classList.add("hidden");
  await refreshStatus();
  await loadProjects();
  state.chatThreadId = DEMO_SNAPSHOT.chatThread.thread_id;
  setCount("strategies", DEMO_SNAPSHOT.strategies.strategies.length);
  setCount("specs", DEMO_SNAPSHOT.specs.specs.length);
  if (!location.hash) location.hash = "#/library";
  else route();
});""",
    )

    # Library: no categorize-all action.
    src = src.replace(
        """  const actions = active.length
    ? [el("button", { class: "btn btn-brass btn-sm", onclick: categorizeAll }, "✦ Categorize all")]
    : [];
  setView("library", actions);""",
        '  setView("library", []);',
    )

    # Connections: no find button.
    src = src.replace(
        """  setView("connections", active.length >= 2
    ? [el("button", { class: "btn btn-primary btn-sm", onclick: findConnections }, "⁂ Find connections")] : []);""",
        '  setView("connections", []);',
    )

    # Groups: no group button.
    src = src.replace(
        """  setView("groups", active.length >= 2
    ? [el("button", { class: "btn btn-primary btn-sm", onclick: findPaperGroups }, "◎ Group papers")] : []);""",
        '  setView("groups", []);',
    )

    # Strategies: saved plans only (no builder form).
    src = src.replace(
        """  setView("strategies");
  await renderKpiStrip("strategies");
  const wrap = el("div", {});

  // builder
  wrap.append(buildStrategyForm());""",
        """  setView("strategies", []);
  await renderKpiStrip("strategies");
  const wrap = el("div", {});""",
    )

    # Specs: no upload toolbar.
    src = src.replace(
        'setView("specs", specsToolbarActions());',
        'setView("specs", []);',
    )

    # Specs: skip file upload UI on demo.
    src = src.replace(
        """      viewHero("Upload & screen your library",
        "Save a grant aim or proposal, then use Find in library to see which papers you already have that match. This only searches your synced Zotero collections."),
      specUploader(),""",
        """      viewHero("Spec screening (demo)",
        "Pre-screened sample spec against the demo library — upload and screening are available when you run locally."),""",
    )

    # Hide destructive row actions in demo.
    src = src.replace(
        'el("button", { class: "btn btn-ghost btn-sm btn-danger", onclick: () => deleteStrategy(s.id) }, "Delete")',
        'null',
    )
    src = src.replace(
        'el("button", { class: "btn btn-ghost btn-sm btn-danger", onclick: () => deleteSpec(s.id) }, "Delete")',
        'null',
    )

    # Chat: read-only sample thread, no compose.
    src = src.replace(
        """  view().replaceChildren(
    chatOverviewPanel(),
    state.status?.using_mock_llm
      ? el("p", { class: "mock-note", id: "chat-mock-note", style: "margin:0 0 24px" },
        "demo AI — connect a Claude API key for full answers")
      : el("p", { id: "chat-mock-note", hidden: true }),
    el("div", { class: "chat-panel card panel" },
      el("div", { class: "chat-messages", id: "chat-messages" }),
      el("div", { class: "chat-compose" },
        el("div", { class: "chat-compose-box" },
          el("textarea", {
            id: "chat-input",
            class: "chat-input",
            rows: "3",
            placeholder: "e.g. Which collections overlap on drift-diffusion? What did grouping put in the Cortex set?",
            onkeydown: (e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
            },
          }),
          chatSendButton()),
        el("span", { class: "muted chat-hint" }, "Enter to send · Shift+Enter for newline"))));""",
        """  view().replaceChildren(
    chatOverviewPanel(),
    el("p", { class: "mock-note", id: "chat-mock-note", style: "margin:0 0 24px" },
      "Sample conversation from the demo library — chat is read-only on this site."),
    el("div", { class: "chat-panel card panel" },
      el("div", { class: "chat-messages", id: "chat-messages" })));""",
    )

    return src


def clean_github_url(remote: str) -> str:
    import urllib.parse

    remote = remote.strip()
    if not remote:
        return "https://github.com"
    if remote.startswith("git@"):
        remote = "https://github.com/" + remote.split(":", 1)[-1]
    parsed = urllib.parse.urlparse(remote)
    if "@" in parsed.netloc:
        parsed = parsed._replace(netloc=parsed.netloc.split("@", 1)[-1])
    url = urllib.parse.urlunparse(parsed)
    return url[:-4] if url.endswith(".git") else url


def write_index_html(repo_url: str) -> None:
    html = (STATIC / "index.html").read_text()
    html = html.replace("/static/styles.css", "styles.css")
    html = html.replace('src="/static/app.js"', 'src="demo-snapshot.js"\n  <script src="app.js"')
    html = html.replace(
        "<title>BindingSolution · your AI reading room</title>",
        "<title>BindingSolution · Demo</title>",
    )

    banner = f"""
  <div class="demo-banner" role="status">
    <strong>Demo site</strong> — pre-loaded sample library for browsing only.
    No sign-in, no data collection, no API calls.
    <a href="{repo_url}" class="demo-banner-link">Run locally</a> for your own Zotero library.
  </div>
"""
    html = html.replace("<body>", "<body>" + banner, 1)
    (OUT / "index.html").write_text(html)


def main() -> int:
    os.environ["MOCK_LLM"] = "true"
    os.environ["ANTHROPIC_API_KEY"] = ""

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BINDING_DATA_DIR"] = tmp
        sys.path.insert(0, str(ROOT))

        import app.jobs as job_mod
        import app.server as server
        from fastapi.testclient import TestClient

        job_mod.reset_registry()
        server._store = None
        client = TestClient(server.create_app())
        snapshot = build_snapshot(client)

    OUT.mkdir(parents=True, exist_ok=True)

    snapshot_js = "window.__DEMO_SNAPSHOT__ = " + json.dumps(snapshot, indent=2) + ";\n"
    (OUT / "demo-snapshot.js").write_text(snapshot_js)

    app_js = patch_app_js((STATIC / "app.js").read_text())
    (OUT / "app.js").write_text(app_js)

    shutil.copy2(STATIC / "styles.css", OUT / "styles.css")
    shutil.copy2(STATIC / "logo.svg", OUT / "logo.svg")

    remote = os.popen("git -C " + str(ROOT) + " remote get-url origin 2>/dev/null").read().strip()
    write_index_html(clean_github_url(remote))

    # Demo banner styles appended to CSS.
    demo_css = """

/* ── Vercel demo banner ─────────────────────────────────────── */
.demo-banner {
  position: relative;
  z-index: 100;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.35em 0.75em;
  padding: 0.55rem 1.25rem;
  background: linear-gradient(90deg, var(--bind-green) 0%, var(--bind-green-2) 100%);
  color: #f4efe4;
  font-size: 0.42rem;
  text-align: center;
  border-bottom: 2px solid var(--brass);
}
.demo-banner strong { color: var(--brass-2); font-weight: 600; }
.demo-banner-link {
  color: #fff;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.demo-banner-link:hover { color: var(--brass-2); }
"""
    with open(OUT / "styles.css", "a") as f:
        f.write(demo_css)

    print(f"Wrote Vercel demo to {OUT}/")
    print(f"  projects: {len(snapshot['projects'])}")
    print(f"  strategies: {len(snapshot['strategies']['strategies'])}")
    print(f"  specs: {len(snapshot['specs']['specs'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
