import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """TestClient with mocked rag_system and a temp frontend directory."""
    # Create a fake frontend directory so StaticFiles resolves "../frontend"
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html></html>")

    # Create backend dir — app.py uses relative "../frontend"
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()

    original_cwd = os.getcwd()
    os.chdir(str(backend_dir))

    # Remove cached app module so re-import picks up new CWD
    for mod_name in list(sys.modules.keys()):
        if mod_name == "app" or mod_name.startswith("app."):
            del sys.modules[mod_name]

    try:
        with patch("rag_system.AIGenerator"), \
             patch("rag_system.VectorStore"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
            import app as app_module

            mock_rag = MagicMock()
            mock_rag.query = AsyncMock()
            app_module.rag_system = mock_rag

            yield TestClient(app_module.app, raise_server_exceptions=False), mock_rag
    finally:
        os.chdir(original_cwd)
        # Clean up the cached module so it doesn't affect other tests
        for mod_name in list(sys.modules.keys()):
            if mod_name == "app" or mod_name.startswith("app."):
                del sys.modules[mod_name]


class TestQueryEndpoint:
    def test_query_endpoint_success(self, client):
        test_client, mock_rag = client
        mock_rag.session_manager.create_session.return_value = "session_1"
        mock_rag.query.return_value = (
            "This is the answer.",
            [{"title": "Course A", "url": "https://example.com"}],
        )

        response = test_client.post(
            "/api/query", json={"query": "What is testing?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is the answer."
        assert len(data["sources"]) == 1
        assert data["session_id"] == "session_1"

    def test_query_endpoint_with_session_id(self, client):
        test_client, mock_rag = client
        mock_rag.query.return_value = ("Answer", [])

        response = test_client.post(
            "/api/query",
            json={"query": "Follow up?", "session_id": "session_42"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_42"
        mock_rag.query.assert_called_once_with("Follow up?", "session_42")

    def test_query_endpoint_missing_query(self, client):
        test_client, _ = client
        response = test_client.post("/api/query", json={})
        assert response.status_code == 422


class TestCoursesEndpoint:
    def test_courses_endpoint_success(self, client):
        test_client, mock_rag = client
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course A", "Course B"],
        }

        response = test_client.get("/api/courses")
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert "Course A" in data["course_titles"]

    def test_courses_endpoint_error(self, client):
        test_client, mock_rag = client
        mock_rag.get_course_analytics.side_effect = RuntimeError("DB error")

        response = test_client.get("/api/courses")
        assert response.status_code == 500
