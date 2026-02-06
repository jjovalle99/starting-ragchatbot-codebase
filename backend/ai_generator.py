from openai import OpenAI
from typing import List, Optional, Dict, Any
import json


class AIGenerator:
    """Handles interactions with OpenAI's API for generating responses"""

    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
- **search_course_content**: Search for specific content within course materials
- **get_course_outline**: Get the complete structure of a course (title, link, and all lessons)

Tool Usage Guidelines:
- Use search for questions about specific course content or detailed educational materials
- Use outline for questions about course structure, available lessons, or what topics a course covers
- **One tool call per query maximum**
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
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_response(
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
        response = self.client.chat.completions.create(**params)

        # Handle tool calls if present
        if response.choices[0].finish_reason == "tool_calls" and tool_manager:
            return self._handle_tool_execution(response, messages, tool_manager)

        return response.choices[0].message.content

    def _handle_tool_execution(
        self,
        initial_response: Any,
        messages: List[Dict[str, Any]],
        tool_manager: Any
    ) -> str:
        """
        Handle execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            messages: Current conversation messages
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Add assistant message with tool calls
        assistant_message = initial_response.choices[0].message
        messages.append(assistant_message)

        # Execute each tool call and add results
        for tool_call in assistant_message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = tool_manager.execute_tool(tool_call.function.name, **args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        # Get final response
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            max_tokens=800
        )

        return final_response.choices[0].message.content
