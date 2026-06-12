"""Chat assistant — local shelf context, no re-upload."""
from conftest import run_job


def _load_demo(client):
    start = client.post("/api/library/sync", json={"source": "demo"}).json()
    return run_job(client, start)


def test_chat_requires_library(client):
    res = client.post("/api/chat", json={"message": "What papers do I have?"})
    assert res.status_code == 400


def test_chat_answers_with_demo_library(client):
    _load_demo(client)
    res = client.post("/api/chat", json={"message": "What collections are on my shelf?"})
    assert res.status_code == 200
    body = res.json()
    assert body["reply"]
    assert body["thread_id"]
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"


def test_chat_thread_continues(client):
    _load_demo(client)
    first = client.post("/api/chat", json={"message": "Tell me about connections"}).json()
    second = client.post("/api/chat", json={
        "message": "What about groups?",
        "thread_id": first["thread_id"],
    }).json()
    assert second["thread_id"] == first["thread_id"]
    assert len(second["messages"]) == 4


def test_chat_threads_list_and_get(client):
    _load_demo(client)
    client.post("/api/chat", json={"message": "Hello shelf"})
    threads = client.get("/api/chat/threads").json()["threads"]
    assert len(threads) == 1
    detail = client.get(f"/api/chat/threads/{threads[0]['id']}").json()["thread"]
    assert detail["messages"]


def test_chat_context_includes_projects(client):
    from app.chat_context import assemble_chat_context
    from app.server import get_store

    _load_demo(client)
    ctx = assemble_chat_context(get_store(), "fairness papers", {})
    assert "Fairness" in ctx or "DEMOFAIR" in ctx
    assert "Graph Neural Networks" in ctx or "DEMOGRAPH" in ctx


def test_purge_clears_chat_threads(client):
    _load_demo(client)
    client.post("/api/chat", json={"message": "Hi"})
    assert client.get("/api/chat/threads").json()["threads"]
    client.delete("/api/library")
    assert client.get("/api/chat/threads").json()["threads"] == []
