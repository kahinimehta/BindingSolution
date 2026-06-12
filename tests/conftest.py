import os
import tempfile

import pytest

# Force offline, deterministic mode BEFORE app import.
os.environ["MOCK_LLM"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""


@pytest.fixture()
def client(tmp_path):
    # Each test gets its own data dir + a fresh store, so libraries never leak
    # between tests.
    os.environ["BINDING_DATA_DIR"] = str(tmp_path)
    from fastapi.testclient import TestClient

    import app.jobs as job_mod
    import app.server as server

    job_mod.reset_registry()
    server._store = None
    return TestClient(server.create_app())


def run_job(client, start_response):
    """Poll a started job to completion (jobs run in background threads)."""
    import time

    job_id = start_response["job_id"]
    for _ in range(200):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == "done":
            return job["result"]
        if job["status"] == "error":
            raise AssertionError(f"job failed: {job['error']}")
        time.sleep(0.02)
    raise AssertionError("job did not finish in time")
