"""End-to-end API tests, running fully offline (MOCK_LLM=true)."""
from conftest import run_job


def _load_demo(client):
    start = client.post("/api/library/sync", json={"source": "demo"}).json()
    return run_job(client, start)


def test_status_reports_mock_mode(client):
    body = client.get("/api/status").json()
    assert body["using_mock_llm"] is True
    assert body["anthropic_model"]  # a model id is always reported


def test_purge_library(client):
    _load_demo(client)
    client.post(
        "/api/specs",
        data={"text": "We study fairness and calibration in recommender systems using causal inference.", "title": "Aim"},
    )
    start = client.post("/api/strategies", json={"goal": "read", "mode": "auto"}).json()
    run_job(client, start)
    assert client.delete("/api/library").status_code == 200
    assert client.get("/api/projects").json()["projects"] == []
    assert client.get("/api/specs").json()["specs"] == []
    assert client.get("/api/strategies").json()["strategies"] == []
    assert client.get("/api/connections").json()["connections"] is None
    assert client.delete("/api/library").status_code == 400


def test_demo_sync_loads_projects(client):
    result = _load_demo(client)
    assert result["num_projects"] == 6
    projects = client.get("/api/projects").json()["projects"]
    assert len(projects) == 6
    assert {p["name"] for p in projects} >= {"Graph Neural Networks", "Fairness in ML"}
    usable = [p for p in projects if p["usable"]]
    inactive = [p for p in projects if not p["usable"]]
    assert len(usable) == 4
    assert len(inactive) == 2
    assert {p["inactive_reason"] for p in inactive} == {"empty", "single"}


def test_categorize_rejects_inactive_collection(client):
    _load_demo(client)
    inactive = [p for p in client.get("/api/projects").json()["projects"] if not p["usable"]]
    assert len(inactive) == 2
    for proj in inactive:
        resp = client.post(f"/api/projects/{proj['key']}/categorize")
        assert resp.status_code == 400


def test_categorize_project(client):
    _load_demo(client)
    key = client.get("/api/projects").json()["projects"][0]["key"]
    start = client.post(f"/api/projects/{key}/categorize").json()
    run_job(client, start)
    proj = client.get(f"/api/projects/{key}").json()
    assert proj["category"]["discipline"]
    assert proj["category"]["themes"]
    assert proj["category"]["keywords"]


def test_connections_need_two_projects(client):
    # Empty library → 400
    resp = client.post("/api/connections")
    assert resp.status_code == 400


def test_connections_after_demo(client):
    _load_demo(client)
    start = client.post("/api/connections").json()
    run_job(client, start)
    conn = client.get("/api/connections").json()["connections"]
    assert conn["overview"]
    # The demo data deliberately shares tags ('recommenders', 'causal', ...) across projects.
    assert len(conn["shared_threads"]) >= 1
    assert conn["suggested_combination"]


def test_reading_strategy_manual(client):
    _load_demo(client)
    projects = [p for p in client.get("/api/projects").json()["projects"] if p["usable"]]
    keys = [projects[0]["key"], projects[1]["key"]]
    paper_count = projects[0]["num_items"] + projects[1]["num_items"]
    start = client.post("/api/strategies", json={"goal": "connect these", "mode": "manual", "project_keys": keys}).json()
    saved = run_job(client, start)
    assert len(saved["plan"]["sequence"]) == paper_count
    assert saved["plan"]["schedule"]["total_minutes"] > 0
    assert all(step.get("read_minutes") for step in saved["plan"]["sequence"])
    listed = client.get("/api/strategies").json()["strategies"]
    assert len(listed) == 1
    # delete
    sid = listed[0]["id"]
    assert client.delete(f"/api/strategies/{sid}").status_code == 200
    assert client.get("/api/strategies").json()["strategies"] == []


def test_strategy_from_spec(client):
    _load_demo(client)
    spec = client.post(
        "/api/specs",
        data={
            "text": "We study fairness and calibration in recommender systems using causal inference and graphs.",
            "title": "Fairness aim",
        },
    ).json()
    run_job(client, client.post(f"/api/specs/{spec['id']}/analyze", json={}).json())
    start = client.post("/api/strategies", json={"spec_id": spec["id"], "goal": ""}).json()
    saved = run_job(client, start)
    assert saved["mode"] == "spec"
    assert saved["spec_id"] == spec["id"]
    assert saved["plan"]["spec_id"] == spec["id"]
    assert saved["plan"]["sequence"]
    for step in saved["plan"]["sequence"]:
        assert step.get("spec_relevance") in {"core", "supporting"}
        assert step.get("spec_why")
        assert step.get("scheduled_day")
    assert saved["plan"]["schedule"]["estimated_days"] >= 1


