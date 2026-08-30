# ContextDrop Evaluation

This directory contains evaluation datasets and scripts to measure the quality of the ContextDrop RAG retrieval pipeline.

## Files
- `questions.json`: A small evaluation dataset mapping questions to expected text snippets that should be retrieved.
- `evaluate.py`: A Python script to calculate Recall@K against a running ContextDrop backend.

## Usage
1. Ingest a document that contains the expected text snippets (e.g., the ContextDrop README or a test file).
2. Note the generated capsule slug.
3. Run the evaluation script:
   ```bash
   python evaluate.py <capsule_slug>
   ```
4. The script will output the Recall@5 metric.
