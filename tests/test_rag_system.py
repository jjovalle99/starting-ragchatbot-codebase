import os
from unittest.mock import patch, MagicMock
import pytest

from rag_system import RAGSystem


@pytest.fixture
def rag_config(tmp_path):
    """Config-like object for RAGSystem tests."""
    from config import Config

    return Config(
        OPENAI_API_KEY="fake-key",
        CHROMA_PATH=str(tmp_path / "chroma_db"),
        CHUNK_SIZE=200,
        CHUNK_OVERLAP=30,
    )


@pytest.fixture
def rag_system(rag_config):
    """RAGSystem with mocked AI generator."""
    with patch("rag_system.AIGenerator") as MockAI:
        mock_ai_instance = MagicMock()
        MockAI.return_value = mock_ai_instance
        system = RAGSystem(rag_config)
        system.ai_generator = mock_ai_instance
        yield system


@pytest.fixture
def sample_course_path(tmp_path):
    """Create a sample course file and return its path."""
    content = """Course Title: Test Course Alpha
Course Link: https://example.com/alpha
Course Instructor: Dr. Alpha

Lesson 1: First Lesson
Lesson Link: https://example.com/alpha/1
This is the content of the first lesson. It covers basic concepts of programming and software development.

Lesson 2: Second Lesson
Lesson Link: https://example.com/alpha/2
This is the content of the second lesson. It covers advanced concepts and design patterns.
"""
    file_path = tmp_path / "course_alpha.txt"
    file_path.write_text(content)
    return str(file_path)


@pytest.fixture
def sample_course_folder(tmp_path):
    """Create a folder with two course files and return its path."""
    folder = tmp_path / "courses"
    folder.mkdir()

    course1 = """Course Title: Course One
Course Link: https://example.com/one
Course Instructor: Teacher One

Lesson 1: Intro
This is lesson one content for course one with basic information.
"""
    course2 = """Course Title: Course Two
Course Link: https://example.com/two
Course Instructor: Teacher Two

Lesson 1: Intro
This is lesson one content for course two with basic information.
"""
    (folder / "course1.txt").write_text(course1)
    (folder / "course2.txt").write_text(course2)
    return str(folder)


class TestAddCourseDocument:
    def test_add_course_document(self, rag_system, sample_course_path):
        course, chunk_count = rag_system.add_course_document(sample_course_path)
        assert course is not None
        assert course.title == "Test Course Alpha"
        assert chunk_count > 0


class TestAddCourseFolder:
    def test_add_course_folder(self, rag_system, sample_course_folder):
        courses, chunks = rag_system.add_course_folder(sample_course_folder)
        assert courses == 2
        assert chunks > 0

    def test_add_course_folder_skips_existing(self, rag_system, sample_course_folder):
        rag_system.add_course_folder(sample_course_folder)
        # Second call should skip existing courses
        courses, chunks = rag_system.add_course_folder(sample_course_folder)
        assert courses == 0
        assert chunks == 0


class TestQuery:
    def test_query_calls_ai_generator(self, rag_system):
        rag_system.ai_generator.generate_response.return_value = "Mocked AI answer"
        answer, sources = rag_system.query("What is testing?", session_id=None)
        assert answer == "Mocked AI answer"
        rag_system.ai_generator.generate_response.assert_called_once()

    def test_query_stores_session_history(self, rag_system):
        rag_system.ai_generator.generate_response.return_value = "Answer"
        session_id = rag_system.session_manager.create_session()
        rag_system.query("Question?", session_id=session_id)
        history = rag_system.session_manager.get_conversation_history(session_id)
        assert "Question?" in history
        assert "Answer" in history


class TestGetCourseAnalytics:
    def test_get_course_analytics(self, rag_system, sample_course_path):
        rag_system.add_course_document(sample_course_path)
        analytics = rag_system.get_course_analytics()
        assert analytics["total_courses"] == 1
        assert "Test Course Alpha" in analytics["course_titles"]
