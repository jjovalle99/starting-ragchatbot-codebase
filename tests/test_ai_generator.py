import json
from unittest.mock import patch, MagicMock, AsyncMock
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
    @patch("ai_generator.AsyncOpenAI")
    async def test_simple_response(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_response(content="This is a test answer.")
        )

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = await gen.generate_response(query="What is testing?")
        assert result == "This is a test answer."

    @patch("ai_generator.AsyncOpenAI")
    async def test_includes_conversation_history(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_response()
        )

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        await gen.generate_response(
            query="Follow up question",
            conversation_history="User: Hello\nAssistant: Hi",
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        system_msg = messages[0]["content"]
        assert "Previous conversation:" in system_msg

    @patch("ai_generator.AsyncOpenAI")
    async def test_without_history(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_response()
        )

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        await gen.generate_response(query="First question")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        system_msg = messages[0]["content"]
        assert "Previous conversation:" not in system_msg

    @patch("ai_generator.AsyncOpenAI")
    async def test_tool_call_flow(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client

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

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[first_response, second_response]
        )

        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search result: found content"

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = await gen.generate_response(
            query="Search for something",
            tools=[{"type": "function", "function": {"name": "search_course_content"}}],
            tool_manager=mock_tool_manager,
        )

        assert result == "Final answer with tool results."
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="testing"
        )

    @patch("ai_generator.AsyncOpenAI")
    async def test_api_params(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_chat_response()
        )

        gen = AIGenerator(api_key="fake", model="gpt-4o")
        await gen.generate_response(query="Test")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 800
        assert call_kwargs["model"] == "gpt-4o"

    @patch("ai_generator.AsyncOpenAI")
    async def test_two_sequential_tool_rounds(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client

        tool_call_a = MagicMock()
        tool_call_a.id = "call_a"
        tool_call_a.function.name = "search_course_content"
        tool_call_a.function.arguments = json.dumps({"query": "lesson 4"})

        tool_call_b = MagicMock()
        tool_call_b.id = "call_b"
        tool_call_b.function.name = "search_course_content"
        tool_call_b.function.arguments = json.dumps({"query": "related topic"})

        resp1 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call_a])
        resp2 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call_b])
        resp3 = _make_chat_response(content="Combined answer from two searches.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[resp1, resp2, resp3]
        )

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["Result A", "Result B"]

        tools = [{"type": "function", "function": {"name": "search_course_content"}}]
        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = await gen.generate_response(query="Multi-step query", tools=tools, tool_manager=mock_tool_manager)

        assert result == "Combined answer from two searches."
        assert mock_client.chat.completions.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # 2nd call (after round 1) should include tools
        second_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

        # 3rd call (after round 2, max reached) should omit tools
        third_call_kwargs = mock_client.chat.completions.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs

    @patch("ai_generator.AsyncOpenAI")
    async def test_max_rounds_enforced(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client

        tool_call_1 = MagicMock()
        tool_call_1.id = "call_1"
        tool_call_1.function.name = "search_course_content"
        tool_call_1.function.arguments = json.dumps({"query": "q1"})

        tool_call_2 = MagicMock()
        tool_call_2.id = "call_2"
        tool_call_2.function.name = "search_course_content"
        tool_call_2.function.arguments = json.dumps({"query": "q2"})

        resp1 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call_1])
        resp2 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call_2])
        # 3rd response is text because tools are omitted on the final call
        resp3 = _make_chat_response(content="Final after max rounds.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[resp1, resp2, resp3]
        )

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["Res1", "Res2"]

        tools = [{"type": "function", "function": {"name": "search_course_content"}}]
        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = await gen.generate_response(query="Greedy model", tools=tools, tool_manager=mock_tool_manager)

        assert result == "Final after max rounds."
        assert mock_client.chat.completions.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Final call must not have tools
        final_kwargs = mock_client.chat.completions.create.call_args_list[2][1]
        assert "tools" not in final_kwargs

    @patch("ai_generator.AsyncOpenAI")
    async def test_tool_execution_error_passed_to_model(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client

        tool_call = MagicMock()
        tool_call.id = "call_err"
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = json.dumps({"query": "broken"})

        resp1 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call])
        resp2 = _make_chat_response(content="I encountered an error.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[resp1, resp2]
        )

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = RuntimeError("DB connection failed")

        tools = [{"type": "function", "function": {"name": "search_course_content"}}]
        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = await gen.generate_response(query="Will fail", tools=tools, tool_manager=mock_tool_manager)

        assert result == "I encountered an error."

        # Verify the error was passed as a tool result message
        second_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]
        tool_messages = [m for m in second_call_kwargs["messages"] if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert "Error executing tool: DB connection failed" in tool_messages[0]["content"]

    @patch("ai_generator.AsyncOpenAI")
    async def test_malformed_tool_arguments(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client

        tool_call = MagicMock()
        tool_call.id = "call_bad_json"
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = "not valid json{{"

        resp1 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call])
        resp2 = _make_chat_response(content="Sorry, I had trouble with that tool call.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[resp1, resp2]
        )

        mock_tool_manager = MagicMock()

        tools = [{"type": "function", "function": {"name": "search_course_content"}}]
        gen = AIGenerator(api_key="fake", model="gpt-4o")
        result = await gen.generate_response(query="Bad args", tools=tools, tool_manager=mock_tool_manager)

        assert result == "Sorry, I had trouble with that tool call."
        # Tool was never actually executed because args couldn't be parsed
        mock_tool_manager.execute_tool.assert_not_called()

        # Error message was sent as tool result
        second_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]
        tool_messages = [m for m in second_call_kwargs["messages"] if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert "Error parsing tool arguments" in tool_messages[0]["content"]

    @patch("ai_generator.AsyncOpenAI")
    async def test_tools_included_in_intermediate_calls(self, MockAsyncOpenAI):
        mock_client = MagicMock()
        MockAsyncOpenAI.return_value = mock_client

        tool_call = MagicMock()
        tool_call.id = "call_inter"
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = json.dumps({"query": "test"})

        resp1 = _make_chat_response(content=None, finish_reason="tool_calls", tool_calls=[tool_call])
        resp2 = _make_chat_response(content="Done after one tool call.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[resp1, resp2]
        )

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Some result"

        tools = [{"type": "function", "function": {"name": "search_course_content"}}]
        gen = AIGenerator(api_key="fake", model="gpt-4o")
        await gen.generate_response(query="Check intermediate", tools=tools, tool_manager=mock_tool_manager)

        # The follow-up call (after round 1) should include tools and tool_choice
        second_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]
        assert second_call_kwargs["tools"] == tools
        assert second_call_kwargs["tool_choice"] == "auto"

    def test_system_prompt_allows_multiple_tool_calls(self):
        assert "One tool call per query maximum" not in AIGenerator.SYSTEM_PROMPT
        assert "two sequential tool calls" in AIGenerator.SYSTEM_PROMPT
