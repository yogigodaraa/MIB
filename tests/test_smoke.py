"""Smoke tests: the API starts, and the tension pipeline handles normal readings and spikes."""

from fastapi.testclient import TestClient

import main
from app.services.tension_monitoring import TensionMonitoringService


def test_health_endpoint_responds():
    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"]


def test_steady_readings_are_processed_with_high_confidence():
    service = TensionMonitoringService()
    for value in [40, 41, 39, 40, 42, 40, 41]:
        result = service.process_tension_reading("HOOK-1", value)

    assert result["is_outlier"] is False
    assert result["processed_value"] is not None
    assert result["confidence_score"] >= service.config["confidence_threshold"]


def test_sudden_spike_is_flagged_as_outlier_and_not_passed_through():
    service = TensionMonitoringService()
    for value in [40, 41, 39, 40, 42, 40, 41]:
        service.process_tension_reading("HOOK-1", value)

    result = service.process_tension_reading("HOOK-1", 400)

    assert result["is_outlier"] is True
    assert result["processed_value"] is None
    assert "OUTLIER_DETECTED" in result["quality_flags"]
