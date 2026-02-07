"""Orchestrates RAG queries using session history, tools, and AI generation."""

import os
from typing import List, Tuple, Optional, Dict, Any, Set

from document_processor import DocumentProcessor
from vector_store import VectorStore
from ai_generator import AIGenerator
from session_manager import SessionManager
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
from models import Course, CourseChunk


class RAGSystem:
    """Main orchestrator for the Retrieval-Augmented Generation system"""

    def __init__(self, config):
        self.config = config

        # Initialize core components
        self.document_processor = DocumentProcessor(
            config.CHUNK_SIZE,
            config.CHUNK_OVERLAP
        )
        self.vector_store = VectorStore(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            config.MAX_RESULTS
        )
        self.ai_generator = AIGenerator(
            config.OPENAI_API_KEY,
            config.OPENAI_MODEL
        )
        self.session_manager = SessionManager(config.MAX_HISTORY)

        # Initialize search tools
        self.tool_manager = ToolManager()
        self.search_tool = CourseSearchTool(self.vector_store)
        self.tool_manager.register_tool(self.search_tool)
        self.outline_tool = CourseOutlineTool(self.vector_store)
        self.tool_manager.register_tool(self.outline_tool)

    def add_course_document(self, file_path: str) -> Tuple[Optional[Course], int]:
        """
        Add a single course document to the knowledge base.

        Args:
            file_path: Path to the course document

        Returns:
            Tuple of (Course object, number of chunks created)
        """
        try:
            # Process the document
            course, course_chunks = self.document_processor.process_course_document(file_path)

            # Add course metadata to vector store for semantic search
            self.vector_store.add_course_metadata(course)

            # Add course content chunks to vector store
            self.vector_store.add_course_content(course_chunks)

            return course, len(course_chunks)
        except Exception as e:
            print(f"Error processing course document {file_path}: {e}")
            return None, 0

    def add_course_folder(
        self,
        folder_path: str,
        clear_existing: bool = False
    ) -> Tuple[int, int]:
        """
        Add all course documents from a folder.

        Args:
            folder_path: Path to folder containing course documents
            clear_existing: Whether to clear existing data first

        Returns:
            Tuple of (total courses added, total chunks created)
        """
        # Clear existing data if requested
        if clear_existing:
            print("Clearing existing data for fresh rebuild...")
            self.vector_store.clear_all_data()

        # Validate folder exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return 0, 0

        # Get existing course titles to avoid re-processing
        existing_titles = set(self.vector_store.get_existing_course_titles())

        # Process files in the folder
        total_courses = 0
        total_chunks = 0

        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)

            if not self._is_valid_document_file(file_path):
                continue

            processed_courses, processed_chunks = self._process_single_document(
                file_path,
                existing_titles
            )
            total_courses += processed_courses
            total_chunks += processed_chunks

        return total_courses, total_chunks

    def _is_valid_document_file(self, file_path: str) -> bool:
        """Check if a file is a valid document for processing"""
        if not os.path.isfile(file_path):
            return False

        valid_extensions = ('.pdf', '.docx', '.txt')
        return file_path.lower().endswith(valid_extensions)

    def _process_single_document(
        self,
        file_path: str,
        existing_titles: Set[str]
    ) -> Tuple[int, int]:
        """
        Process a single document file.

        Returns:
            Tuple of (courses added, chunks added)
        """
        try:
            # Process the document to get course data
            course, course_chunks = self.document_processor.process_course_document(file_path)

            if not course:
                return 0, 0

            # Skip if course already exists
            if course.title in existing_titles:
                print(f"Course already exists: {course.title} - skipping")
                return 0, 0

            # Add new course to vector store
            self.vector_store.add_course_metadata(course)
            self.vector_store.add_course_content(course_chunks)

            print(f"Added new course: {course.title} ({len(course_chunks)} chunks)")
            existing_titles.add(course.title)

            return 1, len(course_chunks)

        except Exception as e:
            file_name = os.path.basename(file_path)
            print(f"Error processing {file_name}: {e}")
            return 0, 0

    async def query(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a user query using the RAG system with tool-based search.

        Args:
            query: User's question
            session_id: Optional session ID for conversation context

        Returns:
            Tuple of (response, sources list)
        """
        # Create prompt for the AI
        prompt = f"Answer this question about course materials: {query}"

        # Get conversation history if session exists
        history = None
        if session_id:
            history = self.session_manager.get_conversation_history(session_id)

        # Generate response using AI with tools
        response = await self.ai_generator.generate_response(
            query=prompt,
            conversation_history=history,
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager
        )

        # Get sources from the search tool
        sources = self.tool_manager.get_last_sources()

        # Reset sources after retrieving them
        self.tool_manager.reset_sources()

        # Update conversation history
        if session_id:
            self.session_manager.add_exchange(session_id, query, response)

        return response, sources

    def get_course_analytics(self) -> Dict[str, Any]:
        """Get analytics about the course catalog"""
        return {
            "total_courses": self.vector_store.get_course_count(),
            "course_titles": self.vector_store.get_existing_course_titles()
        }