from session_manager import SessionManager


class TestSessionManager:
    def test_create_session_returns_sequential_ids(self):
        sm = SessionManager()
        assert sm.create_session() == "session_1"
        assert sm.create_session() == "session_2"

    def test_add_message_stores_message(self, session_manager):
        session_manager.create_session()
        session_manager.add_message("session_1", "user", "Hello")
        history = session_manager.get_conversation_history("session_1")
        assert "Hello" in history

    def test_add_message_creates_session_if_not_exists(self, session_manager):
        session_manager.add_message("new_session", "user", "Hi")
        history = session_manager.get_conversation_history("new_session")
        assert "Hi" in history

    def test_add_exchange_stores_both_messages(self, session_manager):
        session_manager.create_session()
        session_manager.add_exchange("session_1", "What is testing?", "Testing verifies code.")
        history = session_manager.get_conversation_history("session_1")
        assert "What is testing?" in history
        assert "Testing verifies code." in history

    def test_get_conversation_history_format(self, session_manager):
        session_manager.create_session()
        session_manager.add_exchange("session_1", "Q1", "A1")
        history = session_manager.get_conversation_history("session_1")
        assert "User: Q1" in history
        assert "Assistant: A1" in history

    def test_get_conversation_history_none_for_unknown(self, session_manager):
        assert session_manager.get_conversation_history("nonexistent") is None

    def test_get_conversation_history_none_for_empty(self, session_manager):
        session_manager.create_session()
        assert session_manager.get_conversation_history("session_1") is None

    def test_history_trimming(self):
        sm = SessionManager(max_history=2)
        sm.create_session()
        # Add 10 exchanges (20 messages); max_history=2 means keep last 4 messages
        for i in range(10):
            sm.add_exchange("session_1", f"Q{i}", f"A{i}")
        history = sm.get_conversation_history("session_1")
        # Should NOT contain early messages
        assert "Q0" not in history
        # Should contain the last 2 exchanges
        assert "Q9" in history
        assert "A9" in history
        assert "Q8" in history
        assert "A8" in history

    def test_clear_session(self, session_manager):
        session_manager.create_session()
        session_manager.add_message("session_1", "user", "Hello")
        session_manager.clear_session("session_1")
        assert session_manager.get_conversation_history("session_1") is None
