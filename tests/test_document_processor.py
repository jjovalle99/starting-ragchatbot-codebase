import os
from document_processor import DocumentProcessor


class TestReadFile:
    def test_read_file_utf8(self, sample_course_file):
        dp = DocumentProcessor(chunk_size=800, chunk_overlap=100)
        content = dp.read_file(sample_course_file)
        assert "Introduction to Testing" in content
        assert "Jane Smith" in content


class TestChunkText:
    def test_chunk_text_short_text(self):
        dp = DocumentProcessor(chunk_size=500, chunk_overlap=30)
        chunks = dp.chunk_text("This is a short sentence.")
        assert len(chunks) == 1
        assert chunks[0] == "This is a short sentence."

    def test_chunk_text_respects_size(self):
        dp = DocumentProcessor(chunk_size=100, chunk_overlap=0)
        text = "First sentence here. Second sentence here. Third sentence is also here. Fourth sentence too."
        chunks = dp.chunk_text(text)
        for chunk in chunks:
            # Allow some tolerance since splitting is sentence-aware
            assert len(chunk) <= 150  # generous upper bound

    def test_chunk_text_sentence_aware(self):
        dp = DocumentProcessor(chunk_size=60, chunk_overlap=0)
        text = "Hello world. This is a test. Another sentence here."
        chunks = dp.chunk_text(text)
        # Each chunk should contain complete sentences (not cut mid-word)
        for chunk in chunks:
            # Chunks should not end mid-word (except possibly the raw text boundary)
            assert chunk.strip()[-1] in ".!?" or chunk == chunks[-1]

    def test_chunk_text_overlap(self):
        dp = DocumentProcessor(chunk_size=80, chunk_overlap=40)
        text = "First sentence here. Second sentence here. Third sentence also. Fourth sentence too."
        chunks = dp.chunk_text(text)
        if len(chunks) >= 2:
            # With overlap, end of chunk N should appear somewhere in chunk N+1
            # Check that there's some overlap content
            last_words_chunk0 = chunks[0].split()[-3:]
            overlap_found = any(
                word in chunks[1] for word in last_words_chunk0
            )
            assert overlap_found

    def test_chunk_text_empty(self):
        dp = DocumentProcessor(chunk_size=200, chunk_overlap=30)
        chunks = dp.chunk_text("")
        assert chunks == []


class TestProcessCourseDocument:
    def test_process_course_metadata(self, document_processor, sample_course_file):
        course, _ = document_processor.process_course_document(sample_course_file)
        assert course.title == "Introduction to Testing"
        assert course.course_link == "https://example.com/courses/testing"
        assert course.instructor == "Jane Smith"

    def test_process_course_lessons(self, document_processor, sample_course_file):
        course, _ = document_processor.process_course_document(sample_course_file)
        assert len(course.lessons) == 2
        assert course.lessons[0].lesson_number == 1
        assert course.lessons[0].title == "Getting Started"
        assert course.lessons[1].lesson_number == 2
        assert course.lessons[1].title == "Advanced Techniques"

    def test_process_course_chunks_created(self, document_processor, sample_course_file):
        course, chunks = document_processor.process_course_document(sample_course_file)
        assert len(chunks) > 0
        assert all(c.course_title == "Introduction to Testing" for c in chunks)

    def test_process_course_chunk_lesson_numbers(self, document_processor, sample_course_file):
        _, chunks = document_processor.process_course_document(sample_course_file)
        # Every chunk should have a lesson number assigned
        lesson_numbers = {c.lesson_number for c in chunks}
        assert 1 in lesson_numbers
        assert 2 in lesson_numbers
