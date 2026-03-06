"""Stewrd SDK client."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Sequence

import httpx

from .errors import StewrdError
from .streaming import AgentStream
from .types import AgentResponse, InputFile, ToolDefinition, ToolOutput

__all__ = ["Stewrd"]

_DEFAULT_BASE_URL = "https://api.stewrd.dev"
_DEFAULT_TIMEOUT = 120.0  # seconds
_USER_AGENT = "stewrd-python/1.1.0"


class _AgentNamespace:
    """Namespace so callers can write ``stewrd.agent.run(...)``."""

    def __init__(self, client: "Stewrd") -> None:
        self._client = client

    def run(
        self,
        message: str,
        *,
        capabilities: Optional[Sequence[str]] = None,
        files: Optional[Sequence[InputFile]] = None,
        tools: Optional[Sequence[ToolDefinition]] = None,
    ) -> AgentResponse:
        """Run the agent and return the full response.

        Args:
            message: The instruction for the agent.
            capabilities: Capabilities to enable (e.g. ``["research", "documents"]``).
            files: Files to include as context.
            tools: Custom tool definitions for function calling.
        """
        body = self._build_body(message, capabilities=capabilities, files=files, tools=tools, stream=False)
        resp = self._client._request("/v1/agent", body)
        return AgentResponse.from_dict(resp.json())

    def stream(
        self,
        message: str,
        *,
        capabilities: Optional[Sequence[str]] = None,
        files: Optional[Sequence[InputFile]] = None,
    ) -> AgentStream:
        """Run the agent with streaming — returns an iterable of events.

        Args:
            message: The instruction for the agent.
            capabilities: Capabilities to enable (e.g. ``["research", "documents"]``).
            files: Files to include as context.
        """
        body = self._build_body(message, capabilities=capabilities, files=files, tools=None, stream=True)
        resp = self._client._request("/v1/agent", body, stream=True)
        return AgentStream(resp)

    def submit_tool_outputs(
        self,
        request_id: str,
        tool_outputs: Sequence[ToolOutput],
        *,
        compute_instance: Optional[str] = None,
    ) -> AgentResponse:
        """Submit tool call results and continue execution.

        Args:
            request_id: The request ID from the initial agent response.
            tool_outputs: Tool outputs to submit.
            compute_instance: Compute instance ID for machine affinity routing.
        """
        body: Dict[str, Any] = {
            "tool_outputs": [asdict(o) for o in tool_outputs],
        }
        if compute_instance is not None:
            body["_compute_instance"] = compute_instance
        resp = self._client._request(f"/v1/agent/{request_id}/tool-outputs", body)
        return AgentResponse.from_dict(resp.json())

    def run_with_tools(
        self,
        message: str,
        *,
        tools: Sequence[ToolDefinition],
        handler: Callable[[Dict[str, Any]], str],
        capabilities: Optional[Sequence[str]] = None,
        files: Optional[Sequence[InputFile]] = None,
    ) -> AgentResponse:
        """Run the agent with tools, automatically handling the tool call loop.

        Args:
            message: The instruction for the agent.
            tools: Custom tool definitions.
            handler: A callable that receives a tool call dict (with ``id``, ``name``,
                ``arguments``) and returns the result as a string.
            capabilities: Capabilities to enable.
            files: Files to include as context.
        """
        data = self.run(message, capabilities=capabilities, files=files, tools=tools)

        while data.status == "requires_tool_outputs":
            outputs = [
                ToolOutput(
                    tool_call_id=tc.id,
                    output=handler({"id": tc.id, "name": tc.name, "arguments": tc.arguments}),
                )
                for tc in data.tool_calls
            ]
            data = self.submit_tool_outputs(
                data.id,
                outputs,
                compute_instance=data._compute_instance,
            )

        return data

    @staticmethod
    def _build_body(
        message: str,
        *,
        capabilities: Optional[Sequence[str]],
        files: Optional[Sequence[InputFile]],
        tools: Optional[Sequence[ToolDefinition]],
        stream: bool,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"message": message, "stream": stream}
        if capabilities is not None:
            body["capabilities"] = list(capabilities)
        if files is not None:
            body["files"] = [asdict(f) for f in files]
        if tools is not None:
            body["tools"] = [asdict(t) for t in tools]
        return body


class Stewrd:
    """Stewrd API client.

    Example::

        from stewrd import Stewrd

        stewrd = Stewrd("sk-stw_your_key")
        result = stewrd.agent.run(message="Research CRM tools")
        print(result.message)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError(
                'An API key is required. Pass it as the first argument: Stewrd("sk-stw_...")'
            )

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
        )

        self.agent = _AgentNamespace(self)

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> "Stewrd":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    # -- internal -----------------------------------------------------------

    def _request(
        self,
        path: str,
        body: Dict[str, Any],
        *,
        stream: bool = False,
    ) -> httpx.Response:
        """Send a POST request, raising ``StewrdError`` on non-2xx responses."""
        if stream:
            request = self._client.build_request("POST", path, json=body)
            resp = self._client.send(request, stream=True)
            if resp.status_code >= 400:
                resp.read()
                resp.close()
                self._handle_error(resp)
            return resp

        response = self._client.post(path, json=body)
        if response.status_code >= 400:
            self._handle_error(response)
        return response

    @staticmethod
    def _handle_error(response: httpx.Response) -> None:
        """Parse an error response and raise ``StewrdError``."""
        try:
            data = response.json()
            err = data.get("error", data)
            code = err.get("code", "unknown_error")
            message = err.get("message", response.reason_phrase or "Unknown error")
            docs = err.get("docs")
        except Exception:
            code = "unknown_error"
            message = response.reason_phrase or "Unknown error"
            docs = None

        raise StewrdError(
            status=response.status_code,
            code=code,
            message=message,
            docs=docs,
        )
