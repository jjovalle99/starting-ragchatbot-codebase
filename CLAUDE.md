# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Dependency Management

**All dependencies must be managed with `uv`** - never use pip, pip-tools, or other package managers. Use `uv add <package>` to add new dependencies.

## Build and Run Commands

**Always use `uv` to run the server** - do not use pip or other package managers.

```bash
# Install dependencies (requires uv package manager)
uv sync

# Run the application (starts on http://localhost:8000)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

## Required Environment

Set `OPENAI_API_KEY` in a `.env` file at the project root.

## Architecture Overview

This is a RAG (Retrieval-Augmented Generation) chatbot for querying course materials. It uses OpenAI's tool calling feature to let the AI decide when to search the vector database.

### Request Flow

1. **Frontend** (`frontend/script.js`) sends POST to `/api/query` with `{query, session_id}`
2. **FastAPI** (`backend/app.py`) receives request, creates/retrieves session
3. **RAGSystem** (`backend/rag_system.py`) orchestrates the query:
   - Retrieves conversation history from `SessionManager`
   - Calls `AIGenerator` with the query and available tools
4. **AIGenerator** (`backend/ai_generator.py`) sends request to OpenAI API with `search_course_content` tool
5. If the AI decides to search:
   - `ToolManager` executes `CourseSearchTool` (`backend/search_tools.py`)
   - `VectorStore` (`backend/vector_store.py`) queries ChromaDB
   - Results return to the AI for final answer synthesis
6. Response flows back with sources for UI display

### Document Ingestion

On startup, `app.py` loads documents from `docs/` folder:
- `DocumentProcessor` (`backend/document_processor.py`) parses course metadata and lesson markers
- Text is chunked with sentence-aware splitting and overlap
- Chunks are embedded and stored in ChromaDB collections: `course_catalog` (metadata) and `course_content` (chunks)

### Key Design Patterns

- **Tool-based search**: The AI autonomously decides when to search via OpenAI's tool calling
- **Session management**: In-memory conversation history for multi-turn context
- **Fuzzy course matching**: Vector store resolves partial course names to full titles

## Personal Preferences

@.claude/dev-preferences.md