"""Type definitions for the Stewrd API — matches the OpenAPI spec."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------


@dataclass
class InputFile:
    """A file attached to the agent request."""

    name: str
    content: str


@dataclass
class ToolDefinition:
    """A custom tool definition for function calling."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    """A tool call returned by the agent."""

    id: str
    name: str
    arguments: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolCall":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
        )


@dataclass
class ToolOutput:
    """A tool output to submit back to the agent."""

    tool_call_id: str
    output: str


# ---------------------------------------------------------------------------
# Response types
# ---------------------------------------------------------------------------


@dataclass
class ResponseFile:
    """A file returned in the agent response."""

    name: str
    content: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResponseFile":
        return cls(
            name=data.get("name", ""),
            content=data.get("content"),
            url=data.get("url"),
        )


@dataclass
class Usage:
    """Credit and token usage for a run."""

    credits_this_request: int = 0
    credits_remaining: int = 0
    tokens_used: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Usage":
        return cls(
            credits_this_request=data.get("credits_this_request", 0),
            credits_remaining=data.get("credits_remaining", 0),
            tokens_used=data.get("tokens_used", 0),
        )


@dataclass
class Meta:
    """Response metadata."""

    duration_ms: int = 0
    project_id: str = ""
    plan: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Meta":
        return cls(
            duration_ms=data.get("duration_ms", 0),
            project_id=data.get("project_id", ""),
            plan=data.get("plan", ""),
        )


@dataclass
class AgentResponse:
    """Synchronous response from ``stewrd.agent.run()``."""

    id: str = ""
    object: str = "agent.response"
    status: str = "completed"
    message: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    capabilities_used: List[str] = field(default_factory=list)
    files: List[ResponseFile] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    meta: Meta = field(default_factory=Meta)
    _compute_instance: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentResponse":
        return cls(
            id=data.get("id") or data.get("request_id", ""),
            object=data.get("object", "agent.response"),
            status=data.get("status", "completed"),
            message=data.get("message", ""),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            capabilities_used=data.get("capabilities_used", []),
            files=[ResponseFile.from_dict(f) for f in data.get("files", [])],
            usage=Usage.from_dict(data.get("usage", {})),
            meta=Meta.from_dict(data.get("meta", {})),
            _compute_instance=data.get("_compute_instance"),
        )


# ---------------------------------------------------------------------------
# Stream event types
# ---------------------------------------------------------------------------


@dataclass
class TokenEvent:
    """A chunk of the agent's response text."""

    type: str = "token"
    content: str = ""


@dataclass
class ToolStartEvent:
    """A tool invocation started."""

    type: str = "tool_start"
    tool: str = ""


@dataclass
class ToolEndEvent:
    """A tool invocation finished."""

    type: str = "tool_end"
    tool: str = ""


@dataclass
class DoneEvent:
    """Stream complete — carries the full ``AgentResponse``."""

    type: str = "done"
    response: AgentResponse = field(default_factory=AgentResponse)
    usage: Usage = field(default_factory=Usage)


@dataclass
class ErrorEvent:
    """An error occurred during streaming."""

    type: str = "error"
    code: str = ""
    message: str = ""


StreamEvent = Union[TokenEvent, ToolStartEvent, ToolEndEvent, DoneEvent, ErrorEvent]
