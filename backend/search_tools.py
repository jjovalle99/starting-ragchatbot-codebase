from typing import Dict, Any, Optional, List
from vector_store import VectorStore, SearchResults


class CourseSearchTool:
    """Tool for searching course content with semantic course name matching"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources: List[Dict[str, Any]] = []

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return OpenAI-style tool definition for this tool"""
        return {
            "type": "function",
            "function": {
                "name": "search_course_content",
                "description": "Search course materials with smart course name matching and lesson filtering",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in the course content"
                        },
                        "course_name": {
                            "type": "string",
                            "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                        },
                        "lesson_number": {
                            "type": "integer",
                            "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def execute(
        self,
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None
    ) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """
        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
        )

        # Handle errors
        if results.error:
            return results.error

        # Handle empty results
        if results.is_empty():
            filter_info = self._build_filter_info(course_name, lesson_number)
            return f"No relevant content found{filter_info}."

        # Format and return results
        return self._format_results(results)

    def _build_filter_info(
        self,
        course_name: Optional[str],
        lesson_number: Optional[int]
    ) -> str:
        """Build filter information string for error messages"""
        parts = []
        if course_name:
            parts.append(f"in course '{course_name}'")
        if lesson_number:
            parts.append(f"in lesson {lesson_number}")

        if parts:
            return " " + " ".join(parts)
        return ""

    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted_sections = []
        sources = []
        seen_sources = set()

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')

            # Build context header
            header = self._build_header(course_title, lesson_num)
            formatted_sections.append(f"{header}\n{doc}")

            # Track unique sources
            source_key = f"{course_title}|{lesson_num}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                source = self._create_source(course_title, lesson_num)
                sources.append(source)

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted_sections)

    def _build_header(self, course_title: str, lesson_num: Optional[int]) -> str:
        """Build a context header for a search result"""
        header = f"[{course_title}"
        if lesson_num is not None:
            header += f" - Lesson {lesson_num}"
        header += "]"
        return header

    def _create_source(self, course_title: str, lesson_num: Optional[int]) -> Dict[str, Any]:
        """Create a source citation object"""
        source_title = course_title
        if lesson_num is not None:
            source_title += f" - Lesson {lesson_num}"

        source_url = None
        if lesson_num is not None:
            source_url = self.store.get_lesson_link(course_title, lesson_num)

        return {"title": source_title, "url": source_url}


class CourseOutlineTool:
    """Tool for retrieving course outlines with lesson lists"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources: List[Dict[str, Any]] = []

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_course_outline",
                "description": "Get the complete outline of a course including title, link, and all lesson numbers with titles. Use when users ask about course structure or what topics a course covers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_name": {
                            "type": "string",
                            "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                        }
                    },
                    "required": ["course_name"]
                }
            }
        }

    def execute(self, course_name: str) -> str:
        metadata = self.store.get_course_metadata(course_name)

        if not metadata:
            return f"No course found matching '{course_name}'"

        return self._format_outline(metadata)

    def _format_outline(self, metadata: Dict[str, Any]) -> str:
        title = metadata.get('title', 'Unknown Course')
        course_link = metadata.get('course_link')
        lessons = metadata.get('lessons', [])

        lines = [f"Course: {title}"]
        if course_link:
            lines.append(f"Course Link: {course_link}")

        lines.append(f"\nLessons ({len(lessons)} total):")
        for lesson in lessons:
            lesson_num = lesson.get('lesson_number', '?')
            lesson_title = lesson.get('lesson_title', 'Untitled')
            lines.append(f"  {lesson_num}. {lesson_title}")

        self.last_sources = [{"title": title, "url": course_link}]
        return "\n".join(lines)


class ToolManager:
    """Manages available tools for the AI"""

    def __init__(self):
        self.tools: Dict[str, CourseSearchTool] = {}

    def register_tool(self, tool: CourseSearchTool) -> None:
        """Register a tool that provides the get_tool_definition method"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("function", {}).get("name")

        if not tool_name:
            raise ValueError("Tool must have a 'name' in its function definition")

        self.tools[tool_name] = tool

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for AI tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"

        return self.tools[tool_name].execute(**kwargs)

    def get_last_sources(self) -> List[Dict[str, Any]]:
        """Get sources from the last search operation"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self) -> None:
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []