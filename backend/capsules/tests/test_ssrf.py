from django.test import TestCase
from capsules.utils import safe_requests_get
import requests
from unittest.mock import patch, MagicMock

class SSRFProtectionTests(TestCase):
    def test_invalid_scheme(self):
        with self.assertRaises(ValueError) as context:
            safe_requests_get("ftp://example.com")
        self.assertIn("Invalid URL scheme", str(context.exception))

    def test_localhost(self):
        with self.assertRaises(ValueError) as context:
            safe_requests_get("http://localhost")
        self.assertIn("Disallowed IP address resolved", str(context.exception))

    def test_loopback_ip(self):
        with self.assertRaises(ValueError) as context:
            safe_requests_get("http://127.0.0.1")
        self.assertIn("Disallowed IP address resolved", str(context.exception))
        
    def test_private_ip(self):
        with self.assertRaises(ValueError) as context:
            safe_requests_get("http://192.168.1.1")
        self.assertIn("Disallowed IP address resolved", str(context.exception))

    @patch('requests.Session.get')
    def test_valid_public_url(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"Valid Content"]
        mock_get.return_value = mock_response

        res = safe_requests_get("http://example.com")
        self.assertEqual(res._content, b"Valid Content")
        mock_get.assert_called_once()
