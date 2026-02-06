from unittest.mock import MagicMock
import pytest

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolDefinition:
    def test_get_tool_definition(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        defn = tool.get_tool_definition()
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "search_course_content"
        assert "query" in defn["function"]["parameters"]["properties"]


class TestCourseSearchToolExecute:
    def test_execute_returns_formatted_results(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        result = tool.execute(query="unit testing")
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain course context headers
        assert "Introduction to Testing" in result

    def test_execute_error_handling(self):
        mock_store = MagicMock()
        mock_store.search.return_value = SearchResults.empty("Search error: timeout")
        tool = CourseSearchTool(mock_store)
        result = tool.execute(query="anything")
        assert "Search error: timeout" in result

    def test_execute_tracks_sources(self, populated_vector_store):
        tool = CourseSearchTool(populated_vector_store)
        tool.execute(query="unit testing")
        assert len(tool.last_sources) > 0
        assert "title" in tool.last_sources[0]

    def test_execute_deduplicates_sources(self):
        mock_store = MagicMock()
        # Return two results from the same course+lesson
        mock_store.search.return_value = SearchResults(
            documents=["doc1", "doc2"],
            metadata=[
                {"course_title": "C1", "lesson_number": 1},
                {"course_title": "C1", "lesson_number": 1},
            ],
            distances=[0.1, 0.2],
        )
        mock_store.get_lesson_link.return_value = "https://example.com"
        tool = CourseSearchTool(mock_store)
        tool.execute(query="test")
        # Should have only 1 unique source
        assert len(tool.last_sources) == 1

    def test_execute_no_results(self):
        mock_store = MagicMock()
        mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_store)
        result = tool.execute(query="nonexistent content")
        assert "No relevant content found" in result


class TestCourseOutlineTool:
    def test_get_tool_definition(self, populated_vector_store):
        tool = CourseOutlineTool(populated_vector_store)
        defn = tool.get_tool_definition()
        assert defn["function"]["name"] == "get_course_outline"
        assert "course_name" in defn["function"]["parameters"]["properties"]

    def test_execute_formatted_outline(self, populated_vector_store):
        tool = CourseOutlineTool(populated_vector_store)
        result = tool.execute(course_name="Testing")
        assert "Introduction to Testing" in result
        assert "Getting Started" in result
        assert "Advanced Techniques" in result
        assert "Lessons (2 total)" in result

    def test_execute_course_not_found(self):
        mock_store = MagicMock()
        mock_store.get_course_metadata.return_value = None
        tool = CourseOutlineTool(mock_store)
        result = tool.execute(course_name="Nonexistent Course XYZ 999")
        assert "No course found" in result


class TestToolManager:
    def test_register_tool(self, populated_vector_store):
        manager = ToolManager()
        tool = CourseSearchTool(populated_vector_store)
        manager.register_tool(tool)
        assert "search_course_content" in manager.tools

    def test_execute_dispatch(self, tool_manager):
        result = tool_manager.execute_tool("search_course_content", query="testing")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_tool(self, tool_manager):
        result = tool_manager.execute_tool("nonexistent_tool", query="test")
        assert "not found" in result

    def test_get_last_sources(self, tool_manager):
        tool_manager.execute_tool("search_course_content", query="testing")
        sources = tool_manager.get_last_sources()
        assert len(sources) > 0

    def test_reset_sources(self, tool_manager):
        tool_manager.execute_tool("search_course_content", query="testing")
        tool_manager.reset_sources()
        sources = tool_manager.get_last_sources()
        assert sources == []
