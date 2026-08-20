# 1. Project Overview

- **Project Name:** ContextDrop
- **One-Line Description:** A "TinyURL for understanding" that lets users upload documents or web links and generate a shareable, password-protected URL with an interactive, document-grounded AI chat.
- **Problem Statement:** Sharing static documents or lengthy articles is inefficient because readers often struggle to extract specific insights quickly.
- **Motivation:** To provide an instant, frictionless way for content creators (e.g., lawyers, academics, professionals) to share knowledge where readers can actively question the document rather than passively reading it.
- **Target Users:** Professionals, educators, and creators who frequently share complex documents (e.g., contracts, research papers, technical specs) and want to offer an interactive reading experience.
- **Objective:** Provide a fast, reliable, and secure platform for converting static files/links into context-aware LLM chatbots.
- **Current Implementation Status:** Functional MVP.
- **What is Complete:** 
  - PDF/TXT upload and web scraping.
  - Chunking and pgvector embedding generation.
  - Zero-shot domain classification and automated starter question generation.
  - Dynamic RAG (Retrieval-Augmented Generation) chat interface with Server-Sent Events (SSE) streaming.
  - Capsule dashboard with analytics and heatmaps.
- **What is Incomplete:** 
  - Thorough test suite (only a single exploratory scrape script exists).
  - Robust file handling (currently limited to basic text/PDF without OCR).
- **What is Simulated:** Nothing core is simulated, but there are frontend fallback mockups if the backend goes offline.
- **What is Experimental:** The dual-model fallback (Groq to local Ollama) and heuristic web scraping (Jina/Fandom specific bypasses).

# 2. Complete Tech Stack

| Category | Technology | Version | Actual Usage | Important Files | Why Used |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend** | React + TypeScript | 19.2.6 | SPA UI, state management, SSE handling | `frontend/src/App.tsx` | Modern, component-driven UI development. |
| **Build Tool** | Vite | 8.0.12 | Frontend bundling and dev server | `frontend/vite.config.ts`, `frontend/package.json` | Faster HMR and build times compared to Webpack/CRA. |
| **Backend API** | Django REST Framework | 5.0+ | Core API, ingestion, auth, db management | `backend/capsules/views.py` | Rapid API development, built-in ORM, admin dashboard. |
| **Streaming Server**| Node.js + Express | 4.19 | Handles SSE for real-time LLM chat | `sse-server/index.js` | Django synchronous workers aren't ideal for long-lived SSE connections; Node handles async streams better. |
| **Database** | PostgreSQL + pgvector | 15 | Relational data and vector similarity search | `docker-compose.yml` | Native vector storage alongside relational metadata. |
| **Cache/Limit** | Redis | 7 | Rate limiting for the SSE streaming endpoint | `sse-server/index.js` | High-performance memory store to prevent API abuse. |
| **AI/ML API** | Groq | N/A | Primary LLM for chat, domain classification | `sse-server/index.js`, `backend/capsules/utils.py` | Extremely fast inference (Llama-3.3-70b-versatile). |
| **AI/ML Local** | Ollama | N/A | Fallback LLM and Embeddings | `backend/capsules/utils.py` | Offline capability and cost savings using local models (Gemma4:e2b, nomic-embed-text). |
| **Deployment** | Render / Docker | N/A | `render.yaml` orchestrates deployment | `render.yaml`, `docker-compose.yml` | Simple PaaS deployment for multi-service apps. |

# 3. Repository Structure

| File/Folder | Purpose | Important Logic |
| :--- | :--- | :--- |
| `backend/` | Django Application | Contains the main API logic, models, and ML utility functions. |
| `backend/capsules/models.py` | Database Schema | Defines `Capsule`, `DocumentChunk`, `CapsuleAnalytic`, and `Tag`. |
| `backend/capsules/views.py` | API Controllers | Endpoints for ingestion, search, auth, and analytics. Raw SQL for pgvector. |
| `backend/capsules/utils.py` | ML / Processing Utilities | Handles PDF parsing, URL scraping, embedding API calls, and zero-shot classification. |
| `frontend/` | React Application | Contains the UI logic. |
| `frontend/src/App.tsx` | Main Frontend Logic | Giant single-file React component handling routing, SSE stream reading, and UI state. |
| `sse-server/` | Node.js Streaming Server | Microservice dedicated to streaming LLM responses to the frontend. |
| `sse-server/index.js` | Streaming Entry Point | Express app that rate-limits via Redis, fetches context from Django, calls Groq, and streams to client. |
| `docker-compose.yml` | Local Infrastructure | Defines PostgreSQL (pgvector) and Redis containers. |
| `render.yaml` | Production Deployment | Configuration for deploying Django and Node.js services to Render. |

