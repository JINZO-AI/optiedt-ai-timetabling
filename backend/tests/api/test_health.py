from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests import factories


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_and_schema(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["checks"] == {"database": "ok", "schema": "ok"}


def test_security_headers_and_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": "abcdef123456"})
    assert response.headers["x-request-id"] == "abcdef123456"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_unknown_route_is_a_problem_document(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 404


def test_metrics_endpoint(client: TestClient) -> None:
    client.get("/api/v1/health/live")
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "optiedt_http_requests_total" in response.text


def test_system_status_is_for_administrators(client: TestClient, db: Session) -> None:
    factories.user(db, "viewer.one", [("viewer", None)])
    factories.login(client, "viewer.one")
    assert client.get("/api/v1/system/status").status_code == 403
    factories.user(db, "root.admin", [("system_admin", None)])
    factories.login(client, "root.admin")
    status = client.get("/api/v1/system/status").json()
    assert status["schema"]["revision"] == status["schema"]["expected"]
    assert status["queue"] == {
        "queued": 0,
        "running": 0,
        "oldest_queued_seconds": 0,
        "failed_last_day": 0,
    }
