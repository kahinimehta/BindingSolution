"""Job progress: indeterminate steps and message formatting."""
import time

from conftest import run_job


def _load_demo(client):
    start = client.post("/api/library/sync", json={"source": "demo"}).json()
    return run_job(client, start)


def _poll_until_done(client, job_id, *, on_progress=None, timeout=4.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        last = job
        if on_progress:
            on_progress(job)
        if job["status"] == "done":
            return job
        if job["status"] == "error":
            raise AssertionError(job["error"])
        time.sleep(0.01)
    raise AssertionError(f"job did not finish: {last}")


def _check_indeterminate(job, bucket: list) -> None:
    p = job["progress"]
    msg = p.get("message", "")
    assert "…" not in msg
    assert not msg.endswith("...")
    if p.get("indeterminate"):
        bucket.append(True)


def test_connections_analyze_step_is_indeterminate(client, monkeypatch):
    _load_demo(client)
    import app.analysis as analysis_mod

    orig = analysis_mod.Analyzer.find_connections

    def slow_find(self, projects):
        time.sleep(0.12)
        return orig(self, projects)

    monkeypatch.setattr(analysis_mod.Analyzer, "find_connections", slow_find)

    start = client.post("/api/connections").json()
    saw_analyze = False

    def on_progress(job):
        nonlocal saw_analyze
        p = job["progress"]
        msg = p.get("message", "")
        assert "…" not in msg
        if msg.startswith("Preparing "):
            assert not p.get("indeterminate")
        if msg.startswith("Analyzing connections"):
            saw_analyze = True
            assert p.get("indeterminate")

    _poll_until_done(client, start["job_id"], on_progress=on_progress)
    assert saw_analyze


def test_grouping_analyze_step_is_indeterminate(client, monkeypatch):
    _load_demo(client)
    import app.analysis as analysis_mod

    orig = analysis_mod.Analyzer.find_paper_groups

    def slow_groups(self, projects):
        time.sleep(0.12)
        return orig(self, projects)

    monkeypatch.setattr(analysis_mod.Analyzer, "find_paper_groups", slow_groups)

    start = client.post("/api/groups").json()
    saw_analyze = False

    def on_progress(job):
        nonlocal saw_analyze
        p = job["progress"]
        msg = p.get("message", "")
        assert "…" not in msg
        if msg.startswith("Preparing "):
            assert not p.get("indeterminate")
        if msg.startswith("Analyzing "):
            saw_analyze = True
            assert p.get("indeterminate")

    _poll_until_done(client, start["job_id"], on_progress=on_progress)
    assert saw_analyze


def test_reading_plan_job_uses_indeterminate_progress(client, monkeypatch):
    _load_demo(client)
    import app.analysis as analysis_mod

    orig = analysis_mod.Analyzer.reading_strategy

    def slow_strategy(self, projects, goal):
        time.sleep(0.12)
        return orig(self, projects, goal)

    monkeypatch.setattr(analysis_mod.Analyzer, "reading_strategy", slow_strategy)

    projects = client.get("/api/projects").json()["projects"]
    keys = [p["key"] for p in projects if p.get("usable")][:2]
    start = client.post("/api/strategies", json={"goal": "read", "mode": "manual", "project_keys": keys}).json()
    flags: list[bool] = []
    _poll_until_done(
        client,
        start["job_id"],
        on_progress=lambda j: _check_indeterminate(j, flags),
    )
    assert flags


def test_strategy_uses_indeterminate_progress(client, monkeypatch):
    _load_demo(client)
    import app.analysis as analysis_mod

    orig = analysis_mod.Analyzer.reading_strategy

    def slow_strategy(self, projects, goal):
        time.sleep(0.12)
        return orig(self, projects, goal)

    monkeypatch.setattr(analysis_mod.Analyzer, "reading_strategy", slow_strategy)

    start = client.post("/api/strategies", json={"goal": "read", "mode": "auto"}).json()
    flags: list[bool] = []
    _poll_until_done(
        client,
        start["job_id"],
        on_progress=lambda j: _check_indeterminate(j, flags),
    )
    assert flags
