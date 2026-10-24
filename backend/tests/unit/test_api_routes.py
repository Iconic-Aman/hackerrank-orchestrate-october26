from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

TEST_SECRET = "test-secret-key"

@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET)
    return TestClient(app)

@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_SECRET}"}

def test_health_endpoint(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_unauthorized_without_token(client: TestClient) -> None:
    res = client.get("/api/v1/cases")
    assert res.status_code == 401

def test_unauthorized_with_wrong_token(client: TestClient) -> None:
    res = client.get("/api/v1/cases", headers={"Authorization": "Bearer wrong-token"})
    assert res.status_code == 401

def test_list_cases_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.get("/api/v1/cases?limit=10", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert len(data["cases"]) <= 10

def test_get_case_detail_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    list_res = client.get("/api/v1/cases?limit=1", headers=auth_headers)
    first_id = list_res.json()["cases"][0]["case_id"]
    res = client.get(f"/api/v1/cases/{first_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == first_id
    assert data["status"] in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE")

def test_audit_single_case_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    list_res = client.get("/api/v1/cases?limit=1", headers=auth_headers)
    first_id = list_res.json()["cases"][0]["case_id"]
    res = client.post(f"/api/v1/cases/{first_id}/audit", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == first_id
    assert data["status"] in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE")

def test_case_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.get("/api/v1/cases/invalid_case_99999", headers=auth_headers)
    assert res.status_code == 404

def test_stats_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    res = client.get("/api/v1/stats", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_cases"] > 0
    assert "complete_count" in data
    assert "incomplete_count" in data