# 4. Architecture

The system utilizes a microservice-inspired architecture separating the synchronous heavy lifting from the asynchronous streaming.

```mermaid
flowchart TD
    User([User]) -->|Uploads File/URL| React[React Frontend]
    User -->|Asks Question| React
    
    React -->|POST /api/ingest| Django[Django REST API]
    React -->|GET /stream| NodeSSE[Node.js SSE Server]
    
    Django -->|Write| Postgres[(PostgreSQL + pgvector)]
    Django -->|Generate Embeddings| Nomic/Ollama[Nomic/Ollama Embeddings API]
    Django -->|Zero-shot Classification| Groq1[Groq API (Llama3)]
    
    NodeSSE -->|Check Limits| Redis[(Redis)]
    NodeSSE -->|Internal Context Search| Django
    NodeSSE -->|Prompt + Context| Groq2[Groq API (Llama3)]
    Groq2 -->|Stream Tokens| NodeSSE
    NodeSSE -->|Stream to Client| React
    NodeSSE -->|Async Log| Django
```

# 5. End-to-End Data Flow

**Workflow: User Asks a Question in a Capsule**

1. **User Action:** The user types a question in the React frontend and hits send.
2. **Frontend SSE Connection:** `App.tsx` opens an EventSource connection to `sse-server/index.js` endpoint `/stream/:slug?q=...`.
3. **Rate Limiting:** Node.js checks the user's IP against Redis. If $>5$ requests/min, it rejects.
4. **Context Retrieval:** Node.js makes an internal POST request to Django (`/api/capsules/<slug>/search`), passing an `INTERNAL_API_KEY`.
5. **Vector Search (Django):** Django embeds the user's question, connects to PostgreSQL, and runs a pgvector `<=>` (cosine distance) query to find the top 5 closest `DocumentChunk`s.
6. **Prompt Assembly:** Django returns the chunks to Node.js. Node.js formats them into a system prompt, applying a domain-specific tone based on the capsule's domain.
7. **LLM Generation:** Node.js POSTs to the Groq API with `stream: true`.
8. **Streaming (Node.js -> React):** As Groq returns tokens, Node.js parses the JSON and immediately writes SSE `data:` payloads back to the React client.
9. **UI Update:** React appends incoming tokens to the chat bubble.
10. **Analytics Logging:** Once complete, Node.js fires an async POST back to Django to log the query (has it been answered, which page was cited) into `CapsuleAnalytic`.

# 6. Feature-by-Feature Explanation

## Document Ingestion & Chunking
### What it does
Takes a PDF, TXT, or URL and breaks it down into processable text chunks.
### Why it exists
LLMs have context window limits. We must embed smaller chunks of text to search against later (RAG).
### How it works
For PDFs, it extracts text page-by-page. For URLs, it uses BeautifulSoup (with heuristics for Jina and Fandom) to extract paragraphs. It then uses a sliding window (1000 chars, 200 overlap) to create chunks.
### Files involved
`backend/capsules/views.py` (ingest_document), `backend/capsules/utils.py` (chunk_text_by_pages).
### Edge cases
Scraping modern React/SPA websites fails because BeautifulSoup can't execute JS. Jina Reader API is used as a fallback heuristic.

## Vector Search (RAG)
### What it does
Finds the most relevant parts of the uploaded document given a user's question.
### Why it exists
Allows the LLM to answer questions using *only* the provided document context, preventing hallucinations.
### How it works
Embeds the question using Nomic/OpenAI/Ollama. Uses pgvector in PostgreSQL to calculate cosine distance (`<=>`) against stored document chunks.
### Files involved
`backend/capsules/views.py` (search_capsule).

