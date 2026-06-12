"""FastAPI application: REST API + static frontend.

Endpoints are grouped under /api/*. Long-running work (Zotero sync, AI
analysis) returns a job id immediately; poll GET /api/jobs/{id}.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, jobs
from .analysis import AnalysisError, get_analyzer
from .config import STATIC_DIR, get_settings
from .specs import extract_text
from .store import Store

# Lazily-created singletons (so tests can point BINDING_DATA_DIR elsewhere).
_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _store = Store(settings.data_dir / "library.json")
    return _store


def create_app() -> FastAPI:
    app = FastAPI(title="BindingSolution", version=__version__)

    # ── status ───────────────────────────────────────────────────────
    @app.get("/api/status")
    def status() -> dict:
        s = get_settings()
        meta = get_store().get_meta()
        return {
            "version": __version__,
            "anthropic_configured": s.anthropic_configured,
            "anthropic_model": s.model,
            "using_mock_llm": s.mock_llm or not s.anthropic_api_key,
            "zotero_configured": s.zotero_configured,
            "zotero_mode": s.zotero_mode,
            "library": {
                "source": meta.get("source"),
                "last_synced": meta.get("last_synced"),
                "num_projects": len(get_store().get_projects()),
            },
        }

    # ── library: sync / load ─────────────────────────────────────────
    @app.post("/api/library/sync")
    def sync_library(payload: dict = Body(default={})) -> dict:
        source = (payload or {}).get("source", "zotero")
        if source == "demo":
            return _run_demo_sync()
        return _run_zotero_sync()

    @app.get("/api/projects")
    def list_projects() -> dict:
        projects = get_store().get_projects()
        # Strip heavy item lists from the list view; keep counts + category.
        summary = []
        for proj in projects.values():
            summary.append({
                "key": proj["key"],
                "name": proj["name"],
                "short_name": proj.get("short_name"),
                "num_items": proj.get("num_items", len(proj.get("items", []))),
                "category": proj.get("category"),
            })
        summary.sort(key=lambda p: p["name"].lower())
        return {"projects": summary, "meta": get_store().get_meta()}

    @app.get("/api/projects/{key}")
    def get_project(key: str) -> dict:
        proj = get_store().get_project(key)
        if proj is None:
            raise HTTPException(404, "Project not found")
        return proj

    # ── AI: categorize ───────────────────────────────────────────────
    @app.post("/api/projects/{key}/categorize")
    def categorize(key: str) -> dict:
        store = get_store()
        proj = store.get_project(key)
        if proj is None:
            raise HTTPException(404, "Project not found")
        analyzer = get_analyzer(get_settings())

        def work(job: jobs.Job) -> dict:
            job.set_progress(0, 1, f"Categorizing {proj['name']}…")
            category = analyzer.categorize_project(proj)
            store.set_project_category(key, category)
            job.set_progress(1, 1, "Done")
            return {"key": key, "category": category}

        return _start("categorize", work)

    @app.post("/api/projects/categorize-all")
    def categorize_all() -> dict:
        store = get_store()
        projects = list(store.get_projects().values())
        analyzer = get_analyzer(get_settings())

        def work(job: jobs.Job) -> dict:
            total = len(projects)
            done = []
            for i, proj in enumerate(projects, start=1):
                job.set_progress(i - 1, total, f"Categorizing {proj['name']}…")
                category = analyzer.categorize_project(proj)
                store.set_project_category(proj["key"], category)
                done.append(proj["key"])
            job.set_progress(total, total, "Done")
            return {"categorized": done}

        return _start("categorize-all", work)

    # ── AI: connections ──────────────────────────────────────────────
    @app.post("/api/connections")
    def connections() -> dict:
        store = get_store()
        projects = list(store.get_projects().values())
        if len(projects) < 2:
            raise HTTPException(400, "Need at least 2 projects to find connections.")
        analyzer = get_analyzer(get_settings())

        def work(job: jobs.Job) -> dict:
            job.set_progress(0, 1, "Finding connections across projects…")
            result = analyzer.find_connections(projects)
            store.set_connections({**result, "generated_at": _now()})
            job.set_progress(1, 1, "Done")
            return result

        return _start("connections", work)

    @app.get("/api/connections")
    def get_connections() -> dict:
        return {"connections": get_store().get_connections()}

    # ── AI: reading strategy ─────────────────────────────────────────
    @app.post("/api/strategies")
    def make_strategy(payload: dict = Body(...)) -> dict:
        store = get_store()
        goal = (payload or {}).get("goal", "")
        mode = (payload or {}).get("mode", "manual")
        keys = (payload or {}).get("project_keys", [])
        all_projects = store.get_projects()

        if mode == "auto" or not keys:
            # Let the agent decide: use the suggested combination if we have
            # one, else everything.
            conn = store.get_connections()
            keys = (conn or {}).get("suggested_combination") or list(all_projects.keys())

        projects = [all_projects[k] for k in keys if k in all_projects]
        if not projects:
            raise HTTPException(400, "No valid projects selected.")
        analyzer = get_analyzer(get_settings())

        def work(job: jobs.Job) -> dict:
            job.set_progress(0, 1, "Designing a reading strategy…")
            result = analyzer.reading_strategy(projects, goal)
            saved = store.add_strategy({
                "goal": goal,
                "mode": mode,
                "project_keys": [p["key"] for p in projects],
                "plan": result,
            })
            job.set_progress(1, 1, "Done")
            return saved

        return _start("strategy", work)

    @app.get("/api/strategies")
    def list_strategies() -> dict:
        return {"strategies": get_store().list_strategies()}

    @app.delete("/api/strategies/{strategy_id}")
    def delete_strategy(strategy_id: str) -> dict:
        if not get_store().delete_strategy(strategy_id):
            raise HTTPException(404, "Strategy not found")
        return {"deleted": strategy_id}

    # ── specs: upload + analyze ──────────────────────────────────────
    @app.post("/api/specs")
    async def upload_spec(
        file: UploadFile | None = File(default=None),
        title: str = Form(default=""),
        text: str = Form(default=""),
    ) -> dict:
        if file is not None:
            raw = await file.read()
            try:
                content = extract_text(file.filename or "spec", raw)
            except RuntimeError as exc:
                raise HTTPException(400, str(exc))
            spec_title = title.strip() or (file.filename or "Untitled spec")
        elif text.strip():
            content = text.strip()
            spec_title = title.strip() or "Pasted specification"
        else:
            raise HTTPException(400, "Provide a file or some text.")

        if len(content) < 20:
            raise HTTPException(400, "The specification is too short to analyze.")

        spec = get_store().add_spec({"title": spec_title, "text": content})
        return spec

    @app.get("/api/specs")
    def list_specs() -> dict:
        # Trim the full text from the list view.
        specs = []
        for spec in get_store().list_specs():
            specs.append({
                "id": spec["id"],
                "title": spec["title"],
                "status": spec.get("status"),
                "created_at": spec["created_at"],
                "preview": (spec.get("text", "")[:240]),
                "num_assessed": len(spec.get("analysis", {})),
            })
        return {"specs": specs}

    @app.get("/api/specs/{spec_id}")
    def get_spec(spec_id: str) -> dict:
        spec = get_store().get_spec(spec_id)
        if spec is None:
            raise HTTPException(404, "Spec not found")
        return spec

    @app.delete("/api/specs/{spec_id}")
    def delete_spec(spec_id: str) -> dict:
        if not get_store().delete_spec(spec_id):
            raise HTTPException(404, "Spec not found")
        return {"deleted": spec_id}

    @app.post("/api/specs/{spec_id}/analyze")
    def analyze_spec(spec_id: str, payload: dict = Body(default={})) -> dict:
        store = get_store()
        spec = store.get_spec(spec_id)
        if spec is None:
            raise HTTPException(404, "Spec not found")

        keys = (payload or {}).get("project_keys") or []
        all_projects = store.get_projects()
        if keys:
            projects = [all_projects[k] for k in keys if k in all_projects]
        else:
            projects = list(all_projects.values())

        papers = [(p["key"], it) for p in projects for it in p["items"]]
        if not papers:
            raise HTTPException(400, "No papers to analyze. Sync a library first.")

        analyzer = get_analyzer(get_settings())
        spec_text = spec["text"]

        def work(job: jobs.Job) -> dict:
            total = len(papers)
            store.update_spec(spec_id, status="analyzing")
            results: dict[str, dict] = {}
            for i, (project_key, paper) in enumerate(papers, start=1):
                job.set_progress(i - 1, total, f"Assessing “{paper['title'][:60]}”…")
                assessment = analyzer.assess_paper(spec_text, paper)
                assessment["project_key"] = project_key
                assessment["title"] = paper["title"]
                results[paper["key"]] = assessment
                # Persist incrementally so progress survives an interruption.
                if i % 5 == 0:
                    store.merge_spec_analysis(spec_id, results)
            store.merge_spec_analysis(spec_id, results)
            store.update_spec(spec_id, status="analyzed")
            job.set_progress(total, total, "Done")
            ranked = sorted(results.values(), key=lambda r: r.get("score", 0), reverse=True)
            return {"spec_id": spec_id, "assessed": len(results), "top": ranked[:5]}

        return _start("analyze-spec", work)

    # ── jobs ─────────────────────────────────────────────────────────
    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return job.to_dict()

    # ── frontend ─────────────────────────────────────────────────────
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/")
        def index() -> Any:
            return FileResponse(STATIC_DIR / "index.html")

    return app


# ── helpers ──────────────────────────────────────────────────────────
def _now() -> float:
    import time

    return time.time()


def _start(kind: str, fn) -> dict:
    job = jobs.start(kind, fn)
    return {"job_id": job.id, "kind": kind}


def _run_demo_sync() -> dict:
    from .demo_data import demo_projects

    store = get_store()

    def work(job: jobs.Job) -> dict:
        job.set_progress(0, 1, "Loading demo library…")
        projects = demo_projects()
        store.replace_projects(projects, source="demo")
        job.set_progress(1, 1, "Done")
        return {"num_projects": len(projects), "source": "demo"}

    return _start("sync", work)


def _run_zotero_sync() -> dict:
    settings = get_settings()
    if not settings.zotero_configured:
        raise HTTPException(
            400,
            "Zotero is not configured. Add ZOTERO_LIBRARY_ID + ZOTERO_API_KEY to .env "
            "(or set ZOTERO_LOCAL=true), or load the demo library.",
        )
    store = get_store()

    def work(job: jobs.Job) -> dict:
        from .zotero_client import fetch_projects

        def progress(cur: int, total: int, msg: str) -> None:
            job.set_progress(cur, total, f"Syncing “{msg}”…")

        try:
            projects = fetch_projects(settings, progress)
        except Exception as exc:
            raise AnalysisError(f"Zotero sync failed: {exc}") from exc
        store.replace_projects(projects, source=settings.zotero_mode or "zotero")
        job.set_progress(len(projects), len(projects), "Done")
        return {"num_projects": len(projects), "source": settings.zotero_mode}

    return _start("sync", work)
