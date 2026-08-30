from django.test import TestCase
from capsules.utils import chunk_text_by_pages

class ChunkingTests(TestCase):
    def test_small_document_chunking(self):
        pages = {1: "This is a short test document."}
        chunks = chunk_text_by_pages(pages, chunk_size=1000, overlap=200)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]['page_number'], 1)
        self.assertEqual(chunks[0]['chunk_index'], 0)
        self.assertEqual(chunks[0]['text'], "This is a short test document.")

    def test_large_document_chunking(self):
        # A text with 1200 characters, so it should split into 2 chunks with overlap.
        long_text = "A" * 1200
        pages = {1: long_text}
        chunks = chunk_text_by_pages(pages, chunk_size=1000, overlap=200)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(len(chunks[0]['text']), 1000)
        self.assertEqual(len(chunks[1]['text']), 400) # 1200 - 800 (start of second chunk) = 400
        self.assertEqual(chunks[0]['chunk_index'], 0)
        self.assertEqual(chunks[1]['chunk_index'], 1)
