"""API endpoint tests using an inline FastAPI app (no static-file import issues)."""

import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    @pytest.mark.api
    def test_root_returns_ok(self, api_client):
        response = api_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    @pytest.mark.api
    def test_success_creates_session(self, api_client, mock_rag_system):
        mock_rag_system.session_manager.create_session.return_value = "new_session"
        mock_rag_system.query.return_value = (
            "This is the answer.",
            [{"title": "Course A", "url": "https://example.com"}],
        )

        response = api_client.post("/api/query", json={"query": "What is testing?"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is the answer."
        assert data["session_id"] == "new_session"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "Course A"
        assert data["sources"][0]["url"] == "https://example.com"

    @pytest.mark.api
    def test_preserves_existing_session_id(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Answer", [])

        response = api_client.post(
            "/api/query",
            json={"query": "Follow up?", "session_id": "session_42"},
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == "session_42"
        mock_rag_system.query.assert_called_once_with("Follow up?", "session_42")
        mock_rag_system.session_manager.create_session.assert_not_called()

    @pytest.mark.api
    def test_missing_query_returns_422(self, api_client):
        response = api_client.post("/api/query", json={})
        assert response.status_code == 422

    @pytest.mark.api
    def test_empty_sources_list(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("No sources needed.", [])

        response = api_client.post("/api/query", json={"query": "Hello"})

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == []

    @pytest.mark.api
    def test_source_without_url(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Answer",
            [{"title": "Offline Course"}],
        )

        response = api_client.post("/api/query", json={"query": "test"})

        assert response.status_code == 200
        source = response.json()["sources"][0]
        assert source["title"] == "Offline Course"
        assert source["url"] is None

    @pytest.mark.api
    def test_rag_error_returns_500(self, api_client, mock_rag_system):
        mock_rag_system.query = AsyncMock(side_effect=RuntimeError("LLM down"))

        response = api_client.post("/api/query", json={"query": "anything"})

        assert response.status_code == 500
        assert "LLM down" in response.json()["detail"]

    @pytest.mark.api
    def test_response_content_type(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("ok", [])

        response = api_client.post("/api/query", json={"query": "hi"})

        assert response.headers["content-type"] == "application/json"

    @pytest.mark.api
    def test_multiple_sources(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Combined answer",
            [
                {"title": "Course A", "url": "https://a.com"},
                {"title": "Course B", "url": "https://b.com"},
                {"title": "Course C"},
            ],
        )

        response = api_client.post("/api/query", json={"query": "broad question"})

        assert response.status_code == 200
        sources = response.json()["sources"]
        assert len(sources) == 3
        assert sources[2]["url"] is None


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    @pytest.mark.api
    def test_success(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course A", "Course B"],
        }

        response = api_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Course A", "Course B"]

    @pytest.mark.api
    def test_empty_catalog(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = api_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    @pytest.mark.api
    def test_error_returns_500(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")

        response = api_client.get("/api/courses")

        assert response.status_code == 500
        assert "DB error" in response.json()["detail"]

    @pytest.mark.api
    def test_response_content_type(self, api_client, mock_rag_system):
        response = api_client.get("/api/courses")
        assert response.headers["content-type"] == "application/json"