def test_reading_strategy_auto_mode(client):
    _load_demo(client)
    start = client.post("/api/strategies", json={"goal": "", "mode": "auto"}).json()
    saved = run_job(client, start)
    assert saved["plan"]["sequence"]
    assert saved["mode"] == "auto"


def test_paper_groups(client):
    _load_demo(client)
    start = client.post("/api/groups").json()
    result = run_job(client, start)
    assert result["groups"]
    assert result["overview"]
    grouped_keys: list[str] = []
    for grp in result["groups"]:
        grouped_keys.extend(grp["paper_keys"])
        assert grp["papers"]
        assert len(grp["papers"]) == len(grp["paper_keys"])
    assert len(grouped_keys) == len(set(grouped_keys))
    stored = client.get("/api/groups").json()["paper_groups"]
    assert stored["stats"]["num_groups"] == len(result["groups"])
    ungrouped_keys = {p["paper_key"] for p in stored.get("ungrouped") or []}
    assert "S1" in ungrouped_keys  # demo single-paper collection


def test_spec_discover_pubmed(client):
    _load_demo(client)
    spec = client.post(
        "/api/specs",
        data={
            "text": "We study fairness and calibration in recommender systems using causal inference.",
            "title": "Fairness aim",
        },
    ).json()
    start = client.post(f"/api/specs/{spec['id']}/discover", json={}).json()
    result = run_job(client, start)
    assert result["discovered"] > 0
    full = client.get(f"/api/specs/{spec['id']}").json()
    assert len(full["discoveries"]) == result["discovered"]
    assert result["discovered"] <= 5
    for hit in full["discoveries"]:
        assert hit.get("title")
        assert hit.get("url")
        assert hit.get("summary")
        assert hit.get("relevance_explanation")
        assert hit.get("score", 0) >= 55


def test_spec_upload_text_and_analyze(client):
    _load_demo(client)
    spec = client.post(
        "/api/specs",
        data={"text": "We study fairness and calibration in recommender systems using causal inference and graphs.", "title": "My grant aim"},
    ).json()
    assert spec["id"]
    start = client.post(f"/api/specs/{spec['id']}/analyze", json={}).json()
    result = run_job(client, start)
    assert result["screened"] > 0
    assert result["relevant"] > 0
    assert result["relevant"] <= result["screened"]
    full = client.get(f"/api/specs/{spec['id']}").json()
    assert full["status"] == "analyzed"
    assert full["num_screened"] == result["screened"]
    for assessment in full["analysis"].values():
        assert assessment["relevance"] in {"core", "supporting"}
        assert assessment["relevance_explanation"]


def test_spec_rejects_too_short(client):
    resp = client.post("/api/specs", data={"text": "too short"})
    assert resp.status_code == 400


def test_spec_rejects_irrelevant_text(client):
    resp = client.post(
        "/api/specs",
        data={
            "text": (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
            ),
            "title": "Not a spec",
        },
    )
    assert resp.status_code == 400
    assert "project specification" in resp.json()["detail"].lower()


def test_spec_rejects_shopping_list(client):
    resp = client.post(
        "/api/specs",
        data={
            "text": "Shopping list for Saturday: buy milk, eggs, bread, butter, and bananas.",
            "title": "Groceries",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]


def test_spec_pdf_upload(client):
    _load_demo(client)
    pdf_bytes = _tiny_pdf("Fairness and causal inference in recommender systems")
    resp = client.post(
        "/api/specs",
        files={"file": ("aim.pdf", pdf_bytes, "application/pdf")},
        data={"title": "PDF aim"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "PDF aim"


def test_spec_docx_upload(client):
    from tests.test_specs import _docx_bytes

    _load_demo(client)
    body = (
        "We study fairness and calibration in recommender systems using causal "
        "inference and graph-based methods for literature review planning."
    )
    resp = client.post(
        "/api/specs",
        files={
            "file": (
                "grant_aim.docx",
                _docx_bytes(body),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"title": "Word aim"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "Word aim"


def _tiny_pdf(text: str) -> bytes:
    """Build a minimal one-page PDF with a line of text (no external deps)."""
    content = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n0 %d\n" % (len(objs) + 1)
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += b"%010d 00000 n \n" % off
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref_pos)
    return pdf


def test_index_page_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "BindingSolution" in resp.text
