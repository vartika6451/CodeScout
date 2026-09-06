# 🧭 CodeScout

An AI-powered repository intelligence platform that indexes, analyzes, and searches codebases using autonomous multi-step agents and dense vector Retrieval-Augmented Generation (RAG). 

CodeScout allows developers to paste any public GitHub repository, automatically vectorize its syntax chunks into PostgreSQL (`pgvector`), and query it conversationally with transparent agent reasoning and line-by-line source citations.

---

## ✨ Key Features

- **🚀 Automated GitHub Ingestion**: Scans repository file trees, filters out non-code assets/dependencies, and parses code into semantic chunks.
- **⚡ Vector Embeddings & pgvector**: Generates dense code embeddings via the Google Gemini API (`gemini-embedding-001`) and stores them in PostgreSQL using pgvector cosine distance indexing.
- **🧠 Autonomous Multi-Agent Loop (LangGraph)**:
  - **Retrieve Node**: Queries pgvector for top semantic matches.
  - **Evaluate Node**: LLM agent evaluates whether retrieved code is relevant enough to answer the question.
  - **Refine Node**: If retrieval quality is low, the agent autonomously rewrites and sharpens the technical search query and re-executes retrieval (up to 3 attempts).
  - **Generate Node**: Synthesizes a structured, file-referenced architectural response based on retrieved context.
- **💻 Interactive Source Citations**: Every answer includes clickable source badges showing exact file paths, similarity scores, line-numbered code snippets, and direct links to GitHub.
- **🎨 Modern Dark-Mode UI**: Built with Next.js 16 (App Router), React 19, and Tailwind CSS v4, featuring glassmorphism panels, glowing accents, live API health monitoring, and a repository switcher.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Frontend["Frontend (Next.js 16 + React 19)"]
        UI["Modern Glassmorphic UI"]
        RA["Repository Analyzer"]
        CW["Chat Workspace & Citations"]
        UI --> RA
        UI --> CW
    end

    subgraph Backend["Backend API (FastAPI)"]
        Health["GET /health"]
        Analyze["POST /analyze"]
        Repos["GET & DELETE /repositories"]
        Chat["POST /chat"]
    end

    subgraph Agents["LangGraph Autonomous Agent Workflow"]
        Start([START]) --> Ret["retrieve_node"]
        Ret --> Eval{"evaluate_retrieval"}
        Eval -- "Needs Refinement & attempts < 3" --> Ref["refine_query"]
        Ref --> Ret
        Eval -- "Relevant or Max Attempts" --> Gen["generate_node"]
        Gen --> EndNode([END])
    end

    subgraph Storage["Data & AI Layer"]
        PG[("PostgreSQL + pgvector\n(code_chunks)")]
        Gemini["Google Gemini 3.5 Flash & Embeddings"]
        GH["GitHub REST API"]
    end

    RA -->|POST /analyze| Analyze
    CW -->|POST /chat| Chat
    Analyze --> GH
    Analyze --> Gemini
    Analyze --> PG
    Chat --> Agents
    Ret --> PG
    Eval --> Gemini
    Ref --> Gemini
    Gen --> Gemini
```

---

## 📂 Project Structure

```bash
CodeScout/
├── README.md                      # Comprehensive project documentation
├── backend/                       # FastAPI backend workspace
│   ├── .env                       # API keys and database configuration
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint with CORS & routers
│   │   ├── agents/                # LangGraph Multi-Agent implementation
│   │   │   ├── graph.py           # StateGraph definition & conditional routing
│   │   │   ├── state.py           # CodeScoutState TypedDict schema
│   │   │   ├── retrieve.py        # Semantic vector retrieval node
│   │   │   ├── evaluate.py        # LLM retrieval relevance evaluation node
│   │   │   ├── refine.py          # LLM query reformulation node
│   │   │   └── generate.py        # Final architectural answer generation node
│   │   ├── rag/                   # RAG utilities & vector database connectors
│   │   │   ├── chunker.py         # Code chunking by token/line boundaries
│   │   │   ├── embeddings.py      # Gemini batch embedding generation
│   │   │   ├── retriever.py       # pgvector cosine similarity search (<=>)
│   │   │   ├── vector_store.py    # Chunk upsert and deletion queries
│   │   │   └── generator.py       # Gemini prompt synthesis
│   │   ├── routes/                # HTTP route handlers
│   │   │   ├── health.py          # GET /health
│   │   │   ├── analyze.py         # POST /analyze
│   │   │   ├── chat.py            # POST /chat
│   │   │   └── repositories.py    # GET /repositories & DELETE /repositories/{owner}/{repo}
│   │   └── services/              # External service integrations
│   │       ├── database.py        # PostgreSQL psycopg connection pool
│   │       ├── github_service.py  # GitHub tree & file content extraction
│   │       └── file_filter.py     # Code extension & ignore rule filtering
│   └── test_*.py                  # Verification scripts for DB, embeddings, retrieval
└── frontend/                      # Next.js frontend workspace
    ├── app/
    │   ├── layout.tsx             # Root layout with SEO tags and theme
    │   ├── page.tsx               # Main dashboard with tab state & health sync
    │   ├── globals.css            # Custom design tokens, glassmorphism & glows
    │   ├── types.ts               # Shared TypeScript schemas
    │   └── components/
    │       ├── Header.tsx         # Brand logo, repo switcher & live API health
    │       ├── RepositoryAnalyzer.tsx # GitHub URL ingestion & vector store manager
    │       ├── ChatWorkspace.tsx  # Q&A conversation thread & telemetry badges
    │       ├── CitationViewer.tsx # Modal for line-numbered code snippet inspection
    │       ├── MarkdownView.tsx   # Markdown parser with styled copyable code blocks
    │       └── Icons.tsx          # Standalone SVG icons (e.g. GithubIcon)
    ├── package.json               # Next.js 16, React 19, Tailwind CSS v4, Lucide
    └── tsconfig.json              # TypeScript configuration
