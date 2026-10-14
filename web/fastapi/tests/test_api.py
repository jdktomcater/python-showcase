import pytest
from fastapi.testclient import TestClient

from examples.hello import app as hello_app
from examples.tasks import TaskStore, app, get_store


@pytest.fixture
def client():
    # 每个测试使用独立存储，避免测试顺序影响结果。
    isolated_store = TaskStore()
    app.dependency_overrides[get_store] = lambda: isolated_store
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_hello_and_parameter_conversion():
    with TestClient(hello_app) as client:
        assert client.get("/hello").json() == {"message": "你好，世界！"}
        assert client.get("/items/1?detail=true").json() == {"item_id": 1, "detail": True}
        assert client.get("/items/abc").status_code == 422


def test_task_lifecycle(client):
    response = client.post("/tasks", json={"title": " 学习 FastAPI "})
    assert response.status_code == 201
    task = response.json()
    assert task == {"id": 1, "title": "学习 FastAPI", "completed": False}
    assert client.get("/tasks/1").json() == task
    assert client.put("/tasks/1", json={"title": "完成练习", "completed": True}).status_code == 200
    assert len(client.get("/tasks?completed=true").json()) == 1
    assert client.get("/tasks?completed=false").json() == []
    deleted = client.delete("/tasks/1")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/tasks/1").status_code == 404


@pytest.mark.parametrize("payload", [{"title": ""}, {"title": "   "}, {"title": "x" * 101}, {}, {"title": "x", "id": 99}])
def test_invalid_body(client, payload):
    assert client.post("/tasks", json=payload).status_code == 422
    assert client.get("/tasks").json() == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "completed=maybe"])
def test_invalid_query(client, query):
    assert client.get(f"/tasks?{query}").status_code == 422


def test_pagination_and_put_replacement(client):
    for title in ("A", "B", "C"):
        client.post("/tasks", json={"title": title, "completed": True})
    assert [t["title"] for t in client.get("/tasks?offset=1&limit=1").json()] == ["B"]
    response = client.put("/tasks/1", json={"title": "替换"})
    assert response.json()["completed"] is False


def test_missing_resource_and_invalid_path(client):
    assert client.get("/tasks/0").status_code == 422
    assert client.get("/tasks/abc").status_code == 422
    assert client.get("/tasks/999").json() == {"detail": "任务不存在"}
    assert client.put("/tasks/999", json={"title": "不存在"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404
