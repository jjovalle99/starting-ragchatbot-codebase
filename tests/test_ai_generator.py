import json
from unittest.mock import patch, MagicMock
from ai_generator import AIGenerator


def _make_chat_response(content="Hello!", finish_reason="stop", tool_calls=None):
    """Helper to build a mock OpenAI chat completion response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason

    response = MagicMock()
    response.choices = [choice]
    return response


class TestAIGenerator:
    @patch("ai_generator.OpenAI")
    def test_simple_response(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_chat_response(
            content="This is a test answer."
        )

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = gen.generate_response(query="What is testing?")
        assert result == "This is a test answer."

    @patch("ai_generator.OpenAI")
    def test_includes_conversation_history(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_chat_response()

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        gen.generate_response(
            query="Follow up question",
            conversation_history="User: Hello\nAssistant: Hi",
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        system_msg = messages[0]["content"]
        assert "Previous conversation:" in system_msg

    @patch("ai_generator.OpenAI")
    def test_without_history(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_chat_response()

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        gen.generate_response(query="First question")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        system_msg = messages[0]["content"]
        assert "Previous conversation:" not in system_msg

    @patch("ai_generator.OpenAI")
    def test_tool_call_flow(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        # Build a tool call object
        tool_call = MagicMock()
        tool_call.id = "call_123"
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = json.dumps({"query": "testing"})

        # First response triggers tool call
        first_response = _make_chat_response(
            content=None, finish_reason="tool_calls", tool_calls=[tool_call]
        )
        # Second response after tool execution
        second_response = _make_chat_response(content="Final answer with tool results.")

        mock_client.chat.completions.create.side_effect = [first_response, second_response]

        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search result: found content"

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = gen.generate_response(
            query="Search for something",
            tools=[{"type": "function", "function": {"name": "search_course_content"}}],
            tool_manager=mock_tool_manager,
        )

        assert result == "Final answer with tool results."
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="testing"
        )

    @patch("ai_generator.OpenAI")
    def test_api_params(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_chat_response()

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        gen.generate_response(query="Test")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 800
        assert call_kwargs["model"] == "gpt-4o"