```

---

## ⚙️ Environment Configuration

Create a `.env` file inside the `backend/` directory:

```env
# Gemini API Key (from Google AI Studio)
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub Personal Access Token (for rate limits when fetching repos)
GITHUB_TOKEN=your_github_token_here

# PostgreSQL connection string with pgvector extension enabled
DATABASE_URL=postgresql://user:password@localhost:5432/codescout

# Models
GEMINI_MODEL=gemini-3.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

### Database Schema

Ensure the `vector` extension and table exist in PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS code_chunks (
    id SERIAL PRIMARY KEY,
    repository TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_code_chunks_repo ON code_chunks(repository);
```

---

## 🚀 Getting Started

### Prerequisites
- **Python**: `3.9+`
- **Node.js**: `18+` (or `20+`)
- **PostgreSQL**: `15+` with `pgvector` extension

---

### 1. Backend Setup

1. Navigate to `backend/`:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install fastapi uvicorn psycopg pgvector google-genai python-dotenv langgraph httpx
   ```

4. Run the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - API endpoints: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - Interactive Swagger docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 2. Frontend Setup

1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev -- -p 3000
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🔌 API Reference

### 1. Health Check
* **Endpoint**: `GET /health`
* **Response**:
  ```json
  {
    "status": "healthy"
  }
  ```

---

### 2. List Indexed Repositories
* **Endpoint**: `GET /repositories`
* **Response**:
  ```json
  {
    "repositories": [
      {
        "repository": "vartika6451/Yumzo",
        "total_chunks": 24,
        "total_files": 5
      }
    ]
  }
  ```

---

### 3. Analyze & Index Repository
* **Endpoint**: `POST /analyze`
* **Body**:
  ```json
  {
    "repo_url": "https://github.com/vartika6451/Yumzo"
  }
  ```
* **Response**:
  ```json
  {
    "message": "Repository analyzed successfully",
    "repository": "Yumzo",
    "owner": "vartika6451",
    "language": "JavaScript",
    "stars": 12,
    "total_files": 5,
    "total_chunks": 24,
    "embeddings_created": 24
  }
  ```

---

### 4. Delete Repository Index
* **Endpoint**: `DELETE /repositories/{owner}/{repo}`
* **Response**:
  ```json
  {
    "message": "Successfully deleted vectors for repository 'vartika6451/Yumzo'",
    "repository": "vartika6451/Yumzo"
  }
  ```

---

### 5. AI Chat & Code Exploration
* **Endpoint**: `POST /chat`
* **Body**:
  ```json
  {
    "repository": "vartika6451/Yumzo",
    "question": "Where is the payment checkout session created?"
  }
  ```
* **Response**:
  ```json
  {
    "answer": "The payment checkout session is initiated in **`Yumzo/src/components/Cart.jsx`**...\n\n```javascript\nconst stripeRes = await fetch('http://localhost:5000/api/payments/create-checkout-session', {\n  method: 'POST',\n  ...\n});\n```",
    "sources": [
      {
        "file_path": "Yumzo/src/components/Cart.jsx",
        "chunk_index": 11,
        "similarity": 0.6941,
        "content": "// 2. Get Stripe Checkout URL\nconst stripeRes = await fetch('http://localhost:5000/api/payments/create-checkout-session', ...);"
      }
    ],
    "refined_question": null,
    "attempt_count": 1
  }
  ```

---

## 🤖 The LangGraph Agent Pipeline

```
[User Question]
       │
       ▼
 ┌───────────┐
 │ retrieve  │ ──► Embeds question & queries top-5 chunks from pgvector
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │ evaluate  │ ──► Gemini checks if context is sufficient to answer question
 └─────┬─────┘
       │
   Is relevant?
   ├── NO & attempts < 3 ──► ┌─────────┐
   │                         │ refine  │ ──► Rewrites query with technical terms
   │                         └────┬────┘
   │                              └────────► (Back to 'retrieve')
   └── YES or attempts >= 3
       │
       ▼
 ┌───────────┐
 │ generate  │ ──► Synthesizes structured architectural answer with citations
 └───────────┘
```

---

## 🛡️ License

This project is licensed under the MIT License.
