from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class ApiSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')

    @override_settings(MAX_REQUEST_BODY_SIZE=100)
    def test_request_size_limit(self):
        """Verify that requests exceeding 100 bytes return 413."""
        url = reverse("health-check") # Matches path in ingest/urls.py
        large_data = json.dumps({"test": "x" * 200})
        
        response = self.client.post(
            url, 
            data=large_data, 
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 413)

    @override_settings(DEPRECATED_ENDPOINTS={"/api/ingest/audit-trail/": {"sunset": "2026-12-31", "replacement": "/graphql/"}})
    def test_deprecation_headers(self):
        self.client.force_login(self.user)
        url = reverse("audit-trail")
        response = self.client.get(url)
        
        # Use .headers for Django 3.2+ / 4.x compatibility in CI
        self.assertEqual(response.headers.get("Deprecation"), "true")
        self.assertEqual(response.headers.get("Sunset"), "2026-12-31")