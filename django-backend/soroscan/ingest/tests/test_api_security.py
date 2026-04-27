from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class ApiSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a user for authenticated endpoints
        self.user = User.objects.create_user(username='testuser', password='password')

    @override_settings(MAX_REQUEST_BODY_SIZE=100)
    def test_request_size_limit(self):
        """Verify that requests exceeding the limit return 413."""
        large_data = "x" * 150
        # health-check is public, making it ideal for size testing
        url = reverse("health-check")
        response = self.client.post(
            url, 
            data=large_data, 
            content_type="text/plain"
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"], "Payload Too Large")

    @override_settings(DEPRECATED_ENDPOINTS={"/api/ingest/audit-trail/": {"sunset": "2026-12-31", "replacement": "/graphql/"}})
    def test_deprecation_headers(self):
        """Verify that deprecated endpoints include correct headers."""
        self.client.force_login(self.user)
        # Note: The full path includes the 'api/ingest/' prefix from the main urls.py
        url = reverse("audit-trail")
        response = self.client.get(url)
        
        self.assertEqual(response["Deprecation"], "true")
        self.assertEqual(response["Sunset"], "2026-12-31")
        self.assertIn('rel="replacement"', response["Link"])