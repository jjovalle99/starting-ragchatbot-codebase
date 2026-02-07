"""Handles OpenAI API interactions and tool-calling for RAG query responses."""

from dataclasses import dataclass
import logging
from openai import AsyncOpenAI
from typing import List, Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


@dataclass
class ToolRoundContext:
    round_number: int
    max_rounds: int
    tools: List
    tool_manager: Any


class AIGenerator:
    """Handles interactions with OpenAI's API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
- **search_course_content**: Search for specific content within course materials
- **get_course_outline**: Get the complete structure of a course (title, link, and all lessons)

Tool Usage Guidelines:
- Use search for questions about specific course content or detailed educational materials
- Use outline for questions about course structure, available lessons, or what topics a course covers
- **Up to two sequential tool calls per query** - you may call a tool, review the results, and call another tool if the first result is insufficient or you need to combine information from different sources
- Synthesize results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**: Provide direct answers only

All responses must be:
1. **Brief and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked."""

    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        # Build system prompt with conversation history if available
        system_prompt = self.SYSTEM_PROMPT
        if conversation_history:
            system_prompt = f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"

        # Build messages array
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Create API call parameters
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 800
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Call OpenAI API
        response = await self.client.chat.completions.create(**params)

        # Handle tool calls if present
        if response.choices[0].finish_reason == "tool_calls" and tool_manager:
            logger.info("Tool calls requested by model, starting tool execution rounds")
            context = ToolRoundContext(
                round_number=1,
                max_rounds=self.MAX_TOOL_ROUNDS,
                tools=tools,
                tool_manager=tool_manager,
            )
            return await self._handle_tool_execution(response, messages, context)

        logger.info("No tool calls, returning direct response")
        return response.choices[0].message.content

    async def _handle_tool_execution(
        self,
        initial_response: Any,
        messages: List[Dict[str, Any]],
        context: ToolRoundContext,
    ) -> str:
        """
        Handle execution of tool calls and get follow-up response.

        Supports up to `context.max_rounds` sequential tool-call rounds via
        recursion. Each round executes the requested tools and makes a
        follow-up API call. Intermediate rounds include tools so the model
        can request another; the final round omits tools to force a text
        response.

        Args:
            initial_response: The response containing tool use requests
            messages: Current conversation messages
            context: Tracks round number, max rounds, tools, and tool_manager

        Returns:
            Final response text after tool execution
        """
        # Add assistant message with tool calls
        assistant_message = initial_response.choices[0].message
        messages.append(assistant_message)

        # Execute each tool call and add results
        tool_count = len(assistant_message.tool_calls)
        logger.info("Round %d/%d: executing %d tool call(s)", context.round_number, context.max_rounds, tool_count)
        for tool_call in assistant_message.tool_calls:
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as exc:
                logger.warning("Round %d: failed to parse arguments for tool '%s': %s", context.round_number, tool_call.function.name, exc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Error parsing tool arguments: {exc}",
                })
                continue

            logger.info("Round %d: calling tool '%s' with args %s", context.round_number, tool_call.function.name, args)
            try:
                result = context.tool_manager.execute_tool(
                    tool_call.function.name, **args
                )
            except Exception as exc:
                logger.error("Round %d: tool '%s' raised an error: %s", context.round_number, tool_call.function.name, exc)
                result = f"Error executing tool: {exc}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        # Build follow-up API call params
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 800,
        }

        if context.round_number < context.max_rounds:
            params["tools"] = context.tools
            params["tool_choice"] = "auto"

        follow_up = await self.client.chat.completions.create(**params)

        # If the model wants another tool call and we have rounds left, recurse
        if (
            follow_up.choices[0].finish_reason == "tool_calls"
            and context.round_number < context.max_rounds
        ):
            logger.info("Round %d: model requested another tool call, proceeding to round %d", context.round_number, context.round_number + 1)
            next_context = ToolRoundContext(
                round_number=context.round_number + 1,
                max_rounds=context.max_rounds,
                tools=context.tools,
                tool_manager=context.tool_manager,
            )
            return await self._handle_tool_execution(follow_up, messages, next_context)

        logger.info("Tool execution complete after %d round(s)", context.round_number)
        return follow_up.choices[0].message.content
