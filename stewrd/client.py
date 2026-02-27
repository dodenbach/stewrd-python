"""Stewrd SDK client."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence

import httpx

from .errors import StewrdError
from .streaming import AgentStream
from .types import AgentResponse, InputFile

__all__ = ["Stewrd"]

_DEFAULT_BASE_URL = "https://api.stewrd.dev"
_DEFAULT_TIMEOUT = 120.0  # seconds
_USER_AGENT = "stewrd-python/1.0.0"


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
    ) -> AgentResponse:
        """Run the agent and return the full response.

        Args:
            message: The instruction for the agent.
            capabilities: Capabilities to enable (e.g. ``["research", "documents"]``).
            files: Files to include as context.
        """
        body = self._build_body(message, capabilities=capabilities, files=files, stream=False)
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
        body = self._build_body(message, capabilities=capabilities, files=files, stream=True)
        resp = self._client._request("/v1/agent", body, stream=True)
        return AgentStream(resp)

    @staticmethod
    def _build_body(
        message: str,
        *,
        capabilities: Optional[Sequence[str]],
        files: Optional[Sequence[InputFile]],
        stream: bool,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"message": message, "stream": stream}
        if capabilities is not None:
            body["capabilities"] = list(capabilities)
        if files is not None:
            body["files"] = [asdict(f) for f in files]
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
            response = self._client.stream("POST", path, json=body)
            # Enter the stream context so the caller can iterate
            resp = response.__enter__()
            if resp.status_code >= 400:
                # Read the error body before raising
                resp.read()
                response.__exit__(None, None, None)
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