## Domain Classification & Tone Adjustment
### What it does
Automatically detects if a document is legal, medical, academic, etc., and adjusts the chatbot's tone to match.
### Why it exists
A legal contract chatbot should sound different than a casual blog post chatbot.
### How it works
During ingestion, a zero-shot prompt is sent to an LLM to classify the first text chunk. At chat time, Node.js maps this domain to a specific system prompt modifier.
### Files involved
`backend/capsules/utils.py` (classify_domain), `sse-server/index.js` (domainTones dictionary).

# 7. Database Deep Dive

The database is PostgreSQL with the `pgvector` extension.

- **Capsule:** Represents a shared link. `id` (UUID), `slug` (short url), `domain` (classification), `expires_at`, `password_hash`, `suggested_questions` (JSON string).
- **DocumentChunk:** The RAG knowledge base. `capsule` (FK), `text`, `page_number`, `embedding` (vector type).
- **CapsuleAnalytic:** Tracking usage. `capsule` (FK), `question_hash` (SHA-256 for privacy), `was_answered` (boolean), `unanswered_text` (stored raw only if the LLM couldn't answer it).

*Note on implementation:* Because Django's ORM support for pgvector requires extra plugins, the developer used raw SQL (`cursor.execute`) for inserting and querying vector data in `views.py`.

# 8. API Deep Dive

| Method | Endpoint | Request | Response | Auth | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| POST | `/api/ingest` | `FormData` (file, url, ttl) | `{ slug, domain, expires_at }` | Optional (Token) | Creates a new capsule and chunks/embeds document. |
| POST | `/api/capsules/<slug>/search` | `{ question, password }` | `{ chunks: [...] }` | Internal API Key | Returns closest text chunks (Used by Node server). |
| GET | `/stream/<slug>?q=...` | Query Params | SSE Stream (`text/event-stream`) | None (Rate limited) | Main chat interface. Streams LLM response. |
| POST | `/api/capsules/<slug>/analytics` | `{ question, was_answered }` | `{ status: "Analytic logged" }` | Internal API Key | Logs question outcomes to dashboard. |

# 9. Authentication & Authorization

- **Global Users:** Uses standard Django Token Authentication (`rest_framework.authtoken`).
- **Capsule Passwords:** Creators can set a password for a capsule. It is stored as a hash (`make_password`). The Node server forwards passwords to Django to authorize search requests.
- **Service-to-Service:** The Node.js SSE server communicates with Django using a static `INTERNAL_API_KEY` defined in environment variables.
- **Dashboard Access:** To prevent IDOR (Insecure Direct Object Reference) on analytics, the dashboard requires either the global Auth Token OR checking the local storage `cd_ownerships` map for the capsule's UUID.

# 10. AI/ML Deep Dive

- **Embeddings:** Uses Nomic's `nomic-embed-text-v1.5` or OpenAI's `text-embedding-3-small`. Embeddings are arrays of floats representing the semantic meaning of text chunks.
- **LLM Models:** Uses `llama-3.3-70b-versatile` (via Groq API) for primary generation due to fast token output, which is critical for real-time chat.
- **Fallbacks:** Implements extensive `try/catch` blocks to fall back to a local Ollama instance (`gemma4:e2b`) if cloud APIs are unavailable.
- **Prompt Engineering:** The RAG system prompt explicitly commands the model to cite sources (`[Page X]`) and state "This document doesn't cover that" if the answer isn't present in the context.

# 13. Algorithms & Data Structures

- **Sliding Window Chunking:** Used to split documents into chunks of 1000 characters with a 200-character overlap.
  - *Problem:* Ensures semantic meaning isn't abruptly cut off between chunks.
  - *Time Complexity:* $O(N)$ where $N$ is text length.
- **Cosine Distance (pgvector):** Used for finding relevant context.
  - *Problem:* Need to find text chunks semantically similar to a user's question.
  - *Complexity:* $O(V)$ where $V$ is the number of vectors, accelerated by HNSW or IVFFlat indexes in Postgres (though explicit indexes aren't defined in the raw SQL in this codebase).

# 14. Design Decisions

## Why Node.js for SSE instead of Django?
Django uses synchronous worker threads (WSGI/Gunicorn). If we stream responses using Django, a long-lived SSE connection occupies a worker thread for the duration of the stream. With just a few concurrent users, Django would run out of workers and hang. Node.js uses an event loop (async/await) which can handle thousands of concurrent idle or streaming connections efficiently.

## Why raw SQL for pgvector instead of Django ORM?
The developer opted to use `connection.cursor()` for vector insertion and querying rather than installing and configuring `pgvector-python` and Django extensions. This avoids heavy dependency overhead for a relatively simple two-query requirement.

# 15. Real Technical Challenges

- **Problem:** Streaming LLM tokens efficiently to the React client while integrating with Django's database.
- **Attempt:** Likely initially tried doing it all in Django, realizing WSGI blocks on streaming.
- **Final Solution:** Splitting the architecture. Node.js handles the SSE stream and Groq API call, while reaching back to Django via an internal API for the vector search results.
- **Lesson:** Use the right tool for the job (Node for async streaming IO, Django for relational DB/ORM logic).

# 16. Bugs / Risks

- **[IMPLEMENTED PROBLEM] No pgvector Indexes:** The `capsules_documentchunk` table does not have an HNSW or IVFFlat index. A sequential scan is performed for every search, which will be slow if a capsule contains massive documents.
- **[RISK] Scraper Fragility:** `scrape_url_text` relies on BeautifulSoup. It will fail on SPAs and heavily protected sites.
- **[RISK] Redis offline handling:** The Node.js server gracefully degrades if Redis is offline ("Redis offline. Rate limiting will be bypassed"). This means the app works locally without Redis, but in production, if Redis drops, the API is exposed to unrestricted abuse.
- **[RISK] SQL Injection:** The raw SQL query for pgvector search is parameterized correctly (`%s`), which is good, but managing raw SQL always carries a slightly higher risk of accidental injection if modified improperly in the future.

# 17. Performance

- **[IMPLEMENTED] Fast LLM:** Utilizing Groq provides extremely fast time-to-first-token (TTFT).
- **[IMPLEMENTED] Sliding Window Chunking:** Balances context preservation with fast embedding generation.
- **[RECOMMENDED] Database Indexing:** Add `CREATE INDEX ON capsules_documentchunk USING hnsw (embedding vector_cosine_ops);` to speed up searches.
- **[RECOMMENDED] React Optimization:** `App.tsx` is nearly 1200 lines long. Component re-renders on every keystroke in the chat input might cause slight UI lag. Needs to be refactored into smaller components.

# 18. Security

- **Rate Limiting:** Implemented via Redis in Node.js on the `/stream` endpoint (Max 5 queries per minute per IP).
- **Service Authentication:** Django endpoints are protected by `INTERNAL_API_KEY`.
- **Privacy:** `CapsuleAnalytic` hashes answered questions (SHA-256) so capsule creators can't see exactly what readers asked if the question was successfully answered, protecting reader privacy while still tracking usage counts. Unanswered questions are stored raw to help creators improve their documents.
- **[RISK] SSRF:** The `/api/ingest` endpoint accepts a `url` parameter and server-side fetches it using `requests.get()`. This is a Server-Side Request Forgery (SSRF) risk. A user could pass `http://localhost:8000/admin` or AWS metadata URLs.

# 19. Testing

- **Tests missing:** No unit tests or integration tests exist in the standard Django testing framework (`tests.py` is empty).
- **Manual Testing script:** `test_scrape.py` is an exploratory script to test the Fandom API bypass.

# 20. Deployment

The project is configured for deployment, but it is **NOT CURRENTLY DEPLOYED** in this local workspace.
- **Deployment Architecture:** Defined in `render.yaml`.
  - Service 1: `contextdrop-api` (Python/Gunicorn).
  - Service 2: `contextdrop-sse` (Node.js).
  - Depends on external Postgres and Redis databases.

# 21. Interview Questions

### Easy
- What problem does ContextDrop solve?
- Why did you use React for the frontend?

### Medium
- Explain the end-to-end flow of uploading a document to getting an AI response.
- Why did you separate the Node.js server from the Django server?
- How does the system handle documents that exceed the LLM's context window?

### Hard
- How did you implement vector similarity search in PostgreSQL without relying on an ORM extension?
- Explain your approach to protecting user privacy while providing analytics to document creators.
- What is Server-Side Request Forgery (SSRF) and how might your URL scraping feature be vulnerable to it?

### Very Hard
- If ContextDrop scaled to 10,000 concurrent streaming users, how would you re-architect the Node.js streaming service and rate-limiting system?

# 22. Interview Answer Guidance

**Why did you separate Node.js from Django?**
*Interviewer is testing:* Understanding of synchronous vs asynchronous I/O and web server concurrency models.
*Key Points:* Mention Django's WSGI (Gunicorn) synchronous workers. Explain that a long-lived SSE (Server-Sent Events) connection would block a worker thread. If you have 4 workers, the 5th user hangs. Node.js is event-driven and non-blocking, making it perfect for holding thousands of open SSE connections while waiting for the LLM to stream tokens.

**How does chunking and RAG work?**
*Interviewer is testing:* Understanding of modern LLM patterns.
*Key Points:* Explain the sliding window approach (1000 chars, 200 overlap) to prevent cutting semantic meaning in half. Explain that embeddings represent text as vectors, and pgvector uses cosine distance to find the most mathematically similar chunks to the user's question.

# 23. 30-Second Explanation
"ContextDrop is a platform I built that lets users upload lengthy documents and instantly generate a shareable 'TinyURL'. When someone opens that URL, instead of reading a static PDF, they get an interactive chatbot grounded strictly in the document's context. I built the backend in Django with PostgreSQL for vector search, a Node.js microservice for real-time LLM streaming, and a React frontend."

# 24. 2-Minute Explanation
"I built ContextDrop to solve the problem of sharing complex documents. If you send a 50-page legal contract, no one reads it. With ContextDrop, you upload it, and I use Django to parse the text, chunk it with a sliding window, generate embeddings, and store them in Postgres using pgvector. 

When a user asks a question, I have a Node.js microservice that handles Server-Sent Events. It reaches out to Django to perform a vector similarity search, retrieves the most relevant document chunks, and passes them to an LLM like Groq or Ollama. The LLM streams the answer back through Node to the React frontend. I split the Node and Django architecture specifically because Django's synchronous workers would choke on long-lived streaming connections, whereas Node handles them perfectly."

# 25. 5-Minute Technical Explanation
*(Expand on the 2-minute explanation by detailing the raw SQL implementation of pgvector, the zero-shot classification for domain-specific tone injection, the SHA-256 hashing for privacy analytics, and the Redis rate-limiting fallback mechanisms).*

# 26. Resume Claim Verification

[NO RESUME FOUND IN WORKSPACE]
(If you add a resume later, compare its claims against this guide).

# 27. Truthfulness Audit

## Confidently Claim
- Built a microservice architecture (Django + Node.js).
- Implemented RAG (Retrieval-Augmented Generation) from scratch.
- Integrated pgvector using raw SQL.
- Handled Server-Sent Events (SSE) for real-time streaming.

## Explain More Carefully
- "Custom Analytics Dashboard": Be clear that it tracks counts, heatmaps, and unanswered questions, but hashes answered questions for privacy.

## Do Not Claim
- "Highly scalable/Secure" (It has SSRF risks and lacks pgvector indexes).
- "Complete Test Coverage" (No tests exist).

# 28. What This Project Demonstrates
- **Systems Architecture:** Understanding the limitations of WSGI and splitting services to solve I/O bottlenecks.
- **AI/ML Engineering:** Practical application of RAG, embeddings, and prompt engineering (zero-shot classification).
- **Full-Stack Development:** React, Node, Python, and SQL databases.
- **Product Thinking:** The SHA-256 privacy feature shows consideration for user trust.

# 29. What This Project Does NOT Demonstrate
- Test-Driven Development (TDD).
- Advanced CI/CD pipelines (deployment is a basic Render config).
- Complex React state management (everything is dumped into `App.tsx`).

# 30. Recommended Improvements

### Critical
- **Fix SSRF Vulnerability:** Validate and sanitize the `url` parameter in the ingest endpoint before fetching it.
- **Database Indexing:** Add an HNSW index to the `embedding` column in PostgreSQL.

### High Value
- **Refactor Frontend:** Break `App.tsx` (1200 lines) into smaller components (`Chat.tsx`, `Upload.tsx`, `Dashboard.tsx`).
- **Add Tests:** Write pytest cases for the ingestion and vector search logic.

### Nice to Have
- Add OCR for image-based PDFs.

### Avoid
- Do not add complex multi-agent frameworks (e.g., LangChain) unless necessary; the current raw implementation is faster and easier to explain in interviews.
