"""Server-Sent Events stream wrapper for the Stewrd Agent API."""

from __future__ import annotations

import json
from typing import Iterator, Optional

import httpx

from .types import (
    AgentResponse,
    DoneEvent,
    ErrorEvent,
    StreamEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
    Usage,
)


class AgentStream:
    """Synchronous iterator over SSE events from the Stewrd Agent API.

    Usage::

        for event in stewrd.agent.stream(message="..."):
            if event.type == "token":
                print(event.content, end="")
    """

    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self._final_response: Optional[AgentResponse] = None

    # -- iteration ----------------------------------------------------------

    def __iter__(self) -> Iterator[StreamEvent]:
        buffer = ""
        for chunk in self._response.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                event = self._parse_sse_block(block)
                if event is not None:
                    if isinstance(event, DoneEvent):
                        self._final_response = event.response
                    yield event

        # Flush remaining buffer
        if buffer.strip():
            event = self._parse_sse_block(buffer)
            if event is not None:
                if isinstance(event, DoneEvent):
                    self._final_response = event.response
                yield event

    # -- helpers ------------------------------------------------------------

    def final_response(self) -> AgentResponse:
        """Consume the entire stream and return the final ``AgentResponse``.

        Useful when you want streaming progress but ultimately need the full
        response object.
        """
        for event in self:
            if isinstance(event, DoneEvent):
                return event.response

        if self._final_response is not None:
            return self._final_response

        raise RuntimeError("Stream ended without a done event")

    # -- SSE parsing --------------------------------------------------------

    @staticmethod
    def _parse_sse_block(block: str) -> Optional[StreamEvent]:
        event_type = ""
        data = ""

        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data += line[len("data:") :].strip()

        if not event_type or not data:
            return None

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return None

        if event_type == "token":
            return TokenEvent(content=parsed.get("content", ""))
        if event_type == "tool_start":
            return ToolStartEvent(tool=parsed.get("tool", ""))
        if event_type == "tool_end":
            return ToolEndEvent(tool=parsed.get("tool", ""))
        if event_type == "done":
            resp = AgentResponse.from_dict(parsed.get("response", {}))
            usage_data = parsed.get("usage") or (parsed.get("response") or {}).get("usage", {})
            return DoneEvent(response=resp, usage=Usage.from_dict(usage_data))
        if event_type == "error":
            return ErrorEvent(code=parsed.get("code", ""), message=parsed.get("message", ""))

        return None
