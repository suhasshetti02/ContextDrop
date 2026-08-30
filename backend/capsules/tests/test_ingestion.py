from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from capsules.models import Capsule
import io
from django.core.files.uploadedfile import SimpleUploadedFile

class IngestionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('capsules.views.get_embedding')
    @patch('capsules.views.classify_domain')
    def test_ingest_txt_file(self, mock_classify, mock_get_embedding):
        mock_classify.return_value = 'general'
        mock_get_embedding.return_value = [0.1] * 768

        test_file = SimpleUploadedFile("test.txt", b"This is a test document.", content_type="text/plain")
        response = self.client.post('/api/ingest', {'file': test_file, 'ttl_days': 7}, format='multipart')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('slug', response.data)
        self.assertTrue(Capsule.objects.filter(slug=response.data['slug']).exists())

    def test_ingest_invalid_file(self):
        response = self.client.post('/api/ingest', {}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('No file uploaded and no URL provided', response.data.get('error', ''))
