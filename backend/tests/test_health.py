"""Health and root endpoint tests."""


def test_root_index(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["docs"] == "/docs"


def test_root_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "FastAPI + SQLAlchemy + MySQL" in data["architecture"]


def test_api_v1_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "attendance" in data["pipelines"]
    assert "infrastructure" in data["pipelines"]
