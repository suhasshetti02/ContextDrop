# ContextDrop — Share Documents That Answer Back

ContextDrop turns a document or web URL into a shareable Q&A capsule. A creator ingests content; readers ask questions through a chat interface; the backend retrieves relevant document chunks and streams grounded responses with source references.

> **Project status:** A multi-service prototype with a React/Vite client, Django REST API, and a Node/Express SSE service. External model providers and PostgreSQL/Redis must be configured separately.

## Implemented capabilities

- Document and URL ingestion for PDF, TXT, and web content.
- Capsule creation, access controls, and shareable capsule routes.
- Text extraction and structure-aware chunking.
- Embedding generation and PostgreSQL vector storage with pgvector / HNSW migrations.
- Semantic retrieval and response grounding with source/page citations.
- SSE-based response streaming through a separate Express service.
- Redis-backed request limiting in the SSE service.
- Inter-service request signing using HMAC-SHA256 and timestamp checks.
- SSRF-related URL validation in the ingestion code.
- Capsule analytics and unanswered-question views.
- Evaluation scripts and a small retrieval question set.

## Architecture

```text
React + TypeScript + Vite
   ├── Django REST API
   │     ├── capsule / ingestion / retrieval logic
   │     └── PostgreSQL + pgvector
   └── Express SSE service
         ├── Redis rate-limit checks
         ├── internal Django API calls
         └── streamed LLM response
```

The README and code identify Groq / Ollama for chat generation and OpenAI / Nomic / Ollama embedding options. Provider choice depends on runtime configuration; model names in documentation are not proof that a provider key or model endpoint is configured.

## Technology

- Frontend: React, TypeScript, Vite.
- Ingestion API: Python, Django, Django REST Framework.
- Retrieval storage: PostgreSQL with pgvector.
- Streaming: Node.js, Express, Server-Sent Events.
- Rate limiting: Redis.
- Embeddings / generation: provider adapters for hosted or local model endpoints.
- Evaluation: retrieval question set and Recall@K script.

## Repository layout

- `frontend/` — React client and analytics UI.
- `backend/contextdrop/` — Django project settings and routing.
- `backend/capsules/` — capsule models, views, ingestion, retrieval and tests.
- `sse-server/` — Express streaming server and tests.
- `evaluation/` — questions and retrieval evaluation.
- `docker-compose.yml` — local database/cache infrastructure.
- `render.yaml` — deployment configuration.

## Run locally

Prerequisites: Docker / Docker Compose, Python 3.10+, Node.js 18+, and configured provider credentials as needed.

1. Start infrastructure from the repository root:

```bash
docker-compose up -d
```

2. Django API:

```bash
cd backend
python -m venv .venv
# Activate the environment
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

3. SSE server:

```bash
cd sse-server
npm install
cp .env.example .env
npm start
```

4. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Check the service-specific environment example files and deployment configuration for port numbers, database settings, internal API secrets, Redis URL, model provider, and API keys. Do not assume a local provider is available unless it is running and configured.

## Testing and evaluation

- Django tests are under `backend/capsules/tests/` and cover authentication, chunking, ingestion, search, and SSRF-related cases.
- Additional HMAC logic tests are under `backend/capsules/test_hmac_logic.py`.
- SSE rate-limit tests are under `sse-server/test/`.
- Retrieval evaluation is under `evaluation/`; inspect the evaluation README and dataset before interpreting its scores.

## Security and known limitations

- The system handles user-supplied files and URLs. Enforce upload limits, content-type validation, safe file storage, and SSRF protections at every ingestion boundary.
- Keep internal HMAC secrets, model-provider keys, database passwords, and Redis credentials out of source control.
- A successful retrieval score on the small included evaluation set is not a general accuracy guarantee.
- LLM output can still be incorrect; source references show retrieved context, not an independent proof that every generated statement is true.
- Validate authorization and password-protected capsule behavior at the API boundary; hiding UI elements is not access control.
- Production deployment requires a managed PostgreSQL/pgvector database, Redis, persistent file handling, and correctly configured internal service URLs.

## License

See the repository for license and model/provider terms.
