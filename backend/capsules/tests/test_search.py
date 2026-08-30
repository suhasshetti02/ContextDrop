from django.test import TestCase
from rest_framework.test import APIClient
from capsules.models import Capsule, DocumentChunk
from unittest.mock import patch
from django.conf import settings
from django.db import connection

class VectorSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.capsule = Capsule.objects.create(slug='searchme', domain='general')
        
        # Insert chunk with raw sql to handle vector
        with connection.cursor() as cursor:
            vector_str = "[" + ",".join(["0.1"] * 768) + "]"
            cursor.execute(
                "INSERT INTO capsules_documentchunk (capsule_id, text, page_number, section_title, chunk_index, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s::vector)",
                [str(self.capsule.id), "Test chunk text", 1, "", 0, vector_str]
            )

    @patch('capsules.views.get_embedding')
    def test_search_success(self, mock_get_embedding):
        mock_get_embedding.return_value = [0.1] * 768
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + getattr(settings, 'INTERNAL_API_KEY', 'default-internal-secret-key-12345'))
        
        response = self.client.post(f'/api/capsules/{self.capsule.slug}/search', {'question': 'Test question'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['chunks']), 1)
        self.assertEqual(response.data['chunks'][0]['text'], "Test chunk text")

    def test_search_unauthorized(self):
        response = self.client.post(f'/api/capsules/{self.capsule.slug}/search', {'question': 'Test question'}, format='json')
        self.assertEqual(response.status_code, 401)
