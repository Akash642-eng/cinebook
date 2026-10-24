from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "cinebook-api",
    }


def test_version_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json() == {
        "application": "cinebook",
        "version": "0.1.0",
    }


def test_movies_endpoint_returns_list():
    with TestClient(app) as client:
        response = client.get("/api/movies")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_metrics_endpoint_exposes_http_request_metrics():
    with TestClient(app) as client:
        health_response = client.get("/api/health")
        metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert metrics_response.status_code == 200
    assert "cinebook_http_requests_total" in metrics_response.text
    assert 'route="/api/health"' in metrics_response.text
    assert "cinebook_http_request_duration_seconds_bucket" in metrics_response.text
