import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestReadinessView:
    def test_ready_when_db_and_cache_connected(self, api_client):
        url = reverse("readiness")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
        assert "components" in response.data

    def test_not_ready_when_db_fails(self, api_client, monkeypatch):
        from django.db import connection
        monkeypatch.setattr(connection, "cursor", lambda: (_ for _ in ()).throw(Exception("DB fail")))

        url = reverse("readiness")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "degraded"
        assert "database" in response.data["components"]

    def test_not_ready_when_cache_fails(self, api_client, monkeypatch):
        from django.core.cache import cache
        monkeypatch.setattr(cache, "get", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Redis fail")))

        url = reverse("readiness")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "degraded"
        assert "redis" in response.data["components"]