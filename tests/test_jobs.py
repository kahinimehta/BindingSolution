import time

from app import jobs


def test_list_jobs_empty(client):
    data = client.get("/api/jobs").json()
    assert data["jobs"] == []


def test_list_jobs_includes_sync_and_active_filter(client):
    start = client.post("/api/library/sync", json={"source": "demo"}).json()
    assert "job_id" in start

    listed = client.get("/api/jobs").json()["jobs"]
    assert any(j["id"] == start["job_id"] for j in listed)

    from tests.conftest import run_job

    run_job(client, start)
    job = client.get(f"/api/jobs/{start['job_id']}").json()
    assert job["status"] == "done"

    active = client.get("/api/jobs", params={"active": True}).json()["jobs"]
    assert all(j["status"] in ("queued", "running") for j in active)
    assert not any(j["id"] == start["job_id"] for j in active)


def test_cooperative_cancel_marks_job_cancelled():
    jobs.reset_registry()

    def work(job: jobs.Job) -> str:
        for _ in range(200):
            job.check_cancelled()
            time.sleep(0.005)
        return "done"

    job = jobs.start("test", work)
    time.sleep(0.03)
    assert jobs.cancel(job.id) is True

    deadline = time.time() + 3
    while time.time() < deadline:
        current = jobs.get(job.id)
        if current and current.status == "cancelled":
            break
        time.sleep(0.02)

    finished = jobs.get(job.id)
    assert finished is not None
    assert finished.status == "cancelled"
    assert finished.error == "Cancelled"
    assert finished.progress["message"] == "Cancelled"


def test_cancel_job_endpoint(client, monkeypatch):
    import app.server as server_mod
    from app.analysis import get_analyzer
    from app.config import get_settings

    client.post("/api/library/sync", json={"source": "demo"})

    analyzer = get_analyzer(get_settings())
    original = analyzer.categorize_project

    def slow_categorize(project):
        time.sleep(0.12)
        return original(project)

    monkeypatch.setattr(analyzer, "categorize_project", slow_categorize)
    monkeypatch.setattr(server_mod, "get_analyzer", lambda _settings: analyzer)

    start = client.post("/api/projects/categorize-all").json()
    time.sleep(0.03)
    resp = client.post(f"/api/jobs/{start['job_id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["id"] == start["job_id"]

    deadline = time.time() + 4
    status = None
    while time.time() < deadline:
        status = client.get(f"/api/jobs/{start['job_id']}").json()["status"]
        if status == "cancelled":
            break
        time.sleep(0.05)
    assert status == "cancelled"


def test_cancel_sets_cancelling_status_immediately(client):
    import threading
    import app.jobs as jobs_mod

    jobs_mod.reset_registry()
    started = threading.Event()
    release = threading.Event()

    def work(job: jobs.Job) -> str:
        started.set()
        release.wait(timeout=2)
        job.check_cancelled()
        return "done"

    job = jobs.start("test", work)
    assert started.wait(timeout=2)
    resp = client.post(f"/api/jobs/{job.id}/cancel")
    assert resp.status_code == 200
    body = client.get(f"/api/jobs/{job.id}").json()
    assert body["status"] == "cancelling"
    assert body["progress"]["message"] == "Cancelling…"
    release.set()
    deadline = __import__("time").time() + 3
    while __import__("time").time() < deadline:
        if client.get(f"/api/jobs/{job.id}").json()["status"] == "cancelled":
            break
        __import__("time").sleep(0.02)
    assert client.get(f"/api/jobs/{job.id}").json()["status"] == "cancelled"


def test_cancel_finished_job_returns_409(client):
    start = client.post("/api/library/sync", json={"source": "demo"}).json()
    from tests.conftest import run_job

    run_job(client, start)
    resp = client.post(f"/api/jobs/{start['job_id']}/cancel")
    assert resp.status_code == 409
