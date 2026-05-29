"""Endpoint /metrics Prometheus (S21-T05).

Formato Prometheus parseavel; o contador de requests aumenta a cada request.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _health_total(metrics_text: str) -> float:
    """Soma http_requests_total do handler /health (registry e global/cumulativo)."""
    total = 0.0
    for v in re.findall(
        r'http_requests_total\{[^}]*handler="/health"[^}]*\}\s+([0-9.eE+]+)', metrics_text
    ):
        total += float(v)
    return total


def test_metrics_formato_prometheus() -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "# TYPE" in r.text
    assert "http_requests_total" in r.text


def test_metrics_conta_requests() -> None:
    before = _health_total(client.get("/metrics").text)
    for _ in range(3):
        assert client.get("/health").status_code == 200
    after = _health_total(client.get("/metrics").text)
    assert after >= before + 3
