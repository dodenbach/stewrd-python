"""Stewrd Python SDK — a thin wrapper around the Stewrd Agent API."""

from .client import Stewrd
from .errors import StewrdError
from .streaming import AgentStream
from .types import (
    AgentResponse,
    DoneEvent,
    ErrorEvent,
    InputFile,
    Meta,
    ResponseFile,
    StreamEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
    Usage,
)

__version__ = "1.0.0"

__all__ = [
    "Stewrd",
    "StewrdError",
    "AgentStream",
    "AgentResponse",
    "InputFile",
    "ResponseFile",
    "Usage",
    "Meta",
    "TokenEvent",
    "ToolStartEvent",
    "ToolEndEvent",
    "DoneEvent",
    "ErrorEvent",
    "StreamEvent",
    "__version__",
]
