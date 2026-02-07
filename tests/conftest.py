import os
from typing import List, Optional
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from models import Course, Lesson, CourseChunk
from config import Config
from document_processor import DocumentProcessor
from vector_store import VectorStore
from session_manager import SessionManager
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool


# ---------------------------------------------------------------------------
# Pydantic models matching backend/app.py (duplicated here so we never import
# app.py and trigger its StaticFiles mount on a non-existent directory).
# ---------------------------------------------------------------------------

class _QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class _Source(BaseModel):
    title: str
    url: Optional[str] = None


class _QueryResponse(BaseModel):
    answer: str
    sources: List[_Source]
    session_id: str


class _CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Shared API testing fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """A MagicMock standing in for RAGSystem with async query support."""
    mock = MagicMock()
    mock.query = AsyncMock(return_value=("Default answer.", []))
    mock.session_manager.create_session.return_value = "session_1"
    mock.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }
    return mock


@pytest.fixture
def test_app(mock_rag_system):
    """A lightweight FastAPI app that mirrors the real API endpoints
    without mounting static files or running the startup event."""

    app = FastAPI()
    rag = mock_rag_system

    @app.get("/")
    async def root():
        return {"status": "ok"}

    @app.post("/api/query", response_model=_QueryResponse)
    async def query_documents(request: _QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = await rag.query(request.query, session_id)
            source_objects = [
                _Source(title=s.get("title", "Unknown"), url=s.get("url"))
                for s in sources
            ]
            return _QueryResponse(
                answer=answer, sources=source_objects, session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=_CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return _CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def api_client(test_app):
    """TestClient wrapping the lightweight test app."""
    return TestClient(test_app, raise_server_exceptions=False)


@pytest.fixture
def sample_course_text():
    """Raw course document text for testing."""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_course.txt")
    with open(fixture_path, "r") as f:
        return f.read()


@pytest.fixture
def sample_course_file(tmp_path, sample_course_text):
    """Write sample course text to a temp file, return the path."""
    file_path = tmp_path / "sample_course.txt"
    file_path.write_text(sample_course_text)
    return str(file_path)


@pytest.fixture
def document_processor():
    """DocumentProcessor with small chunk size for testing."""
    return DocumentProcessor(chunk_size=200, chunk_overlap=30)


@pytest.fixture
def test_config(tmp_path):
    """Config with fake API key and temp ChromaDB path."""
    return Config(
        OPENAI_API_KEY="fake-key-for-testing",
        CHROMA_PATH=str(tmp_path / "chroma_db"),
    )


@pytest.fixture
def vector_store(tmp_path):
    """VectorStore backed by a temp directory."""
    return VectorStore(
        chroma_path=str(tmp_path / "chroma_db"),
        embedding_model="all-MiniLM-L6-v2",
        max_results=5,
    )


@pytest.fixture
def sample_course():
    """A Course object with 2 lessons."""
    return Course(
        title="Introduction to Testing",
        course_link="https://example.com/courses/testing",
        instructor="Jane Smith",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Getting Started",
                lesson_link="https://example.com/courses/testing/lesson/1",
            ),
            Lesson(
                lesson_number=2,
                title="Advanced Techniques",
                lesson_link="https://example.com/courses/testing/lesson/2",
            ),
        ],
    )


@pytest.fixture
def sample_chunks():
    """A list of 3 CourseChunk objects."""
    return [
        CourseChunk(
            content="Welcome to the course on testing. Unit tests verify individual components.",
            course_title="Introduction to Testing",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Integration tests check that components work together.",
            course_title="Introduction to Testing",
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Mocking is a technique where you replace real objects with fake ones.",
            course_title="Introduction to Testing",
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def populated_vector_store(vector_store, sample_course, sample_chunks):
    """Vector store pre-loaded with sample course data."""
    vector_store.add_course_metadata(sample_course)
    vector_store.add_course_content(sample_chunks)
    return vector_store


@pytest.fixture
def session_manager():
    """SessionManager with small history limit."""
    return SessionManager(max_history=3)


@pytest.fixture
def tool_manager(populated_vector_store):
    """ToolManager with both tools registered."""
    manager = ToolManager()
    manager.register_tool(CourseSearchTool(populated_vector_store))
    manager.register_tool(CourseOutlineTool(populated_vector_store))
    return manager
