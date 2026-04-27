from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class ApiSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')

    @override_settings(MAX_REQUEST_BODY_SIZE=100)
    def test_request_size_limit(self):
        """Verify that requests exceeding the limit return 413."""
        large_data = "x" * 150
        # Use 'record-event' because it explicitly allows POST requests
        url = reverse("record-event")
        # We need to authenticate to reach the view logic if CSRF/Auth triggers first
        self.client.force_login(self.user)
        
        response = self.client.post(
            url, 
            data=large_data, 
            content_type="text/plain"
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json().get("error"), "Payload Too Large")

    @override_settings(DEPRECATED_ENDPOINTS={"/api/ingest/audit-trail/": {"sunset": "2026-12-31", "replacement": "/graphql/"}})
    def test_deprecation_headers(self):
        """Verify that deprecated endpoints include correct headers."""
        self.client.force_login(self.user)
        url = reverse("audit-trail")
        response = self.client.get(url)
        
        # Use .get() and check exact casing used in middleware ('Deprecation')
        self.assertEqual(response.get("Deprecation"), "true")
        self.assertEqual(response.get("Sunset"), "2026-12-31")
        self.assertIn('rel="replacement"', response.get("Link", ""))