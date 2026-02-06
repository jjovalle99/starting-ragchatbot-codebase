import pytest
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


class TestSearchResults:
    def test_from_chroma(self):
        chroma_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "val1"}, {"key": "val2"}]],
            "distances": [[0.1, 0.2]],
        }
        sr = SearchResults.from_chroma(chroma_results)
        assert sr.documents == ["doc1", "doc2"]
        assert sr.metadata == [{"key": "val1"}, {"key": "val2"}]
        assert sr.distances == [0.1, 0.2]
        assert sr.error is None

    def test_empty(self):
        sr = SearchResults.empty("No results")
        assert sr.documents == []
        assert sr.metadata == []
        assert sr.distances == []
        assert sr.error == "No results"

    def test_is_empty_true(self):
        sr = SearchResults(documents=[], metadata=[], distances=[])
        assert sr.is_empty() is True

    def test_is_empty_false(self):
        sr = SearchResults(documents=["doc"], metadata=[{}], distances=[0.1])
        assert sr.is_empty() is False


class TestVectorStoreAddAndRetrieve:
    def test_add_course_metadata(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        titles = vector_store.get_existing_course_titles()
        assert "Introduction to Testing" in titles

    def test_add_course_content(self, vector_store, sample_chunks):
        vector_store.add_course_content(sample_chunks)
        count = vector_store.course_content.count()
        assert count == 3

    def test_get_existing_course_titles(self, populated_vector_store):
        titles = populated_vector_store.get_existing_course_titles()
        assert "Introduction to Testing" in titles

    def test_get_course_count(self, populated_vector_store):
        assert populated_vector_store.get_course_count() == 1

    def test_get_course_metadata(self, populated_vector_store):
        metadata = populated_vector_store.get_course_metadata("Testing")
        assert metadata is not None
        assert metadata["title"] == "Introduction to Testing"
        assert "lessons" in metadata
        assert len(metadata["lessons"]) == 2

    def test_get_course_link(self, populated_vector_store):
        link = populated_vector_store.get_course_link("Introduction to Testing")
        assert link == "https://example.com/courses/testing"

    def test_get_lesson_link(self, populated_vector_store):
        link = populated_vector_store.get_lesson_link("Introduction to Testing", 1)
        assert link == "https://example.com/courses/testing/lesson/1"


class TestVectorStoreSearch:
    def test_search_returns_results(self, populated_vector_store):
        results = populated_vector_store.search(query="unit testing")
        assert not results.is_empty()
        assert results.error is None

    def test_search_with_course_filter(self, populated_vector_store):
        results = populated_vector_store.search(
            query="testing", course_name="Introduction to Testing"
        )
        assert not results.is_empty()
        for meta in results.metadata:
            assert meta["course_title"] == "Introduction to Testing"

    def test_search_with_lesson_filter(self, populated_vector_store):
        results = populated_vector_store.search(query="testing", lesson_number=2)
        assert not results.is_empty()
        for meta in results.metadata:
            assert meta["lesson_number"] == 2

    def test_search_nonexistent_course(self, populated_vector_store):
        # Mock _resolve_course_name to return None (simulating no match)
        from unittest.mock import patch

        with patch.object(
            populated_vector_store, "_resolve_course_name", return_value=None
        ):
            results = populated_vector_store.search(
                query="anything", course_name="Nonexistent Course XYZ"
            )
        assert results.error is not None
        assert "No course found" in results.error


class TestBuildFilter:
    def test_none_when_no_filters(self, vector_store):
        assert vector_store._build_filter(None, None) is None

    def test_course_only(self, vector_store):
        f = vector_store._build_filter("My Course", None)
        assert f == {"course_title": "My Course"}

    def test_lesson_only(self, vector_store):
        f = vector_store._build_filter(None, 3)
        assert f == {"lesson_number": 3}

    def test_both_filters(self, vector_store):
        f = vector_store._build_filter("My Course", 3)
        assert f == {"$and": [{"course_title": "My Course"}, {"lesson_number": 3}]}


class TestClearAllData:
    def test_clear_all_data(self, populated_vector_store):
        assert populated_vector_store.get_course_count() == 1
        populated_vector_store.clear_all_data()
        assert populated_vector_store.get_course_count() == 0
