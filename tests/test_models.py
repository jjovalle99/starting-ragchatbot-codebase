from models import Lesson, Course, CourseChunk


class TestLesson:
    def test_lesson_with_all_fields(self):
        lesson = Lesson(lesson_number=1, title="Intro", lesson_link="https://example.com")
        assert lesson.lesson_number == 1
        assert lesson.title == "Intro"
        assert lesson.lesson_link == "https://example.com"

    def test_lesson_link_defaults_to_none(self):
        lesson = Lesson(lesson_number=1, title="Intro")
        assert lesson.lesson_link is None


class TestCourse:
    def test_course_with_all_fields(self):
        course = Course(
            title="Test Course",
            course_link="https://example.com",
            instructor="Dr. Test",
            lessons=[Lesson(lesson_number=1, title="L1")],
        )
        assert course.title == "Test Course"
        assert course.course_link == "https://example.com"
        assert course.instructor == "Dr. Test"
        assert len(course.lessons) == 1

    def test_course_defaults(self):
        course = Course(title="Minimal")
        assert course.course_link is None
        assert course.instructor is None
        assert course.lessons == []


class TestCourseChunk:
    def test_chunk_with_all_fields(self):
        chunk = CourseChunk(
            content="Some text",
            course_title="Course A",
            lesson_number=2,
            chunk_index=0,
        )
        assert chunk.content == "Some text"
        assert chunk.course_title == "Course A"
        assert chunk.lesson_number == 2
        assert chunk.chunk_index == 0

    def test_chunk_lesson_number_defaults_to_none(self):
        chunk = CourseChunk(content="Text", course_title="C", chunk_index=0)
        assert chunk.lesson_number is None
