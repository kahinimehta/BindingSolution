"""Tiny thread-safe JSON persistence layer.

Everything the app knows (synced projects, AI analyses, strategies,
specs) lives in a single human-inspectable JSON file under `data/`
(gitignored). At personal-library scale this is simpler and more
transparent than a database.
"""
from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_EMPTY: dict[str, Any] = {
    "projects": {},      # collection key -> project dict (with items)
    "connections": None,  # latest cross-project analysis
    "strategies": [],     # newest first
    "specs": [],          # newest first
    "meta": {},           # library-level info (source, last_synced, ...)
}


class Store:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data = self._load()

    # ── plumbing ─────────────────────────────────────────────────────
    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return {**copy.deepcopy(_EMPTY), **data}
            except (json.JSONDecodeError, OSError):
                # Corrupt store: keep the bad file aside, start fresh.
                try:
                    self.path.rename(self.path.with_suffix(".corrupt"))
                except OSError:
                    pass
        return copy.deepcopy(_EMPTY)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    # ── projects ─────────────────────────────────────────────────────
    def replace_projects(self, projects: dict[str, dict], source: str) -> None:
        with self._lock:
            # Keep AI categorization for collections that survived the sync.
            for key, proj in projects.items():
                old = self._data["projects"].get(key)
                if old and old.get("category") and not proj.get("category"):
                    proj["category"] = old["category"]
            self._data["projects"] = projects
            self._data["meta"].update({"source": source, "last_synced": time.time()})
            self._save()

    def get_projects(self) -> dict[str, dict]:
        with self._lock:
            return copy.deepcopy(self._data["projects"])

    def get_project(self, key: str) -> dict | None:
        with self._lock:
            proj = self._data["projects"].get(key)
            return copy.deepcopy(proj) if proj else None

    def set_project_category(self, key: str, category: dict) -> None:
        with self._lock:
            proj = self._data["projects"].get(key)
            if proj is None:
                raise KeyError(key)
            proj["category"] = {**category, "generated_at": time.time()}
            self._save()

    # ── connections ──────────────────────────────────────────────────
    def set_connections(self, connections: dict) -> None:
        with self._lock:
            self._data["connections"] = connections
            self._save()

    def get_connections(self) -> dict | None:
        with self._lock:
            return copy.deepcopy(self._data["connections"])

    # ── reading strategies ───────────────────────────────────────────
    def add_strategy(self, strategy: dict) -> dict:
        with self._lock:
            strategy = {"id": uuid.uuid4().hex[:12], "created_at": time.time(), **strategy}
            self._data["strategies"].insert(0, strategy)
            self._save()
            return copy.deepcopy(strategy)

    def list_strategies(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._data["strategies"])

    def delete_strategy(self, strategy_id: str) -> bool:
        with self._lock:
            before = len(self._data["strategies"])
            self._data["strategies"] = [s for s in self._data["strategies"] if s["id"] != strategy_id]
            if len(self._data["strategies"]) != before:
                self._save()
                return True
            return False

    # ── project specs ────────────────────────────────────────────────
    def add_spec(self, spec: dict) -> dict:
        with self._lock:
            spec = {
                "id": uuid.uuid4().hex[:12],
                "created_at": time.time(),
                "status": "new",
                "analysis": {},
                "discoveries": [],
                "discover_status": "idle",
                **spec,
            }
            self._data["specs"].insert(0, spec)
            self._save()
            return copy.deepcopy(spec)

    def list_specs(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._data["specs"])

    def get_spec(self, spec_id: str) -> dict | None:
        with self._lock:
            for spec in self._data["specs"]:
                if spec["id"] == spec_id:
                    return copy.deepcopy(spec)
            return None

    def update_spec(self, spec_id: str, **fields: Any) -> dict:
        with self._lock:
            for spec in self._data["specs"]:
                if spec["id"] == spec_id:
                    spec.update(fields)
                    self._save()
                    return copy.deepcopy(spec)
            raise KeyError(spec_id)

    def merge_spec_analysis(self, spec_id: str, analysis: dict[str, dict]) -> None:
        """Merge per-paper results as analysis batches finish (partial progress survives errors)."""
        with self._lock:
            for spec in self._data["specs"]:
                if spec["id"] == spec_id:
                    spec.setdefault("analysis", {}).update(analysis)
                    self._save()
                    return
            raise KeyError(spec_id)

    def delete_spec(self, spec_id: str) -> bool:
        with self._lock:
            before = len(self._data["specs"])
            self._data["specs"] = [s for s in self._data["specs"] if s["id"] != spec_id]
            if len(self._data["specs"]) != before:
                self._save()
                return True
            return False

    # ── meta ─────────────────────────────────────────────────────────
    def get_meta(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data["meta"])

    def purge(self) -> None:
        """Wipe all local data — projects, analyses, plans, and specs."""
        with self._lock:
            self._data = copy.deepcopy(_EMPTY)
            self._save()
