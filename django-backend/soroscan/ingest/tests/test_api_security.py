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
        """Verify that requests exceeding the limit return 413."""
        # Use 'record-event' because it is a POST endpoint
        url = reverse("record-event")
        
        # We make the payload specifically larger than 100 bytes
        large_data = json.dumps({"contract_id": "x" * 150})
        
        # Login to bypass any potential permission checks that might run before middleware
        self.client.force_login(self.user)
        
        response = self.client.post(
            url, 
            data=large_data, 
            content_type="application/json"
        )
        
        # This should now return 413 because our middleware hits it before the view
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json().get("error"), "Payload Too Large")

    @override_settings(DEPRECATED_ENDPOINTS={"/api/ingest/audit-trail/": {"sunset": "2026-12-31", "replacement": "/graphql/"}})
    def test_deprecation_headers(self):
        self.client.force_login(self.user)
        url = reverse("audit-trail")
        response = self.client.get(url)
        
        # Use .headers for Django 3.2+ / 4.x compatibility in CI
        self.assertEqual(response.headers.get("Deprecation"), "true")
        self.assertEqual(response.headers.get("Sunset"), "2026-12-31")