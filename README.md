# 🧭 CodeScout

An AI-powered repository analysis platform built to scan, understand, and index codebases using agents and Retrieval-Augmented Generation (RAG). CodeScout helps developers explore complex codebases, answer architectural questions, and understand code paths quickly.

---

## 🏗️ Project Architecture

CodeScout is divided into two primary workspaces:

### 1. [Backend](file:///Users/vartikasharma/Documents/CodeScout/backend) (FastAPI)
A Python backend built with FastAPI, designed to handle AI agent workflows, code parsing, indexing, and RAG services.
*   **Entrypoint**: [`app/main.py`](file:///Users/vartikasharma/Documents/CodeScout/backend/app/main.py)
*   **Routes**: 
    *   [`app/routes/health.py`](file:///Users/vartikasharma/Documents/CodeScout/backend/app/routes/health.py) (System health checks)
    *   [`app/routes/analyze.py`](file:///Users/vartikasharma/Documents/CodeScout/backend/app/routes/analyze.py) (Repository analysis)
*   **Modules** *(Placeholder directories for expansion)*:
    *   `app/agents/` — AI agent orchestration and task execution.
    *   `app/rag/` — Vector ingestion, embeddings, and context retrieval.
    *   `app/services/` — Core business logic, parsing, and background processing.
    *   `app/core/` — Config, security, and main settings.

### 2. [Frontend](file:///Users/vartikasharma/Documents/CodeScout/frontend) (Next.js)
A modern, fast web application built on Next.js, React, and Tailwind CSS.
*   **Framework**: Next.js 16 (App Router) & React 19
*   **Styling**: Tailwind CSS v4
*   **Main Page**: [`app/page.tsx`](file:///Users/vartikasharma/Documents/CodeScout/frontend/app/page.tsx)
*   **Global Styles**: [`app/globals.css`](file:///Users/vartikasharma/Documents/CodeScout/frontend/app/globals.css)

---

## 🚀 Getting Started

### Prerequisites
*   **Python**: Version `3.9+`
*   **Node.js**: Version `18+`
*   **Package Manager**: `npm` (or `yarn` / `pnpm` / `bun`)

---

### Backend Setup

1.  **Navigate to the backend directory**:
    ```bash
    cd backend
    ```

2.  **Activate the virtual environment**:
    *   **macOS / Linux**:
        ```bash
        source venv/bin/activate
        ```
    *   **Windows (PowerShell)**:
        ```bash
        .\venv\Scripts\Activate.ps1
        ```

3.  **Run the development server**:
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).
    *   Interactive Swagger docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### Frontend Setup

1.  **Navigate to the frontend directory**:
    ```bash
    cd frontend
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    ```

3.  **Run the development server**:
    ```bash
    npm run dev
    ```
    Open [http://localhost:3000](http://localhost:3000) in your browser to view the application.

---

## 🔌 API Reference

### Health Check
*   **Endpoint**: `GET /health`
*   **Description**: Verifies if the backend server is running correctly.
*   **Response**:
    ```json
    {
      "status": "healthy"
    }
    ```

### Analyze Repository
*   **Endpoint**: `POST /analyze`
*   **Description**: Submits a remote repository URL to start analysis.
*   **Request Body**:
    ```json
    {
      "repo_url": "https://github.com/example/repo"
    }
    ```
*   **Response**:
    ```json
    {
      "message": "Repository received",
      "repo_url": "https://github.com/example/repo"
    }
    ```
